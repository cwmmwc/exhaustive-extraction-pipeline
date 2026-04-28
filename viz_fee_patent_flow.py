#!/usr/bin/env python3
"""
Visualize the flow from fee patent mechanism to allottee outcome.

Shows: Policy mechanism → Allottee → What happened (sold, mortgaged, retained, unknown)

Usage:
    python3 viz_fee_patent_flow.py
    python3 viz_fee_patent_flow.py --output fee_patent_flow.html
"""

import argparse
import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from collections import Counter, defaultdict


def classify_mechanism(mech, context):
    """Normalize mechanism into clean categories."""
    mech = (mech or '').lower()
    context = (context or '').lower()

    if 'declaration' in mech or 'declaration of policy' in context:
        return 'Declaration of Policy'
    elif 'competency' in mech or 'competency commission' in context:
        return 'Competency Commission'
    elif 'forced' in mech or 'without application' in context or 'without consent' in context or 'compelled' in mech:
        return 'Forced (no application)'
    elif 'administrative' in mech:
        return 'Administrative'
    elif 'application' in mech:
        return 'By Application'
    elif 'private_bill' in mech:
        return 'Private Bill'
    else:
        return 'Other/Unknown'


def classify_outcome(fp):
    """Determine what happened after the patent was issued."""
    buyer = (fp.get('subsequent_buyer') or '').lower()
    mortgage = (fp.get('mortgage_amount') or '').lower()
    mortgage_holder = (fp.get('mortgage_holder') or '').lower()
    sale_price = (fp.get('sale_price') or '').lower()
    context = (fp.get('context') or '').lower()

    sold = False
    mortgaged = False

    if buyer and buyer not in ('', 'unknown', 'none', 'not specified', 'not mentioned',
                                'n/a', 'none - original allottee', 'none mentioned',
                                'various', 'grantee'):
        sold = True
    if 'sold' in context or 'purchased by' in context or 'sale' in sale_price:
        sold = True

    if mortgage_holder and mortgage_holder not in ('', 'unknown', 'none', 'not specified',
                                                     'not mentioned', 'n/a', 'none mentioned'):
        mortgaged = True
    if mortgage and mortgage not in ('', 'unknown', 'none', 'not specified', 'none mentioned',
                                      'not mentioned', 'n/a', 'unknown', '0'):
        if 'mortgag' in mortgage or '$' in mortgage:
            mortgaged = True
    if 'mortgage' in context and ('$' in context or 'foreclos' in context):
        mortgaged = True

    if sold and mortgaged:
        return 'Sold & Mortgaged'
    elif sold:
        return 'Sold'
    elif mortgaged:
        return 'Mortgaged'
    elif 'retain' in context or 'still own' in context or 'not sold' in context:
        return 'Retained'
    elif 'cancel' in context:
        return 'Patent Canceled'
    else:
        return 'Outcome Unknown'


def collect_doj_data():
    """Collect DOJ index card tax recovery data."""
    conn = psycopg2.connect(dbname='unified_index_cards', cursor_factory=RealDictCursor)
    cur = conn.cursor()

    # Get tax recovery cases with county info
    cur.execute("""SELECT file_number, canonical_case_name, county, tribe_or_reservation,
                          sonnet_slip_count, qwen_slip_count
                   FROM cases WHERE case_type = 'tax_recovery'""")
    cases = {r['file_number']: r for r in cur.fetchall()}

    # Get allottees linked to tax recovery cases
    cur.execute("""SELECT canonical_name, roles, tribes, file_numbers
                   FROM persons WHERE 'allottee' = ANY(roles)""")

    tax_file_numbers = set(cases.keys())
    allottee_cases = []
    for p in cur.fetchall():
        fns = p.get('file_numbers') or []
        for fn in fns:
            if fn in tax_file_numbers:
                case = cases[fn]
                allottee_cases.append({
                    'allottee': p['canonical_name'],
                    'tribe': (p.get('tribes') or ['Unknown'])[0],
                    'county': case.get('county') or 'Unknown',
                    'case_name': case.get('canonical_case_name') or '',
                    'file_number': fn,
                    'slips': (case.get('sonnet_slip_count') or 0) + (case.get('qwen_slip_count') or 0),
                })

    # Get county-level case counts for all tax recovery (including non-allottee cases)
    county_counts = Counter()
    for fn, case in cases.items():
        county = case.get('county') or 'Unknown'
        county_counts[county] += 1

    conn.close()
    return allottee_cases, county_counts, len(cases)


GENERIC_ALLOTTEE_WORDS = {
    'indians', 'allottees', 'various', 'unnamed', 'general', 'purchasers',
    'unknown', 'unspecified', 'tribal', 'members', 'citizens', 'holders',
    'sellers', 'owners', 'landowners', 'restricted', 'competent',
    'deceased', 'minors', 'heirs', 'full blood', 'mixed blood',
    'incompetents', 'prisoners', 'convicts', 'aged', 'infirm',
    'heads of families', 'applicants', 'patentees',
}


def is_named_individual(name):
    """Filter out category labels — keep only actual names."""
    if not name:
        return False
    name_lower = name.lower().strip()
    if len(name_lower) < 4:
        return False
    if name_lower[0].isdigit():
        return False
    for word in GENERIC_ALLOTTEE_WORDS:
        if word in name_lower:
            return False
    if name_lower.startswith('['):
        return False
    return True


def classify_period(patent_date):
    """Classify a patent date into a period."""
    if not patent_date:
        return 'Unknown'
    # Extract year
    match = re.search(r'(\d{4})', str(patent_date))
    if not match:
        return 'Unknown'
    year = int(match.group(1))
    if year < 1920:
        return 'Pre-1920'
    elif year < 1930:
        return '1920-1929'
    elif year < 1935:
        return '1930-1934'
    else:
        return '1935+'


def collect_data():
    """Collect fee patent data from all databases."""
    patents = []

    for db in ['historical_docs', 'survey_of_conditions', 'crow_historical_docs', 'full_corpus_docs']:
        try:
            conn = psycopg2.connect(dbname=db, cursor_factory=RealDictCursor)
        except Exception:
            continue
        cur = conn.cursor()
        cur.execute("""SELECT allottee, allotment_number, acreage, patent_date,
                              trust_to_fee_mechanism, subsequent_buyer, sale_price,
                              mortgage_amount, mortgage_holder, context
                       FROM fee_patents""")
        for fp in cur.fetchall():
            allottee = (fp.get('allottee') or '').strip()
            if not allottee or allottee.lower() in ('unknown', 'unknown allottee', 'n/a'):
                continue

            mechanism = classify_mechanism(fp.get('trust_to_fee_mechanism', ''),
                                           fp.get('context', ''))
            outcome = classify_outcome(fp)

            period = classify_period(fp.get('patent_date', ''))

            patents.append({
                'allottee': allottee,
                'mechanism': mechanism,
                'outcome': outcome,
                'period': period,
                'acreage': fp.get('acreage', ''),
                'patent_date': fp.get('patent_date', ''),
                'buyer': fp.get('subsequent_buyer', ''),
                'sale_price': fp.get('sale_price', ''),
                'mortgage_holder': fp.get('mortgage_holder', ''),
                'mortgage_amount': fp.get('mortgage_amount', ''),
                'context': (fp.get('context') or '')[:200],
                'database': db,
            })
        conn.close()

    return patents


def build_html(patents, doj_allottee_cases=None, doj_county_counts=None, doj_total_cases=0):
    """Build a Sankey-style flow visualization with DOJ tax recovery data."""

    # Count flows: mechanism → outcome
    flows = Counter()
    mechanism_counts = Counter()
    outcome_counts = Counter()

    for p in patents:
        flows[(p['mechanism'], p['outcome'])] += 1
        mechanism_counts[p['mechanism']] += 1
        outcome_counts[p['outcome']] += 1

    # Build Sankey nodes and links
    mechanisms = sorted(mechanism_counts.keys(), key=lambda m: mechanism_counts[m], reverse=True)
    outcomes = sorted(outcome_counts.keys(), key=lambda o: outcome_counts[o], reverse=True)

    nodes = []
    node_index = {}

    for m in mechanisms:
        node_index[('mech', m)] = len(nodes)
        nodes.append({'label': m, 'type': 'mechanism', 'count': mechanism_counts[m]})

    for o in outcomes:
        node_index[('out', o)] = len(nodes)
        nodes.append({'label': o, 'type': 'outcome', 'count': outcome_counts[o]})

    links = []
    for (m, o), count in flows.most_common():
        src = node_index[('mech', m)]
        tgt = node_index[('out', o)]
        links.append({'source': src, 'target': tgt, 'value': count})

    # Also build a sample table of notable individual cases
    notable = [p for p in patents if p['outcome'] in ('Sold & Mortgaged', 'Sold', 'Mortgaged')
               and p['allottee'] and len(p['allottee']) < 40
               and p['mechanism'] in ('Declaration of Policy', 'Competency Commission', 'Forced (no application)', 'Administrative')]
    # Deduplicate by allottee name, keep first
    seen = set()
    unique_notable = []
    for p in notable:
        if p['allottee'] not in seen:
            seen.add(p['allottee'])
            unique_notable.append(p)
    unique_notable = unique_notable[:50]  # cap for display

    # DOJ county data for bar chart
    doj_counties = []
    if doj_county_counts:
        for county, count in doj_county_counts.most_common(25):
            doj_counties.append({'county': county, 'count': count})

    doj_cases_sample = (doj_allottee_cases or [])[:50]

    # Build temporal Sankey data — one per period
    periods = ['Pre-1920', '1920-1929', '1930-1934', '1935+', 'Unknown']
    temporal_data = {}
    for period in periods:
        period_patents = [p for p in patents if p.get('period') == period]
        if not period_patents:
            continue
        p_flows = Counter()
        p_mechs = Counter()
        p_outcomes = Counter()
        for p in period_patents:
            p_flows[(p['mechanism'], p['outcome'])] += 1
            p_mechs[p['mechanism']] += 1
            p_outcomes[p['outcome']] += 1

        p_mechanisms = sorted(p_mechs.keys(), key=lambda m: p_mechs[m], reverse=True)
        p_outcome_list = sorted(p_outcomes.keys(), key=lambda o: p_outcomes[o], reverse=True)

        p_nodes = []
        p_node_idx = {}
        for m in p_mechanisms:
            p_node_idx[('mech', m)] = len(p_nodes)
            p_nodes.append({'label': m, 'type': 'mechanism', 'count': p_mechs[m]})
        for o in p_outcome_list:
            p_node_idx[('out', o)] = len(p_nodes)
            p_nodes.append({'label': o, 'type': 'outcome', 'count': p_outcomes[o]})

        p_links = []
        for (m, o), count in p_flows.most_common():
            src = p_node_idx[('mech', m)]
            tgt = p_node_idx[('out', o)]
            p_links.append({'source': src, 'target': tgt, 'value': count})

        temporal_data[period] = {
            'nodes': p_nodes,
            'links': p_links,
            'total': len(period_patents),
        }

    data = json.dumps({
        'nodes': nodes,
        'links': links,
        'notable': unique_notable,
        'total_patents': len(patents),
        'temporal': temporal_data,
        'doj_counties': doj_counties,
        'doj_cases': doj_cases_sample,
        'doj_total_cases': doj_total_cases,
        'doj_total_allottees': len(set(c['allottee'] for c in (doj_allottee_cases or []))),
    })

    # Mechanism colors
    mech_colors = {
        'Declaration of Policy': '#8B1A1A',
        'Competency Commission': '#A3542E',
        'Forced (no application)': '#C0392B',
        'Administrative': '#D4754A',
        'By Application': '#5A7A8F',
        'Private Bill': '#3D4F5F',
        'Other/Unknown': '#999',
    }

    outcome_colors = {
        'Sold': '#C0392B',
        'Sold & Mortgaged': '#8B1A1A',
        'Mortgaged': '#D4754A',
        'Retained': '#2E7D32',
        'Patent Canceled': '#5A7A8F',
        'Outcome Unknown': '#BBB',
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Fee Patent Flow: Mechanism to Outcome</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
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
  #sankey {{
    padding: 20px 48px;
  }}
  .node-label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    font-weight: 600;
  }}
  .link {{
    fill: none;
    stroke-opacity: 0.3;
  }}
  .link:hover {{
    stroke-opacity: 0.7;
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
  }}
  .tooltip .label {{ color: #D4754A; font-weight: 600; }}

  h2 {{
    font-family: 'Newsreader', Georgia, serif;
    font-size: 22px;
    font-weight: 500;
    padding: 32px 48px 16px;
  }}
  .cases-table {{
    margin: 0 48px 48px;
    border-collapse: collapse;
    font-size: 13px;
    width: calc(100% - 96px);
  }}
  .cases-table th {{
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #6B6358;
    padding: 8px 12px;
    border-bottom: 2px solid #1A1714;
  }}
  .cases-table td {{
    padding: 8px 12px;
    border-bottom: 1px solid #D4CEC4;
    vertical-align: top;
  }}
  .cases-table tr:hover td {{
    background: #EDE8DF;
  }}
  .mech-tag {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
    color: white;
  }}
  .outcome-tag {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
    color: white;
  }}
</style>
</head>
<body>

<header>
  <h1>Fee Patent Flow: From Policy to Outcome</h1>
  <p>How were fee patents issued, and what happened to the land? The left column shows the mechanism by which trust land was converted to fee patent status. The right column shows the outcome. The width of each flow is proportional to the number of allottees.</p>
</header>

<div class="stats">
  <div>Total fee patents: <span>{len(patents)}</span></div>
  <div>Named allottees: <span>{len(set(p['allottee'] for p in patents))}</span></div>
  <div>Sources: <span>KCA + Survey of Conditions</span></div>
</div>

<div id="sankey"></div>
<div class="tooltip" id="tooltip"></div>

<h2 style="padding: 32px 48px 8px; font-family: 'Newsreader', Georgia, serif; font-size: 22px; font-weight: 500; border-top: 1px solid #D4CEC4;">The Policy Shift Over Time</h2>
<p style="padding: 0 48px 16px; font-size: 14px; color: #6B6358; max-width: 800px; line-height: 1.5;">
The same Sankey split by decade. Watch how the mechanisms and outcomes change: Declaration of Policy and competency commission patents cluster in the pre-1920 era under Commissioner Sells. Administrative patents continue through the 1920s. The proportion of known outcomes varies by period.
</p>
<div id="temporal-sankeys" style="padding: 0 48px 24px;"></div>

<h2 style="padding: 32px 48px 8px; font-family: 'Newsreader', Georgia, serif; font-size: 22px; font-weight: 500; border-top: 1px solid #D4CEC4;">The Government's Response: DOJ Tax Recovery Cases</h2>
<p style="padding: 0 48px 16px; font-size: 14px; color: #6B6358; max-width: 800px; line-height: 1.5;">
After allottees received fee patents, counties began taxing their land — often illegally, since trust land was tax-exempt. The Department of Justice filed suits to recover these taxes. The DOJ index cards document <span style="color: #A3542E; font-weight: 600;">{doj_total_cases}</span> tax recovery cases naming <span style="color: #A3542E; font-weight: 600;">{len(set(c['allottee'] for c in (doj_allottee_cases or [])))}</span> allottees across <span style="color: #A3542E; font-weight: 600;">{len(doj_county_counts)}</span> counties.
</p>
<div id="doj-chart" style="padding: 0 48px 24px;"></div>

<h3 style="padding: 16px 48px 8px; font-family: 'DM Sans', sans-serif; font-size: 14px; font-weight: 700; color: #6B6358;">DOJ Tax Recovery: Allottees by Case</h3>
<table class="cases-table">
  <thead>
    <tr><th>Allottee</th><th>Tribe</th><th>County</th><th>Case</th><th>File #</th></tr>
  </thead>
  <tbody id="doj-body"></tbody>
</table>

<h2>Individual Fee Patent Cases</h2>
<table class="cases-table">
  <thead>
    <tr>
      <th>Allottee</th>
      <th>Mechanism</th>
      <th>Outcome</th>
      <th>Details</th>
    </tr>
  </thead>
  <tbody id="cases-body">
  </tbody>
</table>

<script>
const data = {data};

const mechColors = {json.dumps(mech_colors)};
const outcomeColors = {json.dumps(outcome_colors)};

// Sankey diagram
const margin = {{top: 20, right: 200, bottom: 20, left: 200}};
const width = 900;
const height = 500;

const svg = d3.select('#sankey')
  .append('svg')
  .attr('width', width)
  .attr('height', height);

const sankey = d3.sankey()
  .nodeId(d => d.index)
  .nodeWidth(20)
  .nodePadding(12)
  .nodeAlign(d3.sankeyLeft)
  .extent([[margin.left, margin.top], [width - margin.right, height - margin.bottom]]);

const {{nodes, links}} = sankey({{
  nodes: data.nodes.map((d, i) => ({{...d, index: i}})),
  links: data.links.map(d => ({{...d}}))
}});

const tooltip = document.getElementById('tooltip');

// Draw links
svg.append('g')
  .selectAll('.link')
  .data(links)
  .enter()
  .append('path')
  .attr('class', 'link')
  .attr('d', d3.sankeyLinkHorizontal())
  .attr('stroke', d => {{
    const srcLabel = d.source.label;
    return mechColors[srcLabel] || '#999';
  }})
  .attr('stroke-width', d => Math.max(1, d.width))
  .on('mouseover', function(event, d) {{
    tooltip.innerHTML = `<span class="label">${{d.source.label}}</span> &rarr; <span class="label">${{d.target.label}}</span><br>${{d.value}} allottees`;
    tooltip.style.display = 'block';
    tooltip.style.left = (event.pageX + 12) + 'px';
    tooltip.style.top = (event.pageY - 20) + 'px';
    d3.select(this).attr('stroke-opacity', 0.7);
  }})
  .on('mouseout', function() {{
    tooltip.style.display = 'none';
    d3.select(this).attr('stroke-opacity', 0.3);
  }});

// Draw nodes
svg.append('g')
  .selectAll('rect')
  .data(nodes)
  .enter()
  .append('rect')
  .attr('x', d => d.x0)
  .attr('y', d => d.y0)
  .attr('height', d => Math.max(1, d.y1 - d.y0))
  .attr('width', d => d.x1 - d.x0)
  .attr('fill', d => {{
    if (d.type === 'mechanism') return mechColors[d.label] || '#999';
    return outcomeColors[d.label] || '#999';
  }});

// Node labels
svg.append('g')
  .selectAll('.node-label')
  .data(nodes)
  .enter()
  .append('text')
  .attr('class', 'node-label')
  .attr('x', d => d.type === 'mechanism' ? d.x0 - 8 : d.x1 + 8)
  .attr('y', d => (d.y0 + d.y1) / 2)
  .attr('dy', '0.35em')
  .attr('text-anchor', d => d.type === 'mechanism' ? 'end' : 'start')
  .text(d => `${{d.label}} (${{d.count}})`);

// Populate cases table
const tbody = document.getElementById('cases-body');
data.notable.forEach(p => {{
  const tr = document.createElement('tr');
  const mechColor = mechColors[p.mechanism] || '#999';
  const outColor = outcomeColors[p.outcome] || '#999';

  let details = [];
  if (p.acreage) details.push(p.acreage + ' acres');
  if (p.patent_date) details.push('patented ' + p.patent_date);
  if (p.buyer) details.push('buyer: ' + p.buyer);
  if (p.sale_price) details.push(p.sale_price);
  if (p.mortgage_holder) details.push('mortgage: ' + p.mortgage_holder);
  if (p.mortgage_amount && p.mortgage_amount !== p.mortgage_holder) details.push(p.mortgage_amount);

  tr.innerHTML = `
    <td><strong>${{p.allottee}}</strong></td>
    <td><span class="mech-tag" style="background:${{mechColor}}">${{p.mechanism}}</span></td>
    <td><span class="outcome-tag" style="background:${{outColor}}">${{p.outcome}}</span></td>
    <td>${{details.join(' · ') || p.context}}</td>
  `;
  tbody.appendChild(tr);
}});

// Temporal Sankeys
if (data.temporal) {{
  const periods = ['Pre-1920', '1920-1929', '1930-1934', '1935+'];
  const container = d3.select('#temporal-sankeys');

  periods.forEach(period => {{
    const pData = data.temporal[period];
    if (!pData || !pData.nodes.length) return;

    const div = container.append('div')
      .style('margin-bottom', '24px');

    div.append('h3')
      .style('font-family', 'DM Sans, sans-serif')
      .style('font-size', '14px')
      .style('font-weight', '700')
      .style('color', '#6B6358')
      .style('margin-bottom', '8px')
      .text(`${{period}} (${{pData.total}} patents)`);

    const tMargin = {{top: 10, right: 180, bottom: 10, left: 180}};
    const tWidth = 800;
    const tHeight = Math.max(150, pData.nodes.length * 18 + tMargin.top + tMargin.bottom);

    const tSvg = div.append('svg')
      .attr('width', tWidth)
      .attr('height', tHeight);

    try {{
      const tSankey = d3.sankey()
        .nodeId(d => d.index)
        .nodeWidth(15)
        .nodePadding(8)
        .nodeAlign(d3.sankeyLeft)
        .extent([[tMargin.left, tMargin.top], [tWidth - tMargin.right, tHeight - tMargin.bottom]]);

      const tGraph = tSankey({{
        nodes: pData.nodes.map((d, i) => ({{...d, index: i}})),
        links: pData.links.map(d => ({{...d}}))
      }});

      tSvg.append('g')
        .selectAll('path')
        .data(tGraph.links)
        .enter()
        .append('path')
        .attr('d', d3.sankeyLinkHorizontal())
        .attr('fill', 'none')
        .attr('stroke', d => mechColors[d.source.label] || '#999')
        .attr('stroke-opacity', 0.35)
        .attr('stroke-width', d => Math.max(1, d.width));

      tSvg.append('g')
        .selectAll('rect')
        .data(tGraph.nodes)
        .enter()
        .append('rect')
        .attr('x', d => d.x0)
        .attr('y', d => d.y0)
        .attr('height', d => Math.max(1, d.y1 - d.y0))
        .attr('width', d => d.x1 - d.x0)
        .attr('fill', d => d.type === 'mechanism' ? (mechColors[d.label] || '#999') : (outcomeColors[d.label] || '#999'));

      tSvg.append('g')
        .selectAll('text')
        .data(tGraph.nodes)
        .enter()
        .append('text')
        .attr('x', d => d.type === 'mechanism' ? d.x0 - 6 : d.x1 + 6)
        .attr('y', d => (d.y0 + d.y1) / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', d => d.type === 'mechanism' ? 'end' : 'start')
        .attr('font-family', 'DM Sans, sans-serif')
        .attr('font-size', '10px')
        .attr('font-weight', '600')
        .text(d => `${{d.label}} (${{d.count}})`);
    }} catch(e) {{
      div.append('p')
        .style('color', '#999')
        .style('font-size', '12px')
        .text('Could not render Sankey for this period');
    }}
  }});
}}

// DOJ county bar chart
if (data.doj_counties && data.doj_counties.length > 0) {{
  const dojMargin = {{top: 20, right: 20, bottom: 30, left: 140}};
  const dojWidth = 800;
  const barHeight = 22;
  const dojHeight = data.doj_counties.length * barHeight + dojMargin.top + dojMargin.bottom;

  const dojSvg = d3.select('#doj-chart')
    .append('svg')
    .attr('width', dojWidth)
    .attr('height', dojHeight);

  const dojG = dojSvg.append('g')
    .attr('transform', `translate(${{dojMargin.left}},${{dojMargin.top}})`);

  const maxCount = d3.max(data.doj_counties, d => d.count);
  const xScale = d3.scaleLinear()
    .domain([0, maxCount])
    .range([0, dojWidth - dojMargin.left - dojMargin.right]);

  const yScale = d3.scaleBand()
    .domain(data.doj_counties.map(d => d.county))
    .range([0, dojHeight - dojMargin.top - dojMargin.bottom])
    .padding(0.2);

  dojG.selectAll('rect')
    .data(data.doj_counties)
    .enter()
    .append('rect')
    .attr('x', 0)
    .attr('y', d => yScale(d.county))
    .attr('width', d => xScale(d.count))
    .attr('height', yScale.bandwidth())
    .attr('fill', '#3D4F5F');

  dojG.selectAll('.bar-label')
    .data(data.doj_counties)
    .enter()
    .append('text')
    .attr('x', -8)
    .attr('y', d => yScale(d.county) + yScale.bandwidth() / 2)
    .attr('dy', '0.35em')
    .attr('text-anchor', 'end')
    .attr('font-family', 'DM Sans, sans-serif')
    .attr('font-size', '11px')
    .attr('fill', '#1A1714')
    .text(d => d.county);

  dojG.selectAll('.count-label')
    .data(data.doj_counties)
    .enter()
    .append('text')
    .attr('x', d => xScale(d.count) + 6)
    .attr('y', d => yScale(d.county) + yScale.bandwidth() / 2)
    .attr('dy', '0.35em')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-size', '10px')
    .attr('fill', '#6B6358')
    .text(d => d.count);
}}

// DOJ cases table
const dojBody = document.getElementById('doj-body');
if (data.doj_cases) {{
  data.doj_cases.forEach(c => {{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${{c.allottee}}</strong></td>
      <td>${{c.tribe}}</td>
      <td>${{c.county}}</td>
      <td style="font-size:12px">${{c.case_name.substring(0, 80)}}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:11px">${{c.file_number}}</td>
    `;
    dojBody.appendChild(tr);
  }});
}}
</script>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(description="Fee patent flow visualization")
    parser.add_argument("--output", default="viz_fee_patent_flow.html")
    args = parser.parse_args()

    patents = collect_data()
    print(f"Total fee patents: {len(patents)}")
    print(f"Named allottees: {len(set(p['allottee'] for p in patents))}")

    # Summary
    from collections import Counter
    mechs = Counter(p['mechanism'] for p in patents)
    outcomes = Counter(p['outcome'] for p in patents)
    print("\nMechanisms:")
    for m, c in mechs.most_common():
        print(f"  {c:>5}  {m}")
    print("\nOutcomes:")
    for o, c in outcomes.most_common():
        print(f"  {c:>5}  {o}")

    # Collect DOJ data
    print("\nCollecting DOJ index card data...")
    doj_allottee_cases, doj_county_counts, doj_total_cases = collect_doj_data()
    print(f"DOJ tax recovery cases: {doj_total_cases}")
    print(f"DOJ allottees in tax cases: {len(set(c['allottee'] for c in doj_allottee_cases))}")
    print(f"Counties: {len(doj_county_counts)}")

    html = build_html(patents, doj_allottee_cases, doj_county_counts, doj_total_cases)
    with open(args.output, 'w') as f:
        f.write(html)
    print(f"\nWritten to {args.output}")


if __name__ == "__main__":
    main()
