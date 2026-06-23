# Integration Verification Script - AI Industrial Copilot
import sys
import os
import json
import numpy as np

# Adjust python path to import backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import init_db, SessionLocal, IncidentLog, Relation, Document, DocumentChunk
from backend.services.vector_store import vector_store
from backend.services.gemini_service import get_embedding, generate_text
from backend.services.rca_agent import generate_rca_report
from backend.services.compliance_agent import audit_sop
from backend.services.warning_engine import generate_warning_checklist

def run_tests():
    print("==================================================")
    print("   AI INDUSTRIAL COPILOT INTEGRATION TESTING      ")
    print("==================================================")

    # 1. Database Initialization
    print("\n[1/6] Initializing Database & Seed Data...")
    try:
        init_db()
        db = SessionLocal()
        inc_count = db.query(IncidentLog).count()
        rel_count = db.query(Relation).count()
        print(f"  [OK] Database initialized.")
        print(f"  [OK] Seeded Incident Logs: {inc_count}")
        print(f"  [OK] Seeded Graph Relations: {rel_count}")
        db.close()
    except Exception as e:
        print(f"  [ERROR] Database initialization FAILED: {e}")
        return False

    # 2. Embedding Verification
    print("\n[2/6] Testing Embedding API...")
    try:
        test_text = "Standard LOTO procedure for high pressure valves"
        emb = get_embedding(test_text)
        print(f"  [OK] Embedding generated successfully.")
        print(f"  [OK] Vector dimensions: {len(emb)} (Expected 768)")
        if len(emb) != 768:
            print("  [WARNING] Unexpected dimensions size.")
    except Exception as e:
        print(f"  [ERROR] Embedding API FAILED: {e}")
        return False

    # 3. Vector Similarity Store Verification
    print("\n[3/6] Testing Vector Search Engine...")
    try:
        db = SessionLocal()
        # Seed a mockup chunk
        mock_doc = db.query(Document).filter(Document.filename == "test_manual.pdf").first()
        if not mock_doc:
            mock_doc = Document(filename="test_manual.pdf", filepath="mock_path", doc_type="manual")
            db.add(mock_doc)
            db.commit()
            db.refresh(mock_doc)

        dummy_text = "WARNING: Boiler-101 feed lines must be cleared of scale buildup to prevent mechanical override lockup."
        dummy_emb = get_embedding(dummy_text)
        
        # Clean existing test chunks if any
        db.query(DocumentChunk).filter(DocumentChunk.document_id == mock_doc.id).delete()
        db.commit()

        db_chunk = DocumentChunk(
            document_id=mock_doc.id,
            chunk_index=0,
            content=dummy_text,
            page_number=12,
            embedding_json=json.dumps(dummy_emb)
        )
        db.add(db_chunk)
        db.commit()
        db.refresh(db_chunk)

        # Initialize vector store
        vector_store.initialize(db)

        # Query search
        query = "How to prevent boiler valve lockup?"
        query_emb = get_embedding(query)
        results = vector_store.search(db, query_emb, top_k=2)

        print(f"  [OK] Search query: '{query}'")
        print(f"  [OK] Found matches: {len(results)}")
        for res in results:
            print(f"    - Match (Page {res['page_number']}) [Score: {res['score']:.4f}]: '{res['content'][:60]}...'")

        if len(results) == 0:
            print("  [ERROR] Vector search returned 0 matches.")
            return False

        db.close()
    except Exception as e:
        print(f"  [ERROR] Vector Store test FAILED: {e}")
        return False

    # 4. Agent Workflows: RCA Agent
    print("\n[4/6] Testing Root Cause Analysis Agent...")
    try:
        db = SessionLocal()
        description = "Boiler-101 pressure spiked because SV-101 safety override level got stuck."
        rca_report = generate_rca_report(db, description, "Boiler-101")
        print("  [OK] RCA Report generated successfully.")
        print(f"  [OK] Report length: {len(rca_report)} characters")
        print(f"  --- Snippet ---\n{rca_report[:200]}\n  ...")
        db.close()
    except Exception as e:
        print(f"  [ERROR] RCA Agent FAILED: {e}")
        return False

    # 5. Agent Workflows: Compliance Audit
    print("\n[5/6] Testing Compliance Auditor Agent...")
    try:
        db = SessionLocal()
        sop = "Task: Change dynamic seals on Compressor-05. Step 1: Open panel doors. Step 2: Extract seal rings. Step 3: Swap."
        audit = audit_sop(db, sop)
        print("  [OK] SOP Audited successfully.")
        print(f"  [OK] Compliance Rating: {audit.get('status')} (Score: {audit.get('score')})")
        print(f"  [OK] Gaps found: {len(audit.get('gaps', []))}")
        for gap in audit.get('gaps', []):
            print(f"    - Ref: {gap.get('regulation_ref')}: {gap.get('description')[:60]}...")
        db.close()
    except Exception as e:
        print(f"  [ERROR] Compliance Auditor FAILED: {e}")
        return False

    # 6. Agent Workflows: Warning Permit Engine
    print("\n[6/6] Testing Warning Permit Engine...")
    try:
        db = SessionLocal()
        task = "Clean boiler feedwater tube and check pressure valves on Boiler-101."
        permit = generate_warning_checklist(db, task)
        print("  [OK] Safety Permit & Warnings generated successfully.")
        print(f"  [OK] Permit length: {len(permit)} characters")
        print(f"  --- Snippet ---\n{permit[:200]}\n  ...")
        db.close()
    except Exception as e:
        print(f"  [ERROR] Warning Permit Engine FAILED: {e}")
        return False

    print("\n==================================================")
    print("      ALL SERVICES INTEGRATION RUNS: PASSED       ")
    print("==================================================")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
