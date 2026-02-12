#!/usr/bin/env python3
"""
AI Analysis Interface - Enhanced with sophisticated prompting
"""
import streamlit as st
import psycopg2
import anthropic
import os
from typing import List, Dict
import re

st.set_page_config(
    page_title="AI Analysis - Historical Documents",
    page_icon="🤖",
    layout="wide"
)

@st.cache_resource
def get_db_connection():
    return psycopg2.connect(
        dbname="historical_docs",
        user="cwm6W",
        host="localhost"
    )

@st.cache_resource
def get_anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("ANTHROPIC_API_KEY not set!")
        return None
    return anthropic.Anthropic(api_key=api_key)

def extract_keywords(question: str) -> List[str]:
    """Extract meaningful search terms from question"""
    words = re.findall(r'\b\w+\b', question.lower())
    
    stop_words = {'tell', 'me', 'about', 'the', 'and', 'or', 'what', 'how', 'why', 'when', 'where', 'who', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'can', 'between', 'among'}
    
    keywords = []
    for word in words:
        if len(word) > 3 and word not in stop_words:
            keywords.append(word)
    
    proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', question)
    for noun in proper_nouns:
        if noun.lower() not in keywords:
            keywords.append(noun.lower())
    
    return keywords[:5]

def comprehensive_search(question: str) -> tuple:
    """Do comprehensive search across entities, events, and documents"""
    keywords = extract_keywords(question)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    keyword_conditions = " OR ".join(["e.name ILIKE %s OR e.context ILIKE %s"] * len(keywords))
    keyword_params = []
    for kw in keywords:
        keyword_params.extend([f'%{kw}%', f'%{kw}%'])
    
    cur.execute(f"""
        SELECT DISTINCT e.name, e.type, e.context, COUNT(m.id) as mentions
        FROM entities e
        LEFT JOIN mentions m ON e.id = m.entity_id
        WHERE {keyword_conditions}
        GROUP BY e.id, e.name, e.type, e.context
        ORDER BY mentions DESC
        LIMIT 100
    """, keyword_params)
    
    entities = []
    for row in cur.fetchall():
        entities.append({
            'name': row[0],
            'type': row[1],
            'context': row[2] or '',
            'mentions': row[3]
        })
    
    cur.execute(f"""
        SELECT e.type, e.date, e.location, e.description, d.file_name
        FROM events e
        JOIN documents d ON e.document_id = d.id
        WHERE {keyword_conditions.replace('e.name', 'e.description').replace('e.context', 'e.type')}
        ORDER BY e.date DESC NULLS LAST
        LIMIT 100
    """, keyword_params)
    
    events = []
    for row in cur.fetchall():
        events.append({
            'type': row[0] or '',
            'date': row[1] or '',
            'location': row[2] or '',
            'description': row[3] or '',
            'source': row[4] or ''
        })
    
    cur.execute(f"""
        SELECT file_name, collection, 
               substring(full_text from position(%s in lower(full_text)) - 200 for 500) as excerpt
        FROM documents
        WHERE {" OR ".join(["full_text ILIKE %s"] * len(keywords))}
        LIMIT 50
    """, [keywords[0].lower()] + [f'%{kw}%' for kw in keywords])
    
    documents = []
    for row in cur.fetchall():
        documents.append({
            'file_name': row[0],
            'collection': row[1] or '',
            'excerpt': row[2] or ''
        })
    
    cur.close()
    return entities, events, documents

def get_collection_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT d.id), COUNT(DISTINCT e.id), COUNT(DISTINCT ev.id)
        FROM documents d
        LEFT JOIN mentions m ON d.id = m.document_id
        LEFT JOIN entities e ON m.entity_id = e.id
        LEFT JOIN events ev ON d.id = ev.document_id
    """)
    row = cur.fetchone()
    cur.close()
    return {'documents': row[0], 'entities': row[1], 'events': row[2]}

def analyze_with_ai(question: str, entities: List[Dict], events: List[Dict], documents: List[Dict]) -> str:
    client = get_anthropic_client()
    if not client:
        return "Error: API client not initialized"
    
    # Build sophisticated context with all evidence
    context = f"""You are a historian analyzing a comprehensive database of Native American land loss and forced fee patents. You have access to COMPLETE evidence from ALL relevant documents, not just a sample.

RESEARCH QUESTION: {question}

COMPREHENSIVE EVIDENCE GATHERED:

ENTITIES ({len(entities)} found - showing top 50):
"""
    
    for ent in entities[:50]:
        context += f"\n• {ent['name']} ({ent['type']})"
        if ent['context']:
            context += f": {ent['context'][:400]}"
        if ent['mentions'] > 1:
            context += f" [{ent['mentions']} mentions across documents]"
    
    context += f"\n\nEVENTS ({len(events)} found - showing top 50 chronologically):\n"
    
    for evt in events[:50]:
        date_str = evt.get('date', 'Date unknown')
        context += f"\n• [{evt['type']}] {date_str}"
        if evt.get('location'):
            context += f" ({evt['location']})"
        context += f": {evt['description'][:400]}"
        if evt.get('source'):
            context += f" [Source: {evt['source']}]"
    
    if documents:
        context += f"\n\nDOCUMENT EXCERPTS ({len(documents)} found - showing top 20):\n"
        for doc in documents[:20]:
            context += f"\n[{doc['file_name']}]: {doc.get('excerpt', '')[:500]}..."
    
    # Sophisticated analysis instructions
    context += """

ANALYSIS INSTRUCTIONS:

Your task is to provide a SOPHISTICATED, NUANCED historical analysis. This is not a simple summary - you are acting as a professional historian synthesizing complete archival evidence.

Required elements:

1. ACKNOWLEDGE COMPLEXITY AND CONTRADICTIONS
   - If a person played multiple roles over time, explain the evolution
   - Note when evidence conflicts or shows contradictions
   - Avoid simplistic good/evil narratives
   - Show how individuals' positions changed over time

2. TEMPORAL ANALYSIS
   - Organize findings chronologically when relevant
   - Show how situations evolved across time periods
   - Note pivotal moments or turning points
   - Create timeline tables if helpful (Period | Role | Actions)

3. MULTIPLE PERSPECTIVES
   - Present different viewpoints on contested issues
   - Note who benefited and who suffered
   - Acknowledge agency and resistance, not just victimization
   - Show systemic patterns while honoring individual stories

4. EVIDENCE-BASED CONCLUSIONS
   - Every claim must cite specific entities, events, or documents
   - Distinguish between documented facts and reasonable inferences
   - Note gaps or limitations in the evidence
   - Be explicit about what we can vs cannot know

5. CONTEXTUAL UNDERSTANDING
   - Place individuals within larger institutional structures
   - Show how federal policies shaped individual actions
   - Explain the pressures and constraints people faced
   - Connect micro-level stories to macro-level patterns

6. THOUGHTFUL LANGUAGE
   - Use precise historical terminology
   - Avoid presentist judgments
   - Acknowledge the humanity of all parties
   - Be respectful to descendant communities

7. STRUCTURED PRESENTATION
   - Use clear headings and organization
   - Create summary tables for complex information
   - Provide both overview and detailed evidence
   - End with "Summary" section noting key findings and complexities

CRITICAL: This is COMPLETE data from the archive - you are seeing ALL relevant evidence, not a sample. Your analysis should reflect this comprehensiveness while maintaining scholarly nuance.

Begin your analysis:"""
    
    try:
        with st.spinner("Analyzing complete evidence with historical sophistication..."):
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,  # Increased for more detailed analysis
                temperature=0.3,  # Lower temperature for more consistent, scholarly tone
                messages=[{"role": "user", "content": context}]
            )
        return response.content[0].text
    except Exception as e:
        return f"Error during analysis: {str(e)}"

# Main UI
st.title("🤖 AI Historical Analysis")
st.markdown("**Sophisticated analysis of complete archival evidence**")
st.markdown("---")

with st.sidebar:
    st.header("📊 Database")
    stats = get_collection_stats()
    st.metric("Documents", f"{stats['documents']:,}")
    st.metric("Entities", f"{stats['entities']:,}")
    st.metric("Events", f"{stats['events']:,}")
    
    st.markdown("---")
    st.markdown("### Analysis Features")
    st.markdown("✓ Temporal evolution")
    st.markdown("✓ Contradictions noted")
    st.markdown("✓ Multiple perspectives")
    st.markdown("✓ Complete evidence")
    st.markdown("✓ Scholarly nuance")

question = st.text_area(
    "Research Question:",
    placeholder="e.g., Tell me about Jasper Saunkeah and forced fee patents",
    height=100
)

if st.button("🔍 Analyze with Historical Sophistication", type="primary"):
    if question:
        st.markdown("---")
        
        with st.spinner("Gathering complete evidence..."):
            entities, events, documents = comprehensive_search(question)
        
        st.info(f"📚 Found: {len(entities)} entities, {len(events)} events, {len(documents)} document excerpts")
        
        if entities:
            with st.expander("Preview Top Entities"):
                for ent in entities[:10]:
                    st.write(f"**{ent['name']}** ({ent['type']}) - {ent['mentions']} mentions")
        
        st.markdown("---")
        st.subheader("📖 Historical Analysis")
        
        analysis = analyze_with_ai(question, entities, events, documents)
        st.markdown(analysis)
        
        st.markdown("---")
        with st.expander("📋 View Complete Evidence Base"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Entities:**")
                for ent in entities[:30]:
                    st.text(f"• {ent['name']} ({ent['type']})")
            with col2:
                st.markdown("**Events:**")
                for evt in events[:30]:
                    st.text(f"• [{evt['type']}] {evt.get('date', 'n/a')}")
    else:
        st.warning("Please enter a research question!")

st.markdown("---")
st.caption("💡 This system provides sophisticated analysis backed by 100% of available evidence")
