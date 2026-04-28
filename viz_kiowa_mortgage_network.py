#!/usr/bin/env python3
"""
Focused mortgage network: Kiowa allottees patented 1917-1921 and their lenders.

Builds a clean bipartite graph of named individuals connected to named lending
institutions with dollar amounts on every edge. Filters out category labels,
aggregate figures, and duplicates.

Usage:
    python3 viz_kiowa_mortgage_network.py
"""

import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from collections import defaultdict


def parse_amount(s):
    """Extract a dollar amount. Returns None if not a plausible individual mortgage."""
    if not s:
        return None
    match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', str(s).replace(',', ''))
    if not match:
        return None
    try:
        val = float(match.group(1).replace(',', ''))
    except ValueError:
        return None
    # Filter: individual mortgages in this period were $100-$50,000
    if val < 100 or val > 50000:
        return None
    return val


def normalize_name(name):
    """Normalize for dedup: lowercase, strip titles, collapse whitespace."""
    n = name.strip()
    # Normalize case
    n = ' '.join(w.capitalize() if w.islower() or w.isupper() else w for w in n.split())
    # Remove parenthetical aliases for matching
    n = re.sub(r'\s*\(.*?\)\s*', ' ', n).strip()
    # Collapse whitespace
    n = re.sub(r'\s+', ' ', n)
    return n


def is_named_individual(name):
    """True if this looks like an actual person's name."""
    if not name:
        return False
    n = name.lower().strip()
    if len(n) < 4:
        return False
    if n[0].isdigit():
        return False
    skip_words = [
        'indians', 'allottees', 'various', 'unnamed', 'general', 'purchasers',
        'unknown', 'unspecified', 'tribal', 'members', 'citizens', 'holders',
        'aggregate', 'total', 'historical', 'not specified', 'competent',
        'full blood', 'mixed blood', 'approximately', 'farmers', 'tenants',
        'inherited', 'original allotment', 'partial allotment',
    ]
    for w in skip_words:
        if w in n:
            return False
    if n.startswith('[') or n.startswith('('):
        return False
    if len(name) > 50:
        return False
    return True


def collect_kiowa_mortgages():
    """Collect fee patent mortgage data for the 1917-1921 Kiowa cohort."""
    conn = psycopg2.connect(dbname='historical_docs', cursor_factory=RealDictCursor)
    cur = conn.cursor()

    cur.execute("""SELECT fp.allottee, fp.allotment_number, fp.acreage, fp.patent_date,
                          fp.trust_to_fee_mechanism, fp.subsequent_buyer, fp.sale_price,
                          fp.mortgage_amount, fp.mortgage_holder, fp.context,
                          d.file_name, d.file_path
                   FROM fee_patents fp
                   JOIN documents d ON fp.document_id = d.id
                   WHERE (fp.patent_date ILIKE '%1917%' OR fp.patent_date ILIKE '%1918%'
                       OR fp.patent_date ILIKE '%1919%' OR fp.patent_date ILIKE '%1920%'
                       OR fp.patent_date ILIKE '%1921%')
                   ORDER BY fp.patent_date""")

    records = []
    for fp in cur.fetchall():
        allottee = (fp.get('allottee') or '').strip()
        if not is_named_individual(allottee):
            continue

        # Parse mortgage info — can be in mortgage_holder, mortgage_amount, or context
        mortgage_text = fp.get('mortgage_amount') or ''
        holder = fp.get('mortgage_holder') or ''
        context = fp.get('context') or ''
        amount = parse_amount(mortgage_text)

        # Try to extract lender from mortgage_amount text if no holder
        lenders = []
        if holder and holder.lower() not in ('unknown', 'none', 'n/a', 'not specified',
                                               'none mentioned', 'not mentioned', ''):
            lenders.append({'name': holder, 'amount': amount})

        # Parse multiple mortgages from mortgage_amount text
        # e.g., "$4000 to Gumm Bros (10 years, renewed) and $1000 Government loan"
        if not lenders and mortgage_text:
            # Look for "to LENDER" patterns
            parts = re.split(r'\band\b|;', mortgage_text)
            for part in parts:
                m = re.search(r'\$?([\d,]+(?:\.\d{2})?)\s+(?:to|from|mortgage\s+to)\s+([^,;(]+)', part, re.I)
                if m:
                    amt = parse_amount(m.group(1))
                    lender = m.group(2).strip()
                    if lender and len(lender) > 2:
                        lenders.append({'name': lender, 'amount': amt})
                else:
                    # Just an amount with no lender name
                    amt = parse_amount(part)
                    if amt and not lenders:
                        lenders.append({'name': 'Unknown lender', 'amount': amt})

        # Also check for buyer info (sale after mortgage)
        buyer = (fp.get('subsequent_buyer') or '').strip()
        sale_price = fp.get('sale_price') or ''

        # Determine outcome
        was_sold = buyer and buyer.lower() not in ('', 'unknown', 'none', 'n/a',
                                                      'not specified', 'none mentioned',
                                                      'not applicable', 'retained',
                                                      'none - original allottee',
                                                      'none retained by allottee',
                                                      'none (retained by allottee)')
        was_mortgaged = bool(lenders) and any(l['name'] != 'Unknown lender' for l in lenders)
        never_mortgaged = 'never mortgage' in context.lower() or 'no mortgage' in context.lower() or 'not mortgaged' in context.lower()
        canceled = 'cancel' in context.lower()

        if never_mortgaged:
            outcome = 'retained (never mortgaged)'
        elif canceled:
            outcome = 'patent canceled'
        elif was_sold and was_mortgaged:
            outcome = 'sold & mortgaged'
        elif was_sold:
            outcome = 'sold'
        elif was_mortgaged:
            outcome = 'mortgaged'
        else:
            outcome = 'unknown'

        # Classify source type
        file_name = fp.get('file_name') or ''
        file_path = fp.get('file_path') or ''
        if 'Affidavit' in file_path or 'Affidavit' in file_name:
            source_type = 'Sworn affidavit (1928-1929)'
        elif 'comp comm' in file_name.lower() or 'forced fee' in file_name.lower() or 'competency' in file_name.lower():
            source_type = 'Competency commission records'
        elif 'Survey' in file_name or 'survey' in file_name:
            source_type = 'Congressional testimony (Survey of Conditions)'
        elif 'CCF' in file_name or 'ccf' in file_name:
            source_type = 'BIA correspondence (CCF)'
        elif 'IRA' in file_name or 'Sen Sub' in file_name or 'RG 46' in file_name or 'RG 233' in file_name:
            source_type = 'Congressional records'
        elif 'SANSAR' in file_name or 'SANSR' in file_name:
            source_type = 'BIA statistical report'
        else:
            source_type = 'Other archival source'

        records.append({
            'allottee': normalize_name(allottee),
            'patent_date': fp.get('patent_date', ''),
            'acreage': fp.get('acreage', ''),
            'allotment': fp.get('allotment_number', ''),
            'mechanism': fp.get('trust_to_fee_mechanism', ''),
            'lenders': lenders,
            'buyer': buyer if was_sold else '',
            'sale_price': sale_price if was_sold else '',
            'outcome': outcome,
            'source_type': source_type,
            'source_doc': file_name,
            'context': context[:200],
        })

    conn.close()
    return records


def build_html(records):
    """Build a focused bipartite visualization."""

    # Deduplicate allottees by normalized name, merge their mortgage data
    allottee_data = defaultdict(lambda: {
        'lenders': [], 'patent_date': '', 'acreage': '', 'outcome': '',
        'allotment': '', 'buyer': '', 'sale_price': '', 'context': '',
        'source_type': '', 'source_doc': '', 'is_affidavit': False,
    })
    for r in records:
        name = r['allottee']
        ad = allottee_data[name]
        if not ad['patent_date']:
            ad['patent_date'] = r['patent_date']
            ad['acreage'] = r['acreage']
            ad['allotment'] = r['allotment']
            ad['buyer'] = r['buyer']
            ad['sale_price'] = r['sale_price']
            ad['context'] = r['context']
            ad['source_type'] = r.get('source_type', '')
            ad['source_doc'] = r.get('source_doc', '')
        if 'affidavit' in r.get('source_type', '').lower():
            ad['is_affidavit'] = True
            ad['source_type'] = r['source_type']  # prefer the affidavit source
        if r['outcome'] != 'unknown':
            ad['outcome'] = r['outcome']
        for l in r['lenders']:
            if l['name'] != 'Unknown lender':
                ad['lenders'].append(l)

    # Build unique lender list
    all_lenders = defaultdict(lambda: {'allottees': set(), 'total_volume': 0})
    edges = []

    for allottee, data in allottee_data.items():
        for l in data['lenders']:
            lender_name = normalize_name(l['name'])
            all_lenders[lender_name]['allottees'].add(allottee)
            if l['amount']:
                all_lenders[lender_name]['total_volume'] += l['amount']
            edges.append({
                'allottee': allottee,
                'lender': lender_name,
                'amount': l['amount'],
            })

    # Sort allottees by patent date
    sorted_allottees = sorted(allottee_data.keys(),
                               key=lambda a: allottee_data[a]['patent_date'] or 'zzzz')

    # Only include allottees that have at least one named lender
    allottees_with_lenders = [a for a in sorted_allottees if allottee_data[a]['lenders']]

    # Sort lenders by total volume
    sorted_lenders = sorted(all_lenders.keys(),
                            key=lambda l: all_lenders[l]['total_volume'], reverse=True)

    # Build nodes
    nodes = []
    node_idx = {}

    for lender in sorted_lenders:
        idx = len(nodes)
        node_idx[('lender', lender)] = idx
        ld = all_lenders[lender]
        nodes.append({
            'id': idx, 'label': lender, 'type': 'lender',
            'count': len(ld['allottees']),
            'volume': ld['total_volume'],
            'volume_label': f"${ld['total_volume']:,.0f}" if ld['total_volume'] > 0 else '',
        })

    for allottee in allottees_with_lenders:
        idx = len(nodes)
        node_idx[('allottee', allottee)] = idx
        ad = allottee_data[allottee]
        nodes.append({
            'id': idx, 'label': allottee, 'type': 'allottee',
            'patent_date': ad['patent_date'],
            'outcome': ad['outcome'],
            'acreage': ad['acreage'],
            'is_affidavit': ad['is_affidavit'],
        })

    # Deduplicate edges
    seen = set()
    clean_edges = []
    for e in edges:
        if e['allottee'] not in [a for a in allottees_with_lenders]:
            continue
        key = (e['allottee'], e['lender'])
        if key in seen:
            continue
        seen.add(key)
        src = node_idx.get(('allottee', e['allottee']))
        tgt = node_idx.get(('lender', e['lender']))
        if src is not None and tgt is not None:
            clean_edges.append({
                'source': src, 'target': tgt,
                'amount': e['amount'],
                'amount_label': f"${e['amount']:,.0f}" if e['amount'] else '',
            })

    # Also build a table of ALL allottees (including those without named lenders)
    table_data = []
    for allottee in sorted_allottees:
        ad = allottee_data[allottee]
        table_data.append({
            'name': allottee,
            'date': ad['patent_date'],
            'acreage': ad['acreage'],
            'allotment': ad['allotment'],
            'outcome': ad['outcome'],
            'source_type': ad['source_type'],
            'is_affidavit': ad['is_affidavit'],
            'lenders': ', '.join(f"{l['name']} (${l['amount']:,.0f})" if l['amount'] else l['name']
                                 for l in ad['lenders']) or '—',
            'buyer': ad['buyer'] or '—',
            'context': ad['context'],
        })

    data = json.dumps({
        'nodes': nodes, 'edges': clean_edges, 'table': table_data,
        'n_allottees': len(allottees_with_lenders),
        'n_allottees_total': len(sorted_allottees),
        'n_lenders': len(sorted_lenders),
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Kiowa Mortgage Network, 1917–1921</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,500;1,400&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'DM Sans', sans-serif; background: #F7F3EC; color: #1A1714; }}
  header {{ padding: 40px 48px 24px; border-bottom: 1px solid #D4CEC4; }}
  header h1 {{ font-family: 'Newsreader', Georgia, serif; font-size: 32px; font-weight: 500; margin-bottom: 12px; }}
  header p {{ font-size: 15px; color: #6B6358; max-width: 700px; line-height: 1.6; }}
  .stats {{ padding: 16px 48px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #6B6358; border-bottom: 1px solid #D4CEC4; display: flex; gap: 32px; }}
  .stats span {{ color: #A3542E; font-weight: 500; }}
  #chart {{ padding: 32px 48px; }}
  svg {{ display: block; }}
  .tooltip {{ position: absolute; background: #1A1714; color: #E8E4DC; padding: 12px 16px; border-radius: 4px; font-size: 12px; line-height: 1.6; pointer-events: none; max-width: 400px; display: none; z-index: 100; }}
  .tooltip .t-label {{ color: #D4754A; font-weight: 600; }}
  h2 {{ font-family: 'Newsreader', Georgia, serif; font-size: 22px; font-weight: 500; padding: 32px 48px 16px; border-top: 1px solid #D4CEC4; }}
  table {{ margin: 0 48px 48px; border-collapse: collapse; font-size: 13px; width: calc(100% - 96px); }}
  th {{ text-align: left; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #6B6358; padding: 8px 12px; border-bottom: 2px solid #1A1714; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #D4CEC4; vertical-align: top; }}
  tr:hover td {{ background: #EDE8DF; }}
  .outcome {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; color: white; }}
  .outcome-sold {{ background: #C0392B; }}
  .outcome-mortgaged {{ background: #D4754A; }}
  .outcome-both {{ background: #8B1A1A; }}
  .outcome-retained {{ background: #2E7D32; }}
  .outcome-canceled {{ background: #5A7A8F; }}
  .outcome-unknown {{ background: #BBB; }}
</style>
</head>
<body>
<header>
  <h1>The Kiowa Mortgage Economy, 1917&ndash;1921</h1>
  <p>Between August 1917 and December 1921, fee patents were issued to Kiowa, Comanche, Caddo, and Wichita allottees at the Kiowa Agency in Anadarko, Oklahoma. Within months, many allottees had mortgaged their land to a small number of lending institutions. This graph shows each named allottee connected to the lender(s) who held mortgages on their allotment, with dollar amounts on every edge.</p>
  <p style="margin-top: 12px; font-style: italic; font-size: 13px; color: #8B7B6B;">Note: This is not a complete list of fee patents issued at the Kiowa Agency. These are the {len(sorted_allottees)} allottees documented in the KCA and Survey of Conditions corpora. Allottees marked with a filled circle (&bull;) gave sworn depositions in 1928&ndash;1929 as part of the federal investigation into forced fee patents; their records include first-person testimony. Allottees marked with an open circle (&cir;) appear in BIA correspondence, competency commission records, or congressional testimony. &ldquo;Outcome unknown&rdquo; means the outcome does not appear in these collections, not that the allottee retained the land.</p>
</header>
<div class="stats">
  <div>Allottees with named lenders: <span>{len(allottees_with_lenders)}</span></div>
  <div>Total allottees in cohort: <span>{len(sorted_allottees)}</span></div>
  <div>Lenders: <span>{len(sorted_lenders)}</span></div>
  <div>Mortgage links: <span>{len(clean_edges)}</span></div>
</div>
<div id="chart"></div>
<div class="tooltip" id="tooltip"></div>

<h2>Complete Allottee Register, 1917&ndash;1921</h2>
<table>
  <thead>
    <tr><th>Allottee</th><th>Patent Date</th><th>Source</th><th>Outcome</th><th>Lender(s)</th><th>Buyer</th></tr>
  </thead>
  <tbody id="tbody"></tbody>
</table>

<script>
const data = {data};
const tooltip = document.getElementById('tooltip');

// Bipartite layout: allottees left, lenders right
const margin = {{top: 30, right: 280, bottom: 30, left: 220}};
const allottees = data.nodes.filter(n => n.type === 'allottee');
const lenders = data.nodes.filter(n => n.type === 'lender');

const rowHeight = Math.max(24, 500 / Math.max(allottees.length, 1));
const height = Math.max(allottees.length, lenders.length) * rowHeight + margin.top + margin.bottom;
const width = 900;
const innerW = width - margin.left - margin.right;

const svg = d3.select('#chart').append('svg').attr('width', width).attr('height', height);
const g = svg.append('g').attr('transform', `translate(${{margin.left}},${{margin.top}})`);

// Position nodes
allottees.forEach((n, i) => {{ n.x = 0; n.y = i * rowHeight; }});

// Space lenders by volume
const totalVol = lenders.reduce((s, l) => s + Math.max(Math.sqrt(l.volume || 1), 3), 0);
let ly = 0;
lenders.forEach(n => {{
  const w = Math.max(Math.sqrt(n.volume || 1), 3) / totalVol;
  n.x = innerW;
  n.y = ly + (w * (height - margin.top - margin.bottom)) / 2;
  ly += w * (height - margin.top - margin.bottom);
}});

const pos = {{}};
data.nodes.forEach(n => pos[n.id] = n);

// Edges
g.selectAll('path')
  .data(data.edges)
  .enter()
  .append('path')
  .attr('d', d => {{
    const s = pos[d.source]; const t = pos[d.target];
    const mx = innerW / 2;
    return `M${{s.x}},${{s.y}} C${{mx}},${{s.y}} ${{mx}},${{t.y}} ${{t.x}},${{t.y}}`;
  }})
  .attr('fill', 'none')
  .attr('stroke', '#C4B8A8')
  .attr('stroke-opacity', 0.5)
  .attr('stroke-width', d => d.amount ? Math.max(1, Math.min(5, d.amount / 1500)) : 1)
  .on('mouseover', function(event, d) {{
    const a = pos[d.source]; const l = pos[d.target];
    tooltip.innerHTML = `<span class="t-label">${{a.label}}</span> &rarr; <span class="t-label">${{l.label}}</span><br>${{d.amount_label || 'unknown amount'}}`;
    tooltip.style.display = 'block';
    tooltip.style.left = (event.pageX + 12) + 'px';
    tooltip.style.top = (event.pageY - 20) + 'px';
    d3.select(this).attr('stroke', '#A3542E').attr('stroke-opacity', 1).attr('stroke-width', 4);
  }})
  .on('mouseout', function(d) {{
    tooltip.style.display = 'none';
    d3.select(this).attr('stroke', '#C4B8A8').attr('stroke-opacity', 0.5)
      .attr('stroke-width', d => d.amount ? Math.max(1, Math.min(5, d.amount / 1500)) : 1);
  }});

// Edge amount labels
g.selectAll('.amt')
  .data(data.edges.filter(d => d.amount_label))
  .enter()
  .append('text')
  .attr('x', d => {{ const s = pos[d.source]; const t = pos[d.target]; return (s.x + t.x) / 2; }})
  .attr('y', d => {{ const s = pos[d.source]; const t = pos[d.target]; return (s.y + t.y) / 2 - 3; }})
  .attr('text-anchor', 'middle')
  .attr('font-family', 'JetBrains Mono, monospace')
  .attr('font-size', '9px')
  .attr('fill', '#8B7B6B')
  .text(d => d.amount_label);

// Allottee nodes + labels
g.selectAll('.a-dot')
  .data(allottees).enter().append('circle')
  .attr('cx', d => d.x).attr('cy', d => d.y)
  .attr('r', d => d.is_affidavit ? 5 : 4)
  .attr('stroke', d => d.is_affidavit ? '#1A1714' : 'none')
  .attr('stroke-width', d => d.is_affidavit ? 1.5 : 0)
  .attr('fill', d => {{
    const o = d.outcome || '';
    if (o.includes('sold') && o.includes('mortgaged')) return '#8B1A1A';
    if (o.includes('sold')) return '#C0392B';
    if (o.includes('mortgaged')) return '#D4754A';
    if (o.includes('retained')) return '#2E7D32';
    if (o.includes('cancel')) return '#5A7A8F';
    return '#3D4F5F';
  }});

g.selectAll('.a-label')
  .data(allottees).enter().append('text')
  .attr('x', d => d.x - 10).attr('y', d => d.y + 4)
  .attr('text-anchor', 'end')
  .attr('font-family', 'DM Sans, sans-serif')
  .attr('font-size', '11px')
  .attr('fill', '#1A1714')
  .text(d => d.label);

// Lender nodes + labels
g.selectAll('.l-dot')
  .data(lenders).enter().append('circle')
  .attr('cx', d => d.x).attr('cy', d => d.y)
  .attr('r', d => Math.max(6, Math.sqrt((d.volume || 100) / 200)))
  .attr('fill', '#A3542E')
  .attr('stroke', '#8B1A1A')
  .attr('stroke-width', 1.5);

g.selectAll('.l-label')
  .data(lenders).enter().append('text')
  .attr('x', d => d.x + Math.max(6, Math.sqrt((d.volume || 100) / 200)) + 8)
  .attr('y', d => d.y + 4)
  .attr('font-family', 'DM Sans, sans-serif')
  .attr('font-size', '12px')
  .attr('font-weight', '600')
  .attr('fill', '#A3542E')
  .text(d => {{
    let t = `${{d.label}} (${{d.count}})`;
    if (d.volume_label) t += ` ${{d.volume_label}}`;
    return t;
  }});

// Legend
const legend = svg.append('g').attr('transform', `translate(${{margin.left}}, ${{height - 10}})`);
const items = [
  ['#C0392B', 'Sold'], ['#D4754A', 'Mortgaged'], ['#8B1A1A', 'Sold & Mortgaged'],
  ['#2E7D32', 'Retained'], ['#5A7A8F', 'Canceled'], ['#3D4F5F', 'Unknown']
];
// Add affidavit indicator to legend
legend.append('circle').attr('cx', items.length * 120).attr('cy', 0).attr('r', 5)
  .attr('fill', '#3D4F5F').attr('stroke', '#1A1714').attr('stroke-width', 1.5);
legend.append('text').attr('x', items.length * 120 + 10).attr('y', 4)
  .attr('font-size', '10px').attr('fill', '#6B6358').text('= Sworn affidavit');
items.forEach((item, i) => {{
  legend.append('circle').attr('cx', i * 120).attr('cy', 0).attr('r', 5).attr('fill', item[0]);
  legend.append('text').attr('x', i * 120 + 10).attr('y', 4)
    .attr('font-size', '10px').attr('fill', '#6B6358').text(item[1]);
}});

// Table
const tbody = document.getElementById('tbody');
data.table.forEach(r => {{
  const tr = document.createElement('tr');
  const oClass = r.outcome.includes('sold') && r.outcome.includes('mortgaged') ? 'outcome-both'
    : r.outcome.includes('sold') ? 'outcome-sold'
    : r.outcome.includes('mortgaged') ? 'outcome-mortgaged'
    : r.outcome.includes('retained') ? 'outcome-retained'
    : r.outcome.includes('cancel') ? 'outcome-canceled'
    : 'outcome-unknown';
  const srcTag = r.is_affidavit
    ? '<span style="color:#2E7D32;font-weight:600;font-size:10px">AFFIDAVIT</span>'
    : `<span style="color:#6B6358;font-size:10px">${{r.source_type}}</span>`;
  tr.innerHTML = `
    <td><strong>${{r.name}}</strong></td>
    <td style="font-family:'JetBrains Mono',monospace;font-size:11px">${{r.date}}</td>
    <td>${{srcTag}}</td>
    <td><span class="outcome ${{oClass}}">${{r.outcome}}</span></td>
    <td>${{r.lenders}}</td>
    <td>${{r.buyer}}</td>
  `;
  tbody.appendChild(tr);
}});
</script>
</body>
</html>"""
    return html


def main():
    records = collect_kiowa_mortgages()
    print(f"Fee patents 1917-1921: {len(records)}")

    named = [r for r in records if r['lenders']]
    print(f"With named lenders: {len(named)}")

    html = build_html(records)
    with open('viz_kiowa_mortgage_network.html', 'w') as f:
        f.write(html)
    print("Written to viz_kiowa_mortgage_network.html")


if __name__ == "__main__":
    main()
