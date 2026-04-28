#!/usr/bin/env python3
"""
Visualize Circular 2464 affidavit data — 530 allottees who gave sworn testimony
about forced fee patents.

Hand-transcribed data from the original affidavits. This is not AI-extracted.

Usage:
    python3 viz_circular_2464.py
"""

import json
import re
import openpyxl
from collections import Counter, defaultdict


def parse_amount(s):
    """Extract dollar amounts from text. Returns list of (amount, context) tuples."""
    if not s:
        return []
    amounts = []
    for match in re.finditer(r'\$?([\d,]+(?:\.\d{2})?)', str(s).replace(',', '')):
        try:
            val = float(match.group(1).replace(',', ''))
            if 10 <= val <= 100000:
                amounts.append(val)
        except ValueError:
            pass
    return amounts


def classify_consent(text):
    """Classify the protest/consent field."""
    if not text:
        return 'unclear'
    t = str(text).lower().strip()
    if any(w in t for w in ['refused', 'did not want', 'protest', "didn't want",
                             'did not know', 'was told', 'forced', 'compelled',
                             'under protest', 'not want']):
        return 'protested'
    if any(w in t for w in ['accepted', 'agreed', 'wanted', 'applied', 'requested']):
        return 'accepted'
    return 'unclear'


def classify_outcome(sold_mortgaged_text):
    """Classify the outcome."""
    if not sold_mortgaged_text:
        return 'unknown'
    t = str(sold_mortgaged_text).lower().strip()
    if 'sold' in t and 'mortgag' in t:
        return 'sold & mortgaged'
    if 'sold' in t:
        return 'sold'
    if 'mortgag' in t or 'foreclos' in t:
        return 'mortgaged'
    if 'neither' in t or t == 'no' or 'retain' in t or 'still own' in t:
        return 'retained'
    return 'unknown'


def load_data():
    """Load and parse the Circular 2464 spreadsheet."""
    path = '/Users/cwm6W/Library/CloudStorage/OneDrive-UniversityofVirginia/Circular 2464/Replies to Circular 2464.xlsx'
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb['Sheet1']
    rows = list(ws.iter_rows(values_only=True))
    headers = rows[0]
    data_rows = [r for r in rows[1:] if r[0]]  # skip empty rows

    records = []
    for r in data_rows:
        name = str(r[0] or '').strip()
        if not name:
            continue

        reservation = str(r[1] or '').strip()
        address = str(r[2] or '').strip()
        allotment = str(r[3] or '').strip()
        canceled = str(r[4] or '').strip()
        protest_text = str(r[5] or '').strip()
        recorded = str(r[6] or '').strip()
        sold_mortgaged = str(r[7] or '').strip()
        buyer_text = str(r[8] or '').strip()
        tax_burden = str(r[9] or '').strip()
        trust_date = str(r[10] or '').strip()
        fee_date = str(r[11] or '').strip()
        gender = str(r[12] or '').strip()
        age = str(r[13] or '').strip()
        occupation = str(r[14] or '').strip()
        notes = str(r[15] or '').strip()

        consent = classify_consent(protest_text)
        outcome = classify_outcome(sold_mortgaged)
        was_canceled = 'cancel' in canceled.lower() if canceled else False

        if was_canceled and outcome == 'unknown':
            outcome = 'canceled'

        # Extract sale amounts
        sale_amounts = parse_amount(buyer_text) or parse_amount(sold_mortgaged)
        mortgage_amounts = parse_amount(tax_burden) if 'mortgag' in str(tax_burden).lower() else []
        if not mortgage_amounts and 'mortgag' in sold_mortgaged.lower():
            mortgage_amounts = parse_amount(sold_mortgaged)

        records.append({
            'name': name,
            'reservation': reservation,
            'address': address,
            'allotment': allotment,
            'canceled': was_canceled,
            'consent': consent,
            'consent_text': protest_text[:200],
            'outcome': outcome,
            'sold_mortgaged_text': sold_mortgaged[:200],
            'buyer': buyer_text[:200],
            'tax_burden': tax_burden[:200],
            'trust_date': trust_date,
            'fee_date': fee_date,
            'gender': gender,
            'age': age,
            'occupation': occupation[:150],
            'notes': notes[:200],
            'sale_amount': sale_amounts[0] if sale_amounts else None,
            'mortgage_amount': mortgage_amounts[0] if mortgage_amounts else None,
        })

    return records


def build_html(records):
    """Build the comprehensive visualization."""

    # Stats
    total = len(records)
    by_reservation = Counter(r['reservation'] for r in records)
    by_consent = Counter(r['consent'] for r in records)
    by_outcome = Counter(r['outcome'] for r in records)
    by_gender = Counter(r['gender'].split()[0] if r['gender'] else '?' for r in records)
    canceled = sum(1 for r in records if r['canceled'])

    # Consent → Outcome Sankey
    consent_outcome = Counter()
    for r in records:
        consent_outcome[(r['consent'], r['outcome'])] += 1

    consent_labels = ['protested', 'unclear', 'accepted']
    outcome_labels = ['sold', 'mortgaged', 'sold & mortgaged', 'retained', 'canceled', 'unknown']

    sankey_nodes = []
    sankey_idx = {}
    for c in consent_labels:
        if by_consent.get(c, 0) > 0:
            sankey_idx[('c', c)] = len(sankey_nodes)
            sankey_nodes.append({'label': c.title(), 'type': 'consent', 'count': by_consent[c]})
    for o in outcome_labels:
        if by_outcome.get(o, 0) > 0:
            sankey_idx[('o', o)] = len(sankey_nodes)
            sankey_nodes.append({'label': o.title(), 'type': 'outcome', 'count': by_outcome[o]})

    sankey_links = []
    for (c, o), count in consent_outcome.most_common():
        src = sankey_idx.get(('c', c))
        tgt = sankey_idx.get(('o', o))
        if src is not None and tgt is not None:
            sankey_links.append({'source': src, 'target': tgt, 'value': count})

    # Reservation breakdown for bar chart
    res_data = [{'name': res, 'count': n} for res, n in by_reservation.most_common() if n >= 5]

    data = json.dumps({
        'sankey_nodes': sankey_nodes,
        'sankey_links': sankey_links,
        'reservations': res_data,
        'records': records,
        'stats': {
            'total': total,
            'protested': by_consent.get('protested', 0),
            'accepted': by_consent.get('accepted', 0),
            'sold': by_outcome.get('sold', 0),
            'mortgaged': by_outcome.get('mortgaged', 0),
            'sold_mortgaged': by_outcome.get('sold & mortgaged', 0),
            'retained': by_outcome.get('retained', 0),
            'canceled': canceled,
            'male': by_gender.get('Male', 0),
            'female': by_gender.get('Female', 0),
        }
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Circular 2464: The Forced Fee Patent Record</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,500;1,400&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'DM Sans', sans-serif; background: #F7F3EC; color: #1A1714; }}
  header {{ padding: 48px 48px 28px; border-bottom: 1px solid #D4CEC4; }}
  header h1 {{ font-family: 'Newsreader', Georgia, serif; font-size: 36px; font-weight: 500; margin-bottom: 16px; }}
  header p {{ font-size: 15px; color: #6B6358; max-width: 750px; line-height: 1.65; margin-bottom: 12px; }}
  header .source {{ font-size: 12px; color: #999; font-style: italic; }}
  .num-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 1px; background: #D4CEC4; border: 1px solid #D4CEC4; margin: 32px 48px; }}
  .num-cell {{ background: white; padding: 24px 16px; text-align: center; }}
  .num-cell .num {{ font-family: 'JetBrains Mono', monospace; font-size: 32px; font-weight: 500; color: #1A1714; }}
  .num-cell .num.rust {{ color: #A3542E; }}
  .num-cell .num.red {{ color: #C0392B; }}
  .num-cell .num.green {{ color: #2E7D32; }}
  .num-cell .lbl {{ font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6B6358; margin-top: 6px; }}
  section {{ padding: 32px 48px; border-top: 1px solid #D4CEC4; }}
  section h2 {{ font-family: 'Newsreader', Georgia, serif; font-size: 24px; font-weight: 500; margin-bottom: 8px; }}
  section p {{ font-size: 14px; color: #6B6358; line-height: 1.5; max-width: 750px; margin-bottom: 16px; }}
  .tooltip {{ position: absolute; background: #1A1714; color: #E8E4DC; padding: 12px 16px; border-radius: 4px; font-size: 12px; line-height: 1.6; pointer-events: none; max-width: 450px; display: none; z-index: 100; }}
  .tooltip .t-label {{ color: #D4754A; font-weight: 600; }}
  table {{ border-collapse: collapse; font-size: 12px; width: 100%; margin-top: 16px; }}
  th {{ text-align: left; font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #6B6358; padding: 6px 8px; border-bottom: 2px solid #1A1714; position: sticky; top: 0; background: #F7F3EC; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #D4CEC4; vertical-align: top; }}
  tr:hover td {{ background: #EDE8DF; }}
  .tag {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; color: white; }}
  .tag-protested {{ background: #C0392B; }}
  .tag-accepted {{ background: #2E7D32; }}
  .tag-unclear {{ background: #999; }}
  .tag-sold {{ background: #C0392B; }}
  .tag-mortgaged {{ background: #D4754A; }}
  .tag-both {{ background: #8B1A1A; }}
  .tag-retained {{ background: #2E7D32; }}
  .tag-canceled {{ background: #5A7A8F; }}
  .tag-unknown {{ background: #BBB; }}
  .quote {{ font-family: 'Newsreader', Georgia, serif; font-style: italic; font-size: 13px; color: #4A4038; line-height: 1.5; }}
  .register-wrap {{ max-height: 800px; overflow-y: auto; border: 1px solid #D4CEC4; }}
  .filter-bar {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
  .filter-bar select, .filter-bar input {{ font-family: 'DM Sans', sans-serif; font-size: 13px; padding: 6px 10px; border: 1px solid #D4CEC4; border-radius: 4px; background: white; }}
</style>
</head>
<body>
<header>
  <h1>Circular 2464: &ldquo;I Did Not Want the Patent&rdquo;</h1>
  <p>In 1928&ndash;1929, the Bureau of Indian Affairs collected sworn affidavits from {total} allottees at Pine Ridge, Rosebud, Kiowa, and other agencies, documenting what happened after they received fee patents on their trust land. Of the {total} who testified, <strong>{by_consent.get('protested', 0)}</strong> said they did not want the patent. <strong>{by_outcome.get('sold', 0) + by_outcome.get('sold & mortgaged', 0)}</strong> lost their land through sale, <strong>{by_outcome.get('mortgaged', 0) + by_outcome.get('sold & mortgaged', 0)}</strong> through mortgage. <strong>{canceled}</strong> had their patents canceled and trust status restored.</p>
  <p class="source">Source: Hand-transcribed affidavit data from Replies to Circular 2464 (NARA). This is not AI-extracted data.</p>
</header>

<div class="num-grid">
  <div class="num-cell"><div class="num">{total}</div><div class="lbl">Allottees</div></div>
  <div class="num-cell"><div class="num rust">{by_consent.get('protested', 0)}</div><div class="lbl">Protested / Refused</div></div>
  <div class="num-cell"><div class="num red">{by_outcome.get('sold', 0) + by_outcome.get('sold & mortgaged', 0)}</div><div class="lbl">Land Sold</div></div>
  <div class="num-cell"><div class="num red">{by_outcome.get('mortgaged', 0) + by_outcome.get('sold & mortgaged', 0)}</div><div class="lbl">Land Mortgaged</div></div>
  <div class="num-cell"><div class="num green">{canceled}</div><div class="lbl">Patents Canceled</div></div>
</div>

<section>
  <h2>From Protest to Outcome</h2>
  <p>The left column shows whether the allottee consented to the patent. The right column shows what happened to the land. The width of each flow is proportional to the number of allottees. Read left to right: most who protested still lost their land.</p>
  <div id="sankey"></div>
</section>

<section>
  <h2>By Reservation</h2>
  <div id="res-chart"></div>
</section>

<section>
  <h2>The Voices: What They Said</h2>
  <p>Selected testimony from the affidavits — in the allottees' own words, recorded under oath.</p>
  <div id="quotes"></div>
</section>

<section>
  <h2>Complete Register</h2>
  <p>{total} allottees. Filter by reservation, consent, or outcome. Every row is a person who testified under oath.</p>
  <div class="filter-bar">
    <select id="f-res"><option value="">All reservations</option></select>
    <select id="f-consent"><option value="">All consent types</option></select>
    <select id="f-outcome"><option value="">All outcomes</option></select>
    <input type="text" id="f-search" placeholder="Search names...">
  </div>
  <div class="register-wrap">
    <table>
      <thead>
        <tr><th>Name</th><th>Reservation</th><th>Allotment</th><th>Consent</th><th>Outcome</th><th>What They Said</th><th>What Happened</th></tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</section>

<div class="tooltip" id="tooltip"></div>

<script>
const data = {data};
const tooltip = document.getElementById('tooltip');

// === SANKEY ===
const sMargin = {{top: 20, right: 180, bottom: 20, left: 180}};
const sWidth = 800, sHeight = 400;
const sSvg = d3.select('#sankey').append('svg').attr('width', sWidth).attr('height', sHeight);

const consentColors = {{'Protested': '#C0392B', 'Accepted': '#2E7D32', 'Unclear': '#999'}};
const outcomeColors = {{'Sold': '#C0392B', 'Mortgaged': '#D4754A', 'Sold & Mortgaged': '#8B1A1A',
                        'Retained': '#2E7D32', 'Canceled': '#5A7A8F', 'Unknown': '#BBB'}};

try {{
  const sankey = d3.sankey()
    .nodeId(d => d.index)
    .nodeWidth(20).nodePadding(14)
    .nodeAlign(d3.sankeyLeft)
    .extent([[sMargin.left, sMargin.top], [sWidth - sMargin.right, sHeight - sMargin.bottom]]);

  const sGraph = sankey({{
    nodes: data.sankey_nodes.map((d, i) => ({{...d, index: i}})),
    links: data.sankey_links.map(d => ({{...d}}))
  }});

  sSvg.append('g').selectAll('path')
    .data(sGraph.links).enter().append('path')
    .attr('d', d3.sankeyLinkHorizontal())
    .attr('fill', 'none')
    .attr('stroke', d => consentColors[d.source.label] || '#999')
    .attr('stroke-opacity', 0.35)
    .attr('stroke-width', d => Math.max(1, d.width))
    .on('mouseover', function(event, d) {{
      tooltip.innerHTML = `<span class="t-label">${{d.source.label}}</span> &rarr; <span class="t-label">${{d.target.label}}</span><br>${{d.value}} allottees`;
      tooltip.style.display = 'block';
      tooltip.style.left = (event.pageX + 12) + 'px'; tooltip.style.top = (event.pageY - 20) + 'px';
      d3.select(this).attr('stroke-opacity', 0.7);
    }})
    .on('mouseout', function() {{ tooltip.style.display = 'none'; d3.select(this).attr('stroke-opacity', 0.35); }});

  sSvg.append('g').selectAll('rect')
    .data(sGraph.nodes).enter().append('rect')
    .attr('x', d => d.x0).attr('y', d => d.y0)
    .attr('height', d => Math.max(1, d.y1 - d.y0))
    .attr('width', d => d.x1 - d.x0)
    .attr('fill', d => d.type === 'consent' ? (consentColors[d.label] || '#999') : (outcomeColors[d.label] || '#999'));

  sSvg.append('g').selectAll('text')
    .data(sGraph.nodes).enter().append('text')
    .attr('x', d => d.type === 'consent' ? d.x0 - 8 : d.x1 + 8)
    .attr('y', d => (d.y0 + d.y1) / 2).attr('dy', '0.35em')
    .attr('text-anchor', d => d.type === 'consent' ? 'end' : 'start')
    .attr('font-family', 'DM Sans, sans-serif').attr('font-size', '12px').attr('font-weight', '600')
    .text(d => `${{d.label}} (${{d.count}})`);
}} catch(e) {{ console.error('Sankey error:', e); }}

// === RESERVATION BAR CHART ===
const rMargin = {{top: 10, right: 20, bottom: 20, left: 160}};
const rWidth = 700;
const barH = 24;
const rHeight = data.reservations.length * barH + rMargin.top + rMargin.bottom;
const rSvg = d3.select('#res-chart').append('svg').attr('width', rWidth).attr('height', rHeight);
const rG = rSvg.append('g').attr('transform', `translate(${{rMargin.left}},${{rMargin.top}})`);

const rMax = d3.max(data.reservations, d => d.count);
const rX = d3.scaleLinear().domain([0, rMax]).range([0, rWidth - rMargin.left - rMargin.right]);
const rY = d3.scaleBand().domain(data.reservations.map(d => d.name)).range([0, rHeight - rMargin.top - rMargin.bottom]).padding(0.25);

rG.selectAll('rect').data(data.reservations).enter().append('rect')
  .attr('x', 0).attr('y', d => rY(d.name)).attr('width', d => rX(d.count)).attr('height', rY.bandwidth())
  .attr('fill', '#A3542E');
rG.selectAll('.rlabel').data(data.reservations).enter().append('text')
  .attr('x', -8).attr('y', d => rY(d.name) + rY.bandwidth() / 2).attr('dy', '0.35em')
  .attr('text-anchor', 'end').attr('font-size', '11px').text(d => d.name);
rG.selectAll('.rcount').data(data.reservations).enter().append('text')
  .attr('x', d => rX(d.count) + 6).attr('y', d => rY(d.name) + rY.bandwidth() / 2).attr('dy', '0.35em')
  .attr('font-family', 'JetBrains Mono, monospace').attr('font-size', '11px').attr('fill', '#6B6358')
  .text(d => d.count);

// === VOICES (selected quotes) ===
const voices = data.records.filter(r => r.consent_text.length > 50 && r.consent === 'protested')
  .sort((a, b) => b.consent_text.length - a.consent_text.length)
  .slice(0, 12);
const quotesDiv = document.getElementById('quotes');
voices.forEach(r => {{
  const div = document.createElement('div');
  div.style.marginBottom = '20px';
  div.style.paddingLeft = '16px';
  div.style.borderLeft = '3px solid #A3542E';
  div.innerHTML = `<div class="quote">&ldquo;${{r.consent_text}}&rdquo;</div>
    <div style="font-size:12px;color:#6B6358;margin-top:4px"><strong>${{r.name}}</strong>, ${{r.reservation}}, Allotment ${{r.allotment}}. Outcome: ${{r.outcome}}.</div>`;
  quotesDiv.appendChild(div);
}});

// === REGISTER TABLE ===
const tbody = document.getElementById('tbody');
const fRes = document.getElementById('f-res');
const fConsent = document.getElementById('f-consent');
const fOutcome = document.getElementById('f-outcome');
const fSearch = document.getElementById('f-search');

// Populate filter dropdowns
[...new Set(data.records.map(r => r.reservation))].sort().forEach(v => {{
  fRes.innerHTML += `<option value="${{v}}">${{v}}</option>`;
}});
['protested', 'accepted', 'unclear'].forEach(v => {{
  fConsent.innerHTML += `<option value="${{v}}">${{v}}</option>`;
}});
['sold', 'mortgaged', 'sold & mortgaged', 'retained', 'canceled', 'unknown'].forEach(v => {{
  fOutcome.innerHTML += `<option value="${{v}}">${{v}}</option>`;
}});

function renderTable() {{
  const res = fRes.value;
  const con = fConsent.value;
  const out = fOutcome.value;
  const search = fSearch.value.toLowerCase();

  tbody.innerHTML = '';
  let count = 0;
  data.records.forEach(r => {{
    if (res && r.reservation !== res) return;
    if (con && r.consent !== con) return;
    if (out && r.outcome !== out) return;
    if (search && !r.name.toLowerCase().includes(search)) return;
    count++;

    const cTag = r.consent === 'protested' ? 'tag-protested' : r.consent === 'accepted' ? 'tag-accepted' : 'tag-unclear';
    const oTag = r.outcome === 'sold' ? 'tag-sold' : r.outcome === 'mortgaged' ? 'tag-mortgaged'
      : r.outcome === 'sold & mortgaged' ? 'tag-both' : r.outcome === 'retained' ? 'tag-retained'
      : r.outcome === 'canceled' ? 'tag-canceled' : 'tag-unknown';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${{r.name}}</strong><br><span style="font-size:10px;color:#6B6358">${{r.gender}} ${{r.age}}</span></td>
      <td style="font-size:11px">${{r.reservation}}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${{r.allotment}}</td>
      <td><span class="tag ${{cTag}}">${{r.consent}}</span></td>
      <td><span class="tag ${{oTag}}">${{r.outcome}}</span>${{r.canceled ? '<br><span class="tag tag-canceled">canceled</span>' : ''}}</td>
      <td class="quote" style="max-width:250px;font-size:11px">${{r.consent_text || '—'}}</td>
      <td style="font-size:11px;max-width:250px">${{r.sold_mortgaged_text || '—'}}<br>${{r.buyer ? '<em>Buyer: ' + r.buyer + '</em>' : ''}}</td>
    `;
    tbody.appendChild(tr);
  }});
}}

fRes.onchange = fConsent.onchange = fOutcome.onchange = fSearch.oninput = renderTable;
renderTable();
</script>
</body>
</html>"""
    return html


def main():
    records = load_data()
    print(f"Loaded {len(records)} affidavit records")

    from collections import Counter
    print(f"Reservations: {Counter(r['reservation'] for r in records).most_common(5)}")
    print(f"Consent: {Counter(r['consent'] for r in records)}")
    print(f"Outcomes: {Counter(r['outcome'] for r in records)}")

    html = build_html(records)
    with open('viz_circular_2464.html', 'w') as f:
        f.write(html)
    print("Written to viz_circular_2464.html")


if __name__ == "__main__":
    main()
