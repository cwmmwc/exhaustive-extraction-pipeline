#!/usr/bin/env python3
"""
Build a bipartite visualization of allottees and their lenders/mortgagees.

Produces an HTML file with a D3-based network showing:
- Left column: allottees (people who lost land)
- Right column: lenders/banks/mortgage holders
- Edges: mortgage relationships, sized by amount when known
- Lender nodes sized by number of allottees they're connected to

Usage:
    python3 viz_allottee_lenders.py
    python3 viz_allottee_lenders.py --output my_viz.html
    python3 viz_allottee_lenders.py --min-links 2   # only show lenders with 2+ allottees
"""

import argparse
import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from collections import Counter, defaultdict


# Normalize lender names
LENDER_ALIASES = {
    'United States Government': 'U.S. Government',
    'United States': 'U.S. Government',
    'Government': 'U.S. Government',
    'United States (for tribes)': 'U.S. Government',
    'U.S. Government': 'U.S. Government',
    'Central Bank': 'Central Bank of Toppenish',
    'Central Bank of Toppenish': 'Central Bank of Toppenish',
}

SKIP_LENDERS = {
    'various', 'unknown', 'unspecified', 'unknown mortgage holder',
    'unknown lender', 'unnamed lender', 'unknown/on loan', 'banks',
    '[unspecified lender]', 'not specified', 'none', 'n/a', '',
    'none mentioned', 'not mentioned',
}

# Words that indicate a category label, not a named individual
GENERIC_ALLOTTEE_WORDS = {
    'indians', 'allottees', 'various', 'unnamed', 'general', 'purchasers',
    'unknown', 'unspecified', 'tribal', 'members', 'citizens', 'holders',
    'sellers', 'owners', 'landowners', 'restricted', 'competent',
    'deceased', 'minors', 'heirs', 'full blood', 'mixed blood',
    'incompetents', 'prisoners', 'convicts', 'aged', 'infirm',
    'heads of families', 'applicants', 'patentees',
    'farmers', 'tenants', 'speculators', 'stockmen', 'lessees',
    'renters', 'students', 'homesteaders', 'beneficiaries',
    'tribes', 'bands', 'villages', 'pueblo', 'mission',
    'project', 'unit', 'irrigation', 'district',
    'white', 'western', 'minor', 'trust patented',
    'proposed', 'implied', 'approximately', 'newly reclaimed',
    'power co', 'power company', 'corporation', 'building co',
    'construction', 'storage co', 'club',
}


def is_named_individual(name):
    """Filter out category labels — keep only actual names."""
    if not name:
        return False
    name_lower = name.lower().strip()
    # Too short
    if len(name_lower) < 4:
        return False
    # Starts with a number (e.g., "160 Indians", "493 of 499")
    if name_lower[0].isdigit():
        return False
    # Contains generic category words
    for word in GENERIC_ALLOTTEE_WORDS:
        if word in name_lower:
            return False
    # Bracket-wrapped names like "[Deceased child of...]"
    if name_lower.startswith('['):
        return False
    # Parenthetical descriptions that aren't real names
    if name_lower.startswith('(') or name_lower.startswith('newly'):
        return False
    # "X's father/mother/children" without a proper name
    if name_lower.endswith("'s father") or name_lower.endswith("'s children"):
        return False
    # "Mr./Mrs. + single word" (no real name)
    parts = name.split()
    if len(parts) == 2 and parts[0] in ('Mr.', 'Mrs.', 'Miss', 'Dr.'):
        return True  # This IS likely a name like "Mr. Brown"
    # Very long names are usually descriptions
    if len(name) > 60:
        return False
    return True


def parse_amount(amount_str):
    """Try to extract a dollar amount from a messy string."""
    if not amount_str:
        return None
    match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', amount_str.replace(',', ''))
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except ValueError:
            return None
    return None


def collect_links():
    """Collect allottee-lender links from all databases."""
    links = []  # (allottee, lender, amount, mechanism, source_db, doc_context)

    for db in ['historical_docs', 'survey_of_conditions', 'crow_historical_docs', 'full_corpus_docs']:
        try:
            conn = psycopg2.connect(dbname=db, cursor_factory=RealDictCursor)
        except Exception:
            continue
        cur = conn.cursor()

        # Fee patents with mortgage holder
        cur.execute("""SELECT allottee, mortgage_amount, mortgage_holder,
                              trust_to_fee_mechanism, context
                       FROM fee_patents
                       WHERE mortgage_holder IS NOT NULL""")
        for fp in cur.fetchall():
            holder = (fp.get('mortgage_holder') or '').strip()
            if holder.lower() in SKIP_LENDERS:
                continue
            holder = LENDER_ALIASES.get(holder, holder)
            allottee = (fp.get('allottee') or '').strip()
            if not is_named_individual(allottee):
                continue
            amount = parse_amount(fp.get('mortgage_amount', ''))
            mechanism = fp.get('trust_to_fee_mechanism', '')
            links.append((allottee, holder, amount, mechanism, db, fp.get('context', '')[:150]))

        # Mortgages table
        try:
            cur.execute("""SELECT borrower, lender, amount, context
                          FROM mortgages
                          WHERE lender IS NOT NULL""")
            for m in cur.fetchall():
                lender = (m.get('lender') or '').strip()
                if lender.lower() in SKIP_LENDERS:
                    continue
                lender = LENDER_ALIASES.get(lender, lender)
                borrower = (m.get('borrower') or '').strip()
                if not is_named_individual(borrower):
                    continue
                amount = parse_amount(m.get('amount', ''))
                links.append((borrower, lender, amount, '', db, m.get('context', '')[:150]))
        except Exception:
            conn.rollback()

        conn.close()

    return links


def build_html(links, min_links=1):
    """Build the bipartite D3 visualization."""

    # Aggregate: count links per lender, per allottee, track dollar volume
    lender_allottees = defaultdict(set)
    lender_volume = defaultdict(float)  # total dollar volume per lender
    allottee_lenders = defaultdict(set)
    edge_data = []

    for allottee, lender, amount, mechanism, db, context in links:
        lender_allottees[lender].add(allottee)
        allottee_lenders[allottee].add(lender)
        if amount:
            lender_volume[lender] += amount
        edge_data.append({
            'allottee': allottee,
            'lender': lender,
            'amount': amount,
            'mechanism': mechanism,
            'source': db,
            'context': context,
        })

    # Filter: only lenders with min_links+ allottees
    active_lenders = {l for l, allottees in lender_allottees.items() if len(allottees) >= min_links}
    active_allottees = set()
    for l in active_lenders:
        active_allottees.update(lender_allottees[l])

    # Build nodes and edges for D3
    nodes = []
    node_index = {}

    # Sort lenders by dollar volume (most money at center), fall back to count
    sorted_lenders = sorted(active_lenders,
                            key=lambda l: (lender_volume.get(l, 0), len(lender_allottees[l])),
                            reverse=True)
    for i, lender in enumerate(sorted_lenders):
        idx = len(nodes)
        node_index[('lender', lender)] = idx
        vol = lender_volume.get(lender, 0)
        nodes.append({
            'id': idx,
            'label': lender,
            'type': 'lender',
            'count': len(lender_allottees[lender]),
            'volume': vol,
            'volume_label': f'${vol:,.0f}' if vol > 0 else '',
        })

    # Sort allottees alphabetically
    sorted_allottees = sorted(active_allottees)
    for allottee in sorted_allottees:
        idx = len(nodes)
        node_index[('allottee', allottee)] = idx
        nodes.append({
            'id': idx,
            'label': allottee,
            'type': 'allottee',
            'count': len(allottee_lenders[allottee]),
        })

    edges = []
    seen_edges = set()
    for e in edge_data:
        if e['lender'] not in active_lenders:
            continue
        key = (e['allottee'], e['lender'])
        if key in seen_edges:
            continue
        seen_edges.add(key)
        src = node_index.get(('allottee', e['allottee']))
        tgt = node_index.get(('lender', e['lender']))
        if src is not None and tgt is not None:
            edges.append({
                'source': src,
                'target': tgt,
                'amount': e['amount'],
                'context': e['context'],
            })

    data = json.dumps({'nodes': nodes, 'edges': edges})

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Allottees and Their Lenders — Dispossession Mortgage Network</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Newsreader:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'DM Sans', sans-serif;
    background: #F7F3EC;
    color: #1A1714;
  }}
  header {{
    padding: 40px 48px 24px;
    border-bottom: 1px solid #D4CEC4;
  }}
  header h1 {{
    font-family: 'Newsreader', Georgia, serif;
    font-size: 28px;
    font-weight: 500;
    margin-bottom: 8px;
  }}
  header p {{
    font-size: 14px;
    color: #6B6358;
    max-width: 800px;
    line-height: 1.5;
  }}
  .stats {{
    padding: 16px 48px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #6B6358;
    border-bottom: 1px solid #D4CEC4;
    display: flex;
    gap: 32px;
  }}
  .stats span {{ color: #A3542E; font-weight: 500; }}
  #chart {{
    width: 100%;
    overflow-x: auto;
  }}
  svg {{
    display: block;
  }}
  .allottee-label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 10px;
    fill: #1A1714;
  }}
  .lender-label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 600;
    fill: #A3542E;
  }}
  .edge {{
    stroke: #D4CEC4;
    stroke-opacity: 0.5;
    fill: none;
  }}
  .edge:hover {{
    stroke: #A3542E;
    stroke-opacity: 1;
    stroke-width: 2px;
  }}
  .node-allottee {{
    fill: #3D4F5F;
  }}
  .node-lender {{
    fill: #A3542E;
  }}
  .tooltip {{
    position: absolute;
    background: #1A1714;
    color: #E8E4DC;
    padding: 10px 14px;
    border-radius: 4px;
    font-size: 12px;
    line-height: 1.5;
    pointer-events: none;
    max-width: 350px;
    display: none;
    z-index: 100;
    font-family: 'DM Sans', sans-serif;
  }}
  .tooltip .label {{ color: #D4754A; font-weight: 600; }}
</style>
</head>
<body>

<header>
  <h1>The Dispossession Mortgage Network</h1>
  <p>Each line connects a Native American allottee (left) to a bank, lender, or institution that held a mortgage on their allotment. Lender nodes are sized by the number of allottees they served. Data extracted from KCA/Kiowa and Survey of Conditions corpora.</p>
</header>

<div class="stats">
  <div>Allottees: <span>{len(active_allottees)}</span></div>
  <div>Lenders: <span>{len(active_lenders)}</span></div>
  <div>Mortgage links: <span>{len(edges)}</span></div>
  <div>Min links filter: <span>{min_links}</span></div>
</div>

<div id="chart"></div>
<div class="tooltip" id="tooltip"></div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const data = {data};

const margin = {{top: 40, right: 300, bottom: 40, left: 280}};
const lenders = data.nodes.filter(n => n.type === 'lender');
const allottees = data.nodes.filter(n => n.type === 'allottee');

const rowHeight = 22;
const height = Math.max(allottees.length * rowHeight, lenders.length * 40) + margin.top + margin.bottom;
const width = 1200;

const svg = d3.select('#chart')
  .append('svg')
  .attr('width', width)
  .attr('height', height);

const g = svg.append('g')
  .attr('transform', `translate(${{margin.left}},${{margin.top}})`);

const innerWidth = width - margin.left - margin.right;
const innerHeight = height - margin.top - margin.bottom;

// Position allottees on the left
allottees.forEach((n, i) => {{
  n.x = 0;
  n.y = (i / (allottees.length - 1 || 1)) * innerHeight;
}});

// Position lenders on the right, spaced by connection count
// Size lenders by dollar volume when available, fall back to count
const lenderSize = l => l.volume > 0 ? Math.sqrt(l.volume / 1000) : Math.sqrt(l.count);
const totalLenderWeight = lenders.reduce((s, l) => s + lenderSize(l), 0);
let lenderY = 0;
lenders.forEach((n, i) => {{
  n.x = innerWidth;
  const weight = lenderSize(n) / totalLenderWeight;
  n.y = lenderY + (weight * innerHeight) / 2;
  lenderY += weight * innerHeight;
}});

// Store positions by node id
const pos = {{}};
data.nodes.forEach(n => {{ pos[n.id] = n; }});

// Draw edges as bezier curves
const tooltip = document.getElementById('tooltip');

g.selectAll('.edge')
  .data(data.edges)
  .enter()
  .append('path')
  .attr('class', 'edge')
  .attr('d', d => {{
    const s = pos[d.source];
    const t = pos[d.target];
    const midX = innerWidth / 2;
    return `M${{s.x}},${{s.y}} C${{midX}},${{s.y}} ${{midX}},${{t.y}} ${{t.x}},${{t.y}}`;
  }})
  .attr('stroke-width', d => d.amount ? Math.max(1, Math.min(4, d.amount / 2000)) : 1)
  .on('mouseover', function(event, d) {{
    const allottee = pos[d.source];
    const lender = pos[d.target];
    const amt = d.amount ? '$' + d.amount.toLocaleString() : 'unknown amount';
    tooltip.innerHTML = `<span class="label">${{allottee.label}}</span> &rarr; <span class="label">${{lender.label}}</span><br>${{amt}}<br>${{d.context || ''}}`;
    tooltip.style.display = 'block';
    tooltip.style.left = (event.pageX + 12) + 'px';
    tooltip.style.top = (event.pageY - 20) + 'px';
    d3.select(this).attr('stroke', '#A3542E').attr('stroke-opacity', 1).attr('stroke-width', 3);
  }})
  .on('mouseout', function() {{
    tooltip.style.display = 'none';
    d3.select(this).attr('stroke', '#D4CEC4').attr('stroke-opacity', 0.5).attr('stroke-width', d => d.amount ? Math.max(1, Math.min(4, d.amount / 2000)) : 1);
  }});

// Edge amount labels
g.selectAll('.edge-amount')
  .data(data.edges.filter(d => d.amount))
  .enter()
  .append('text')
  .attr('x', d => {{
    const s = pos[d.source];
    const t = pos[d.target];
    return (s.x + t.x) / 2;
  }})
  .attr('y', d => {{
    const s = pos[d.source];
    const t = pos[d.target];
    return (s.y + t.y) / 2;
  }})
  .attr('text-anchor', 'middle')
  .attr('font-family', 'JetBrains Mono, monospace')
  .attr('font-size', '8px')
  .attr('fill', '#999')
  .text(d => '$' + d.amount.toLocaleString());

// Draw allottee nodes and labels
g.selectAll('.node-allottee')
  .data(allottees)
  .enter()
  .append('circle')
  .attr('class', 'node-allottee')
  .attr('cx', d => d.x)
  .attr('cy', d => d.y)
  .attr('r', 3);

g.selectAll('.allottee-label')
  .data(allottees)
  .enter()
  .append('text')
  .attr('class', 'allottee-label')
  .attr('x', d => d.x - 8)
  .attr('y', d => d.y + 3)
  .attr('text-anchor', 'end')
  .text(d => d.label);

// Draw lender nodes and labels
g.selectAll('.node-lender')
  .data(lenders)
  .enter()
  .append('circle')
  .attr('class', 'node-lender')
  .attr('cx', d => d.x)
  .attr('cy', d => d.y)
  .attr('r', d => Math.max(5, d.volume > 0 ? Math.sqrt(d.volume / 500) : Math.sqrt(d.count) * 4));

g.selectAll('.lender-label')
  .data(lenders)
  .enter()
  .append('text')
  .attr('class', 'lender-label')
  .attr('x', d => d.x + Math.max(5, d.volume > 0 ? Math.sqrt(d.volume / 500) : Math.sqrt(d.count) * 4) + 8)
  .attr('y', d => d.y + 4)
  .text(d => {{
    let label = `${{d.label}} (${{d.count}})`;
    if (d.volume_label) label += ` ${{d.volume_label}}`;
    return label;
  }});

</script>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(description="Allottee-Lender bipartite visualization")
    parser.add_argument("--output", default="viz_allottee_lenders.html")
    parser.add_argument("--min-links", type=int, default=2,
                        help="Only show lenders with this many allottees (default: 2)")
    args = parser.parse_args()

    links = collect_links()
    print(f"Total links collected: {len(links)}")

    html = build_html(links, min_links=args.min_links)

    with open(args.output, 'w') as f:
        f.write(html)
    print(f"Written to {args.output}")


if __name__ == "__main__":
    main()
