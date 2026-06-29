import json
from sqlalchemy.orm import Session
from backend.database import Relation
from backend.services.gemini_service import generate_text
from backend.config import GEMINI_API_KEY

RELATION_EXTRACTION_PROMPT = """
You are a domain-expert knowledge engineer working in industrial plants.
Your task is to analyze the following document excerpt and extract relationships between key entities.
Entities should fall into these categories:
- ASSET (e.g., Boiler-101, Compressor-05, Pump-A, Tank-10, SV-101)
- REGULATION/STANDARD (e.g., OSHA-1910, PESO-2024, ISO-45001)
- PERSONNEL/TEAM (e.g., Maintenance Team A, Operations Lead, Safety Inspector)
- DOCUMENT (e.g., Operator Manual, Safety Log, Incident Report)

Extract the relationship triples in the following JSON format:
{{
  "relations": [
    {{
      "source": "Entity Name (use standard title case, e.g. Boiler-101, Compressor-05, OSHA-Standard-1910)",
      "target": "Entity Name (e.g. Pump-A, Maintenance Team A, etc.)",
      "rel_type": "one of: uses, maintains, references, controls, located_in, regulates",
      "description": "Short description of how they interact (1 sentence)"
    }}
  ]
}}

Only return the JSON. Do not include markdown code block formatting like ```json ... ```, just output the raw JSON text. If no relationships are found, return {{"relations": []}}.

Document Excerpt:
---
{text}
---
"""

def extract_and_save_relations(db: Session, text: str, document_id: int):
    """
    Calls Gemini to extract entity relationships from a text chunk and saves them to the DB.
    """
    prompt = RELATION_EXTRACTION_PROMPT.format(text=text)
    
    try:
        response_text = generate_text(prompt, system_instruction="You are a strict JSON extractor that identifies industrial relationships.")
        
        # Clean up any potential markdown formatting
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```"):
            lines = cleaned_response.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_response = "\n".join(lines).strip()
            
        data = json.loads(cleaned_response)
        relations_list = data.get("relations", [])
        
        db_relations = []
        for rel in relations_list:
            source = rel.get("source", "").strip()
            target = rel.get("target", "").strip()
            rel_type = rel.get("rel_type", "references").strip()
            description = rel.get("description", "").strip()
            
            if source and target:
                # Check for duplicates before adding
                exists = db.query(Relation).filter(
                    Relation.source == source,
                    Relation.target == target,
                    Relation.rel_type == rel_type
                ).first()
                
                if not exists:
                    db_relations.append(Relation(
                        source=source,
                        target=target,
                        rel_type=rel_type,
                        description=description,
                        document_id=document_id
                    ))
                    
        if db_relations:
            db.add_all(db_relations)
            db.commit()
            print(f"Extracted and saved {len(db_relations)} relationships from document {document_id}.")
            
    except Exception as e:
        print(f"Failed to extract relationships from text chunk: {e}")
        # In case of parsing failure, we don't throw to avoid interrupting document ingestion
        # Provide fallback mocked relation for testing if in mock mode
        if not GEMINI_API_KEY:
            try:
                db_relations = [
                    Relation(
                        source="Sample_OEM_Manual.pdf",
                        target="Boiler-101",
                        rel_type="references",
                        description="Manual describes operating limits and startup procedures.",
                        document_id=document_id
                    ),
                    Relation(
                        source="Sample_OEM_Manual.pdf",
                        target="Compressor-05",
                        rel_type="references",
                        description="Manual contains dynamic seal overhaul sequence.",
                        document_id=document_id
                    )
                ]
                db.add_all(db_relations)
                db.commit()
                print("Seeded fallback mock relations since API key is missing.")
            except Exception as db_err:
                print(f"Failed to seed fallback mock relations: {db_err}")
