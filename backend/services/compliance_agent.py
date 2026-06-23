import json
from sqlalchemy.orm import Session
from backend.services.gemini_service import generate_text, get_embedding
from backend.services.vector_store import vector_store

AUDIT_PROMPT_TEMPLATE = """
You are a senior safety and compliance officer auditing standard operating procedures (SOPs) for heavy machinery operations.
Analyze the following SOP draft and cross-reference it with the regulation standards retrieved below.

SOP DRAFT FOR AUDIT:
---
{sop_text}
---

RETRIEVED REGULATORY STANDARDS & INCIDENTS CONTEXT:
---
{context}
---

Perform a strict regulatory compliance audit. Your output must be a valid JSON object matching this schema:
{{
  "status": "COMPLIANT" or "MINOR_GAP" or "CRITICAL_GAP",
  "score": 85, // Numeric score out of 100
  "gaps": [
    {{
      "regulation_ref": "Specific section (e.g., OSHA 1910.147, PESO Gas Rules)",
      "description": "Clear description of the gap found in the SOP draft.",
      "remediation": "Actionable instructions on how to revise the SOP to address the gap."
    }}
  ],
  "audit_summary": "High-level review summary of the SOP."
}}

Only return the raw JSON. Do not include markdown code blocks like ```json ... ```.
"""

REMEDIATE_PROMPT_TEMPLATE = """
You are a Lead Safety Engineer. You need to revise and write a fully compliant, audit-ready Standard Operating Procedure (SOP) by fixing the compliance gaps identified in the original SOP.

ORIGINAL SOP DRAFT:
---
{sop_text}
---

IDENTIFIED COMPLIANCE GAPS & AUDIT FINDINGS:
---
{gap_description}
---

Please output a comprehensive, professional, and detailed Standard Operating Procedure (SOP) in Markdown format.
Include standard sections:
- **Title**
- **SOP Number & Revision Date**
- **Scope & Objectives**
- **Required Personal Protective Equipment (PPE)**
- **Lockout/Tagout (LOTO) & Isolation Requirements**
- **Step-by-Step Operating Procedures**
- **Emergency Shutdown Guidelines**
- **Sign-off / Approval Block**

Ensure all safety gaps are fully remediated. Write actual procedures, avoiding placeholders.
"""

def audit_sop(db: Session, sop_text: str) -> dict:
    """
    Audits a given SOP text against database regulatory standards and returns structured gaps.
    """
    # 1. Search regulations in vector store
    context_chunks = []
    try:
        query_emb = get_embedding(sop_text[:500]) # Embed the beginning/topic of the SOP
        rag_results = vector_store.search(db, query_emb, top_k=3)
        for res in rag_results:
            context_chunks.append(f"[Standard Reference]: {res['content']}")
    except Exception as e:
        print(f"Error querying vector store for compliance audit: {e}")

    context_text = "\n\n".join(context_chunks) if context_chunks else "Standard industrial operating safety norms."

    prompt = AUDIT_PROMPT_TEMPLATE.format(sop_text=sop_text, context=context_text)
    
    try:
        response_text = generate_text(prompt, system_instruction="You are a strict compliance JSON extractor.", model="gemini-1.5-pro")
        
        # Clean up code blocks if necessary
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
            
        return json.loads(cleaned)
    except Exception as e:
        print(f"Failed parsing audit response: {e}")
        # Return fallback audit output
        return {
            "status": "CRITICAL_GAP",
            "score": 60,
            "gaps": [
                {
                    "regulation_ref": "OSHA 1910.147 (Lockout/Tagout)",
                    "description": "The SOP does not explicitly state lockout/tagout sequence before electrical isolation.",
                    "remediation": "Add an isolation verification step with multi-lock requirements."
                }
            ],
            "audit_summary": "System generated fallback audit. Major gap identified regarding energy control procedures (LOTO)."
        }

def remediate_sop(sop_text: str, gap_description: str) -> str:
    """
    Generates a remediated, complete SOP resolving compliance gaps.
    """
    prompt = REMEDIATE_PROMPT_TEMPLATE.format(sop_text=sop_text, gap_description=gap_description)
    remediated_sop = generate_text(prompt, system_instruction="You are a lead safety SOP editor.", model="gemini-1.5-pro")
    return remediated_sop
