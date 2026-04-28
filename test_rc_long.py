import urllib.request, json, time

key = 'sk-d392dfeafc9b4ae08aeafece8e97c837'
url = 'https://open-webui.rc.virginia.edu/api/chat/completions'

# Build a ~5000 character prompt to test timeout behavior
text = """John W. Clendening, Clerk in Charge, Kaw Sub-agency, 24 years in the Service, Kaw, Oklahoma, Pawnee Agency.
In reply to your inquiry concerning Indians who have had the restrictions removed from their lands, I will say that many Kaw Indians are scattered, so that my report will not be definite in each case; but I have decided to make a list of all Kaw Indians to whom restricted deeds were issued and who have since been given a certificate of competency.
Indians on reservations where trust patents were issued may have the restrictions removed from all or part of their lands, but if a Kaw Indian is given a certificate of competency it removes the restrictions from all of his homestead. His inherited land, if any, remains restricted unless a special certificate is given, specifying such inheritance.
Emmet Tayiah, age 31, 4/4 blood, Pawhuska, Okla. Land sold, money spent, lives with Osage.
Harry Stubbs, age 30, 1/2 blood, Kaw, Okla. Land sold, money spent, inheritance spent. Wife restricted, but trying to get certificate.
Helen Jones Burnett, age 24, 1/2 blood, Kaw, Okla. Land sold. Husband and money both gone.
Claude McCauley, age 46, 4/4 blood, Kaw, Okla. Land sold, money gone. Has 160 inherited.
Barclay Delano, age 47, 4/4 blood, Kaw, Okla. Land sold. Funds gone. Living off his friends. Red Cross and neighbors cared for him in a long sick spell last year. Poor health.
Abby Conn, age 43, 4/4 blood, Kaw, Okla. Land sold. Money spent. Has some inheritance.
Ralph Pepper, age 26, 4/4 blood, Kaw, Okla. Land sold, money spent. Has some inheritance.
Forrest Chouteau, age 45, 4/4 blood, Kaw, Okla. Has left 934 acres of land, besides town home. Farms his land and has good family and home.
Henry Wy-e-nah-she, age 31, 4/4 blood. Land sold. Allottee broke. Lives with other tribes. Works part of time.
James Wy-e-nah-she, age 36, 4/4 blood, Kaw, Okla. Land Sold. Money gone. Works part of time. Able-bodied.
Theodore Sumner, age 26, 4/4 blood, Newkirk, Okla. Land sold. Wife has house and lots in her name. Strong and able to work.
Robert Sands, age 45, 4/4 blood. Land sold. Money spent. Nothing left. Lived long time at Pawhuska. Not located now. Strong and ablebodied.
Behesa Burnett (Myrtle Burnett), age 27, 4/4 blood. Land has mortgage. Husband not working regularly this year. Has inheritance.
Leona Taylor Wy-e-nah-she, age 22, 4/4 blood, Kaw, Okla. Land sold, and funds spent. Some inheritance left. She is incompetent.
Peter Taylor, age 37, 4/4 blood, Kaw, Okla. Land sold, and Indian broke. Has a little inheritance. Able to work, which he does when he can not sponge his way.
Oliver Thompson, age 44, 4/4 blood, Kaw, Okla. Land sold. Money spent long ago, and living from rental of minor son's allotment. He is consumptive. Owns nothing.
Leece Johnson, age 44, 4/4 blood, Hominy, Okla. Land sold. Spent part of funds for whiskey, wasted the balance. Not much account."""

# Repeat to make it ~20K chars
text = text * 4

msg = "You are extracting structured data from a historical document about Native American land dispossession. "
msg += "Extract ALL named entities, fee patents, and relationships as JSON. "
msg += "Return a JSON object with keys: entities, fee_patents, relationships. "
msg += "Text:\n\n" + text

payload = json.dumps({
    'model': 'Kimi K2.5',
    'messages': [{'role': 'user', 'content': msg}],
    'max_tokens': 8192,
    'temperature': 0.3,
}).encode()

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + key
}

print(f"Sending {len(msg)} chars ({len(payload)} bytes) to RC GenAI...")
start = time.time()
req = urllib.request.Request(url, data=payload, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=600)
    elapsed = time.time() - start
    data = json.loads(resp.read().decode())
    content = data['choices'][0]['message']['content']
    tokens = data.get('usage', {})
    print(f"SUCCESS in {elapsed:.1f}s")
    print(f"Tokens: {tokens}")
    print(f"Content length: {len(content)} chars")
    print(f"First 300 chars: {content[:300]}")
except Exception as e:
    elapsed = time.time() - start
    print(f"FAILED after {elapsed:.1f}s: {e}")
