#!/usr/bin/env python3
"""
Visualize cancelled fee patents and cross-reference against Circular 2464 affidavits.

Two hand-curated datasets:
  1. Cancelled fee patents master list (1,108 records, 66 tribes, 14 states)
  2. Circular 2464 affidavits (528 allottees who testified about forced patents)

The cross-reference identifies allottees who both testified AND got their patents cancelled —
the complete arc from forced patent to government acknowledgment.

Usage:
    python3 viz_cancelled_patents.py
"""

import json
import re
import openpyxl
from collections import Counter, defaultdict


def normalize_name(name):
    """Normalize for matching: title case, strip whitespace."""
    if not name:
        return ''
    return ' '.join(w.capitalize() for w in str(name).strip().split())


def load_cancelled_patents():
    """Load the cancelled patents master list."""
    path = '/Users/cwm6W/Library/CloudStorage/OneDrive-UniversityofVirginia/Cancelled patents/Cancelled fee patents master list.xlsx'
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb['results 2']
    rows = list(ws.iter_rows(values_only=True))
    data = rows[1:]

    records = []
    for r in data:
        if not r[0]:
            continue
        first = str(r[0] or '').strip()
        middle = str(r[1] or '').strip()
        last = str(r[2] or '').strip()
        full_name = f"{first} {middle} {last}".replace('  ', ' ').strip()

        allotment = str(r[3] or '').strip()
        sig_date = r[4]
        state = str(r[5] or '').strip()
        glo_tribe = str(r[6] or '').strip()
        preferred_tribe = str(r[7] or '').strip()
        comments = str(r[8] or '').strip()

        # Classify cancellation reason
        c = comments.lower()
        if '1927 act' in c or '1927 cancellation' in c:
            if '1931 act' in c:
                reason = '1927 & 1931 Acts'
            else:
                reason = '1927 Act'
        elif '1931 act' in c or '1931 cancellation' in c:
            reason = '1931 Act'
        elif '1917 act' in c or '1935' in c:
            reason = 'Other Act'
        elif 'refused' in c or 'refusal' in c or 'not accepted' in c:
            reason = 'Acceptance refused'
        elif 'erroneous' in c or 'illegal' in c or 'should not have' in c:
            reason = 'Erroneously issued'
        elif 'without application' in c:
            reason = 'Issued without application'
        elif 'incompetent' in c or 'minor' in c:
            reason = 'Allottee incompetent/minor'
        elif 'caster' in c:
            reason = 'Caster patent'
        elif 'secretary of' in c or 'secretary letter' in c or 'order of secretary' in c:
            reason = 'Secretary of Interior order'
        elif 'change of form' in c or 'lien' in c or 'act may 18' in c or 'act of may' in c or 'act july' in c:
            reason = 'Change of form/lien correction'
        elif 'decree' in c or 'decision' in c or 'benewah' in c:
            reason = 'Court decree'
        elif 'name' in c and ('correct' in c or 'change' in c):
            reason = 'Name correction'
        elif 'duplicate' in c or 'duplication' in c or 'double' in c:
            reason = 'Duplicate patent'
        elif 'correct description' in c or 'correct shares' in c or 'correct descrpt' in c:
            reason = 'Corrected description'
        elif 'new patent' in c:
            reason = 'Reissued (new patent)'
        elif 'deceased' in c:
            reason = 'Allottee deceased'
        elif 'illegible' in c or 'unclear' in c:
            reason = 'Illegible/unclear'
        elif comments:
            reason = 'Other'
        else:
            reason = 'Unknown'

        # Determine if this is a substantive cancellation vs administrative
        is_substantive = reason in ('1927 Act', '1931 Act', '1927 & 1931 Acts',
                                     'Acceptance refused', 'Erroneously issued',
                                     'Issued without application', 'Allottee incompetent/minor',
                                     'Secretary of Interior order', 'Court decree',
                                     'Caster patent', 'Other Act')

        records.append({
            'name': normalize_name(full_name),
            'first': normalize_name(first),
            'last': normalize_name(last),
            'allotment': allotment,
            'sig_date': sig_date.strftime('%Y-%m-%d') if hasattr(sig_date, 'strftime') else str(sig_date or ''),
            'state': state,
            'tribe_glo': glo_tribe,
            'tribe': preferred_tribe or glo_tribe,
            'comments': comments,
            'reason': reason,
            'is_substantive': is_substantive,
        })

    # Filter out administrative corrections — these aren't substantive cancellations
    admin_reasons = {'Name correction', 'Duplicate patent', 'Corrected description',
                     'Change of form/lien correction', 'Reissued (new patent)'}
    records = [r for r in records if r['reason'] not in admin_reasons]

    return records


def load_circular_2464():
    """Load the Circular 2464 affidavit data."""
    path = '/Users/cwm6W/Library/CloudStorage/OneDrive-UniversityofVirginia/Circular 2464/Replies to Circular 2464.xlsx'
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb['Sheet1']
    rows = list(ws.iter_rows(values_only=True))
    data = rows[1:]

    records = []
    for r in data:
        if not r[0]:
            continue
        name = str(r[0]).strip()
        records.append({
            'name': normalize_name(name),
            'reservation': str(r[1] or '').strip(),
            'allotment': str(r[3] or '').strip(),
            'canceled': 'cancel' in str(r[4] or '').lower(),
            'consent_text': str(r[5] or '').strip()[:200],
            'outcome': str(r[7] or '').strip()[:200],
            'buyer': str(r[8] or '').strip()[:200],
        })

    return records


def cross_reference(cancelled, affidavits):
    """Find allottees who appear in both datasets."""

    # Build lookup by last name for cancelled patents
    cancelled_by_last = defaultdict(list)
    for r in cancelled:
        last = r['last'].lower()
        if last:
            cancelled_by_last[last].append(r)

    # Build lookup by allotment number
    cancelled_by_allotment = defaultdict(list)
    for r in cancelled:
        if r['allotment']:
            cancelled_by_allotment[r['allotment']].append(r)

    matches = []
    for aff in affidavits:
        aff_name = aff['name'].lower()
        aff_allot = aff['allotment']

        # Try allotment number match first (strongest)
        if aff_allot and aff_allot in cancelled_by_allotment:
            for cp in cancelled_by_allotment[aff_allot]:
                # Check if names are plausibly the same
                cp_name = cp['name'].lower()
                aff_parts = set(aff_name.split())
                cp_parts = set(cp_name.split())
                overlap = aff_parts & cp_parts
                if len(overlap) >= 1:  # at least one name part matches
                    matches.append({
                        'affidavit': aff,
                        'cancelled': cp,
                        'match_type': 'allotment + name',
                        'confidence': 'high',
                    })
                    break
            else:
                # Allotment match but no name overlap — still note it
                for cp in cancelled_by_allotment[aff_allot]:
                    matches.append({
                        'affidavit': aff,
                        'cancelled': cp,
                        'match_type': 'allotment only',
                        'confidence': 'medium',
                    })
                    break
        else:
            # Try name matching
            aff_words = aff_name.split()
            if len(aff_words) >= 2:
                last_word = aff_words[-1]
                if last_word in cancelled_by_last:
                    for cp in cancelled_by_last[last_word]:
                        cp_name = cp['name'].lower()
                        # Check first name too
                        if aff_words[0] in cp_name.split():
                            matches.append({
                                'affidavit': aff,
                                'cancelled': cp,
                                'match_type': 'name',
                                'confidence': 'medium',
                            })
                            break

    return matches


def build_html(cancelled, affidavits, matches):
    """Build the visualization."""

    # Stats
    total_cp = len(cancelled)
    substantive = sum(1 for r in cancelled if r['is_substantive'])
    administrative = total_cp - substantive

    by_tribe = Counter(r['tribe'] for r in cancelled)
    by_state = Counter(r['state'] for r in cancelled)
    by_reason = Counter(r['reason'] for r in cancelled)

    # Tribe data for chart
    tribe_data = [{'name': t, 'count': n, 'substantive': sum(1 for r in cancelled if r['tribe'] == t and r['is_substantive'])}
                  for t, n in by_tribe.most_common(25) if n >= 5]

    # State data
    state_data = [{'name': s, 'count': n} for s, n in by_state.most_common()]

    reason_data = [{'name': r, 'count': n} for r, n in by_reason.most_common()]

    # Match data
    match_table = []
    for m in matches:
        aff = m['affidavit']
        cp = m['cancelled']
        match_table.append({
            'aff_name': aff['name'],
            'aff_reservation': aff['reservation'],
            'aff_allotment': aff['allotment'],
            'aff_canceled': aff['canceled'],
            'aff_consent': aff['consent_text'][:150],
            'aff_outcome': aff['outcome'][:150],
            'cp_name': cp['name'],
            'cp_tribe': cp['tribe'],
            'cp_allotment': cp['allotment'],
            'cp_state': cp['state'],
            'cp_reason': cp['reason'],
            'cp_date': cp['sig_date'],
            'cp_comments': cp['comments'][:150],
            'match_type': m['match_type'],
            'confidence': m['confidence'],
        })

    data = json.dumps({
        'tribes': tribe_data,
        'states': state_data,
        'reasons': reason_data,
        'matches': match_table,
        'cancelled': [{'name': r['name'], 'tribe': r['tribe'], 'state': r['state'],
                        'allotment': r['allotment'], 'reason': r['reason'],
                        'date': r['sig_date'], 'comments': r['comments'][:150],
                        'is_substantive': r['is_substantive']}
                       for r in cancelled],
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cancelled Fee Patents &amp; Circular 2464 Cross-Reference</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,500;1,400&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'DM Sans', sans-serif; background: #F7F3EC; color: #1A1714; }}
  header {{ padding: 48px 48px 28px; border-bottom: 1px solid #D4CEC4; }}
  header h1 {{ font-family: 'Newsreader', Georgia, serif; font-size: 32px; font-weight: 500; margin-bottom: 16px; }}
  header p {{ font-size: 15px; color: #6B6358; max-width: 750px; line-height: 1.65; margin-bottom: 12px; }}
  header .source {{ font-size: 12px; color: #999; font-style: italic; }}
  .num-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 1px; background: #D4CEC4; border: 1px solid #D4CEC4; margin: 32px 48px; }}
  .num-cell {{ background: white; padding: 24px 16px; text-align: center; }}
  .num-cell .num {{ font-family: 'JetBrains Mono', monospace; font-size: 32px; font-weight: 500; }}
  .num-cell .num.rust {{ color: #A3542E; }}
  .num-cell .num.green {{ color: #2E7D32; }}
  .num-cell .num.blue {{ color: #3D4F5F; }}
  .num-cell .lbl {{ font-size: 11px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; color: #6B6358; margin-top: 6px; }}
  section {{ padding: 32px 48px; border-top: 1px solid #D4CEC4; }}
  section h2 {{ font-family: 'Newsreader', Georgia, serif; font-size: 24px; font-weight: 500; margin-bottom: 8px; }}
  section p {{ font-size: 14px; color: #6B6358; line-height: 1.5; max-width: 750px; margin-bottom: 16px; }}
  table {{ border-collapse: collapse; font-size: 12px; width: 100%; margin-top: 16px; }}
  th {{ text-align: left; font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #6B6358; padding: 6px 8px; border-bottom: 2px solid #1A1714; position: sticky; top: 0; background: #F7F3EC; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #D4CEC4; vertical-align: top; }}
  tr:hover td {{ background: #EDE8DF; }}
  .tag {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; color: white; }}
  .tag-high {{ background: #2E7D32; }}
  .tag-medium {{ background: #D4754A; }}
  .tag-sub {{ background: #A3542E; }}
  .tag-admin {{ background: #999; }}
  .match-highlight {{ background: #FFF3CD; }}
  .register-wrap {{ max-height: 600px; overflow-y: auto; border: 1px solid #D4CEC4; }}
  .filter-bar {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
  .filter-bar select, .filter-bar input {{ font-family: 'DM Sans', sans-serif; font-size: 13px; padding: 6px 10px; border: 1px solid #D4CEC4; border-radius: 4px; background: white; }}
</style>
</head>
<body>
<header>
  <h1>Cancelled Fee Patents: The Government&rsquo;s Reversal</h1>
  <p>Between 1916 and 1931, the federal government cancelled {total_cp} fee patents across 66 tribes and 14 states. Of these, <strong>{substantive}</strong> were substantive cancellations (under the 1927 or 1931 Acts, acceptance refused, or erroneously issued) and <strong>{administrative}</strong> were administrative corrections (name changes, duplicate patents, description corrections). The substantive cancellations are evidence that the government itself acknowledged the patents should not have been issued.</p>
  <p>Cross-referencing against the 528 Circular 2464 affidavits identifies <strong>{len(matches)}</strong> allottees who both testified about forced patenting and had their patents cancelled &mdash; the complete arc from dispossession to official acknowledgment.</p>
  <p class="source">Source: Hand-compiled data from GLO records and Circular 2464 affidavits (NARA). Not AI-extracted.</p>
</header>

<div class="num-grid">
  <div class="num-cell"><div class="num">{total_cp}</div><div class="lbl">Cancelled Patents</div></div>
  <div class="num-cell"><div class="num rust">{substantive}</div><div class="lbl">Substantive</div></div>
  <div class="num-cell"><div class="num" style="color:#999">{administrative}</div><div class="lbl">Administrative</div></div>
  <div class="num-cell"><div class="num blue">{len(matches)}</div><div class="lbl">Cross-Matches</div></div>
  <div class="num-cell"><div class="num green">{len(set(r['tribe'] for r in cancelled))}</div><div class="lbl">Tribes</div></div>
</div>

<section>
  <h2>By Tribe</h2>
  <p>Tribes with 5 or more cancelled patents. Dark bars are substantive cancellations (1927/1931 Acts, refused, erroneously issued). Light bars are administrative corrections.</p>
  <div id="tribe-chart"></div>
</section>

<section>
  <h2>Cancellation Reasons</h2>
  <div id="reason-chart"></div>
</section>

<section>
  <h2>Cross-Reference: Testified AND Cancelled</h2>
  <p>Allottees who appear in both the Circular 2464 affidavits (sworn testimony about forced patenting) and the cancelled patents list. These are people who told the government what happened to them &mdash; and the government reversed the patent. {len([m for m in matches if m['confidence'] == 'high'])} high-confidence matches (allotment number + name), {len([m for m in matches if m['confidence'] == 'medium'])} medium-confidence (name or allotment only).</p>
  <div class="register-wrap">
    <table>
      <thead>
        <tr>
          <th>Confidence</th>
          <th>Affidavit Name</th>
          <th>Reservation</th>
          <th>Allotment</th>
          <th>What They Said</th>
          <th>Cancelled Patent Name</th>
          <th>Tribe (GLO)</th>
          <th>Reason</th>
          <th>Comments</th>
        </tr>
      </thead>
      <tbody id="match-tbody"></tbody>
    </table>
  </div>
</section>

<section>
  <h2>Complete Cancelled Patents Register</h2>
  <p>{total_cp} records. Filter by tribe, state, or reason.</p>
  <div class="filter-bar">
    <select id="f-tribe"><option value="">All tribes</option></select>
    <select id="f-state"><option value="">All states</option></select>
    <select id="f-reason"><option value="">All reasons</option></select>
    <input type="text" id="f-search" placeholder="Search names...">
  </div>
  <div class="register-wrap">
    <table>
      <thead>
        <tr><th>Name</th><th>Tribe</th><th>State</th><th>Allotment</th><th>Date</th><th>Reason</th><th>Comments</th></tr>
      </thead>
      <tbody id="cp-tbody"></tbody>
    </table>
  </div>
</section>

<script>
const data = {data};

// Tribe chart — stacked bars
const tMargin = {{top: 10, right: 80, bottom: 20, left: 200}};
const tWidth = 800;
const barH = 24;
const tHeight = data.tribes.length * barH + tMargin.top + tMargin.bottom;
const tSvg = d3.select('#tribe-chart').append('svg').attr('width', tWidth).attr('height', tHeight);
const tG = tSvg.append('g').attr('transform', `translate(${{tMargin.left}},${{tMargin.top}})`);

const tMax = d3.max(data.tribes, d => d.count);
const tX = d3.scaleLinear().domain([0, tMax]).range([0, tWidth - tMargin.left - tMargin.right]);
const tY = d3.scaleBand().domain(data.tribes.map(d => d.name)).range([0, tHeight - tMargin.top - tMargin.bottom]).padding(0.25);

// Administrative (light)
tG.selectAll('.bar-admin').data(data.tribes).enter().append('rect')
  .attr('x', 0).attr('y', d => tY(d.name)).attr('width', d => tX(d.count)).attr('height', tY.bandwidth())
  .attr('fill', '#D4CEC4');
// Substantive (dark) overlay
tG.selectAll('.bar-sub').data(data.tribes).enter().append('rect')
  .attr('x', 0).attr('y', d => tY(d.name)).attr('width', d => tX(d.substantive)).attr('height', tY.bandwidth())
  .attr('fill', '#A3542E');

tG.selectAll('.tlabel').data(data.tribes).enter().append('text')
  .attr('x', -8).attr('y', d => tY(d.name) + tY.bandwidth() / 2).attr('dy', '0.35em')
  .attr('text-anchor', 'end').attr('font-size', '11px').text(d => d.name);
tG.selectAll('.tcount').data(data.tribes).enter().append('text')
  .attr('x', d => tX(d.count) + 6).attr('y', d => tY(d.name) + tY.bandwidth() / 2).attr('dy', '0.35em')
  .attr('font-family', 'JetBrains Mono, monospace').attr('font-size', '10px').attr('fill', '#6B6358')
  .text(d => `${{d.count}} (${{d.substantive}} sub.)`);

// Reason chart
const rMargin = {{top: 10, right: 40, bottom: 20, left: 180}};
const rWidth = 600;
const rHeight = data.reasons.length * barH + rMargin.top + rMargin.bottom;
const rSvg = d3.select('#reason-chart').append('svg').attr('width', rWidth).attr('height', rHeight);
const rG = rSvg.append('g').attr('transform', `translate(${{rMargin.left}},${{rMargin.top}})`);

const rMax = d3.max(data.reasons, d => d.count);
const rX = d3.scaleLinear().domain([0, rMax]).range([0, rWidth - rMargin.left - rMargin.right]);
const rY = d3.scaleBand().domain(data.reasons.map(d => d.name)).range([0, rHeight - rMargin.top - rMargin.bottom]).padding(0.25);

const subReasons = new Set(['1927 Act', '1931 Act', '1927 & 1931 Acts', 'Acceptance refused', 'Erroneously issued']);
rG.selectAll('rect').data(data.reasons).enter().append('rect')
  .attr('x', 0).attr('y', d => rY(d.name)).attr('width', d => rX(d.count)).attr('height', rY.bandwidth())
  .attr('fill', d => subReasons.has(d.name) ? '#A3542E' : '#D4CEC4');
rG.selectAll('.rlabel').data(data.reasons).enter().append('text')
  .attr('x', -8).attr('y', d => rY(d.name) + rY.bandwidth() / 2).attr('dy', '0.35em')
  .attr('text-anchor', 'end').attr('font-size', '11px').text(d => d.name);
rG.selectAll('.rcount').data(data.reasons).enter().append('text')
  .attr('x', d => rX(d.count) + 6).attr('y', d => rY(d.name) + rY.bandwidth() / 2).attr('dy', '0.35em')
  .attr('font-family', 'JetBrains Mono, monospace').attr('font-size', '10px').attr('fill', '#6B6358')
  .text(d => d.count);

// Cross-reference matches table
const matchBody = document.getElementById('match-tbody');
data.matches.forEach(m => {{
  const tr = document.createElement('tr');
  const confTag = m.confidence === 'high' ? 'tag-high' : 'tag-medium';
  const subTag = subReasons.has(m.cp_reason) ? 'tag-sub' : 'tag-admin';
  tr.innerHTML = `
    <td><span class="tag ${{confTag}}">${{m.confidence}}</span></td>
    <td><strong>${{m.aff_name}}</strong></td>
    <td style="font-size:11px">${{m.aff_reservation}}</td>
    <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${{m.aff_allotment}}</td>
    <td style="font-size:11px;max-width:200px;font-style:italic">${{m.aff_consent}}</td>
    <td><strong>${{m.cp_name}}</strong></td>
    <td style="font-size:11px">${{m.cp_tribe}}</td>
    <td><span class="tag ${{subTag}}">${{m.cp_reason}}</span></td>
    <td style="font-size:11px">${{m.cp_comments}}</td>
  `;
  matchBody.appendChild(tr);
}});

// Cancelled patents register
const cpBody = document.getElementById('cp-tbody');
const fTribe = document.getElementById('f-tribe');
const fState = document.getElementById('f-state');
const fReason = document.getElementById('f-reason');
const fSearch = document.getElementById('f-search');

[...new Set(data.cancelled.map(r => r.tribe))].sort().forEach(v => {{
  if (v) fTribe.innerHTML += `<option value="${{v}}">${{v}}</option>`;
}});
[...new Set(data.cancelled.map(r => r.state))].sort().forEach(v => {{
  if (v) fState.innerHTML += `<option value="${{v}}">${{v}}</option>`;
}});
[...new Set(data.cancelled.map(r => r.reason))].sort().forEach(v => {{
  fReason.innerHTML += `<option value="${{v}}">${{v}}</option>`;
}});

function renderCP() {{
  const tribe = fTribe.value;
  const state = fState.value;
  const reason = fReason.value;
  const search = fSearch.value.toLowerCase();

  cpBody.innerHTML = '';
  data.cancelled.forEach(r => {{
    if (tribe && r.tribe !== tribe) return;
    if (state && r.state !== state) return;
    if (reason && r.reason !== reason) return;
    if (search && !r.name.toLowerCase().includes(search)) return;

    const subTag = r.is_substantive ? 'tag-sub' : 'tag-admin';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${{r.name}}</strong></td>
      <td style="font-size:11px">${{r.tribe}}</td>
      <td>${{r.state}}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:10px">${{r.allotment}}</td>
      <td style="font-size:11px">${{r.date}}</td>
      <td><span class="tag ${{subTag}}">${{r.reason}}</span></td>
      <td style="font-size:11px">${{r.comments}}</td>
    `;
    cpBody.appendChild(tr);
  }});
}}

fTribe.onchange = fState.onchange = fReason.onchange = fSearch.oninput = renderCP;
renderCP();
</script>
</body>
</html>"""
    return html


def main():
    print("Loading cancelled patents...")
    cancelled = load_cancelled_patents()
    print(f"  {len(cancelled)} records")

    print("Loading Circular 2464 affidavits...")
    affidavits = load_circular_2464()
    print(f"  {len(affidavits)} records")

    print("Cross-referencing...")
    matches = cross_reference(cancelled, affidavits)
    print(f"  {len(matches)} matches found")
    print(f"    High confidence: {sum(1 for m in matches if m['confidence'] == 'high')}")
    print(f"    Medium confidence: {sum(1 for m in matches if m['confidence'] == 'medium')}")

    # Show some matches
    print("\nSample matches:")
    for m in matches[:10]:
        aff = m['affidavit']
        cp = m['cancelled']
        print(f"  {aff['name']} (aff #{aff['allotment']}) ↔ {cp['name']} (cp #{cp['allotment']}) [{m['match_type']}, {m['confidence']}]")
        print(f"    Reason: {cp['reason']} | Testified: {aff['consent_text'][:80]}")

    html = build_html(cancelled, affidavits, matches)
    with open('viz_cancelled_patents.html', 'w') as f:
        f.write(html)
    print(f"\nWritten to viz_cancelled_patents.html")


if __name__ == "__main__":
    main()
