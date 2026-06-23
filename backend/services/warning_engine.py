import re
from sqlalchemy.orm import Session
from backend.database import IncidentLog
from backend.services.gemini_service import generate_text, get_embedding
from backend.services.vector_store import vector_store

WARNING_PROMPT_TEMPLATE = """
You are a senior Plant Safety Supervisor issuing a Safe Work Permit (SWP) checklist and safety warning alert.
A technician is planning the following maintenance task:

PLANNING TASK:
---
{task_description}
---

HISTORICAL FAILURE & NEAR-MISS CONTEXT (Retrieved from Database):
{incident_context}

Based on this, generate a Safety Briefing and Permit Checklist.
Structure your response in Markdown:

### ⚠️ CRITICAL SAFETY WARNINGS
Provide 2-3 high-impact, bold warnings based on past incidents and the current plant state. (e.g., "Adjacent heat source Boiler-101 is active. If Compressor-05 leaks, immediate ignition hazard!").

### 📋 PRE-JOB SAFETY PERMIT CHECKLIST
Generate a concrete, step-by-step checklist the technician MUST check off before starting work.
Each item must be specific (e.g., "- [ ] Lockout/Tagout (LOTO) on inlet valve V-102 and verify zero pressure").

### 💡 HISTORICAL LESSONS LEARNED
Summarize why these precautions are necessary based on past incidents (e.g. "In 2024, a flash fire occurred because...").
"""

def generate_warning_checklist(db: Session, task_description: str) -> str:
    """
    Scans the planned task, retrieves relevant incidents, and builds safety warning permit checklists.
    """
    # 1. Look for asset names in the text (e.g. Compressor-05, Boiler-101, Pump-A)
    # Let's extract words resembling asset IDs (alphanumeric with hyphens/numbers)
    potential_assets = re.findall(r'[a-zA-Z]+-\d+', task_description)
    
    # 2. Query incidents matching those assets
    incidents = []
    if potential_assets:
        incidents = db.query(IncidentLog).filter(IncidentLog.asset_id.in_(potential_assets)).all()
        
    # If no direct asset match, perform a backup keyword query on incidents
    if not incidents:
        # Search for words like "compressor", "boiler", "pump", "valve"
        keywords = ["compressor", "boiler", "pump", "seal", "valve", "electrical"]
        matched_keywords = [kw for kw in keywords if kw in task_description.lower()]
        
        if matched_keywords:
            query_filter = IncidentLog.hazard_description.like(f"%{matched_keywords[0]}%")
            for kw in matched_keywords[1:]:
                query_filter = query_filter | IncidentLog.hazard_description.like(f"%{kw}%")
            incidents = db.query(IncidentLog).filter(query_filter).limit(3).all()
            
    # Compile incident context
    incident_context_parts = []
    for inc in incidents:
        incident_context_parts.append(
            f"- Incident: {inc.title} (Asset: {inc.asset_id})\n"
            f"  Hazard: {inc.hazard_description}\n"
            f"  Safety precaution: {inc.safety_precaution}\n"
            f"  Lessons Learned: {inc.lessons_learned}"
        )
        
    # Fallback default context if none found
    if not incident_context_parts:
        incident_context_parts.append(
            "- No direct historical incident records match the specific equipment. Apply standard LOTO and hot-work safety procedures."
        )
        
    incident_context = "\n\n".join(incident_context_parts)
    
    prompt = WARNING_PROMPT_TEMPLATE.format(
        task_description=task_description,
        incident_context=incident_context
    )
    
    system_instruction = "You are a plant safety director. You write warning permits and safety checklists to prevent industrial injuries."
    
    response = generate_text(prompt, system_instruction=system_instruction, model="gemini-1.5-flash")
    
    return response
