from sqlalchemy.orm import Session
from backend.database import IncidentLog, DocumentChunk
from backend.services.gemini_service import generate_text, get_embedding
from backend.services.vector_store import vector_store

RCA_PROMPT_TEMPLATE = """
You are an expert Lead Root Cause Analyst in industrial operations (chemical, power, and manufacturing plants).
Your task is to generate a comprehensive, professional **Root Cause Analysis (RCA) Report** for the following reported incident:

---
Incident Description:
{description}
---

Relevant Context from Past Incidents & Operator Manuals:
{context}

Please structure your report in markdown format with the following sections:
1. **Executive Summary**: Brief overview of the incident, severity, and key finding.
2. **5-Whys Analysis**: Perform a logical, step-by-step "5-Whys" drilldown to find the systemic root cause of the failure.
3. **Root Cause Categorization**: Classify the root cause (e.g., Mechanical Failure, Design Defect, Operating Procedure Gap, Human Factor, Environmental).
4. **Corrective & Preventive Actions (CAPA)**:
   - *Immediate Containment Actions*
   - *Long-Term Preventive Measures* (e.g. sensor interlocks, scheduling, PPE)
5. **Regulatory Compliance Implications**: Note if this breaches any standard standards (e.g., OSHA 1910, PESO, etc.).

Keep the tone formal, highly technical, and action-oriented.
"""

def generate_rca_report(db: Session, description: str, asset_id: str = None) -> str:
    """
    Retrieves context from vector store and databases, then generates an RCA report.
    """
    context_chunks = []
    
    # 1. Query vector store using the description as the search criteria
    try:
        query_emb = get_embedding(description)
        rag_results = vector_store.search(db, query_emb, top_k=3)
        for res in rag_results:
            context_chunks.append(f"[Manual Reference (Page {res.get('page_number', 'N/A')})]: {res['content']}")
    except Exception as e:
        print(f"Error querying vector store for RCA: {e}")
        
    # 2. Query SQLite Incident database for the specific asset or general keywords
    try:
        incident_query = db.query(IncidentLog)
        if asset_id:
            incident_query = incident_query.filter(IncidentLog.asset_id == asset_id)
        
        incidents = incident_query.limit(2).all()
        for inc in incidents:
            context_chunks.append(
                f"[Past Incident - '{inc.title}']: {inc.hazard_description}\n"
                f"Lessons learned: {inc.lessons_learned}"
            )
    except Exception as e:
        print(f"Error querying incident DB for RCA: {e}")
        
    context_text = "\n\n".join(context_chunks) if context_chunks else "No historical records or manual segments retrieved."
    
    prompt = RCA_PROMPT_TEMPLATE.format(description=description, context=context_text)
    
    system_instruction = "You are a senior industrial safety auditor. You draft technical RCA documents using 5-Whys logic."
    
    rca_report = generate_text(prompt, system_instruction=system_instruction, model="gemini-1.5-pro")
    
    return rca_report
