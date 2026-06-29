import os
import json
import uuid
import shutil
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.config import UPLOAD_DIR, STATIC_DIR
from backend.database import SessionLocal, init_db, Document, DocumentChunk, Relation, ChatHistory, IncidentLog
from backend.services.pdf_processor import process_pdf
from backend.services.vector_store import vector_store
from backend.services.gemini_service import get_embedding, generate_text, analyze_drawing
from backend.services.graph_service import extract_and_save_relations
from backend.services.rca_agent import generate_rca_report
from backend.services.compliance_agent import audit_sop, remediate_sop
from backend.services.warning_engine import generate_warning_checklist

app = FastAPI(title="AI Industrial Copilot API")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    init_db()
    # Pre-load vector store cache on startup
    db = SessionLocal()
    try:
        vector_store.initialize(db)
    finally:
        db.close()

# Pydantic Schemas for Requests
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"

class RCARequest(BaseModel):
    description: str
    asset_id: Optional[str] = None

class AuditRequest(BaseModel):
    sop_text: str

class RemediateRequest(BaseModel):
    sop_text: str
    gap_description: str

class WarningRequest(BaseModel):
    task_description: str

# ----------------- ENDPOINTS -----------------

@app.post("/api/upload/document")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests a PDF manual, chunks it, embeds it, and updates vector store & relations."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF manuals are supported.")
        
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Check if document already exists
    existing_doc = db.query(Document).filter(Document.filename == file.filename).first()
    if existing_doc:
        # Delete related chunks
        db.query(DocumentChunk).filter(DocumentChunk.document_id == existing_doc.id).delete()
        # Delete related relations
        db.query(Relation).filter(Relation.document_id == existing_doc.id).delete()
        db.delete(existing_doc)
        db.commit()

    # Save document entry
    doc = Document(filename=file.filename, filepath=str(file_path), doc_type="manual")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Process PDF and extract chunks
    chunks = process_pdf(str(file_path))
    
    print(f"Extracted {len(chunks)} chunks from {file.filename}.")
    
    # Embed and save each chunk
    all_chunks_text = []
    for chunk in chunks:
        content = chunk["content"]
        page_num = chunk["page_number"]
        idx = chunk["chunk_index"]
        
        all_chunks_text.append(content)
        
        # Generate embedding
        emb = get_embedding(content)
        
        db_chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=content,
            page_number=page_num,
            embedding_json=json.dumps(emb)
        )
        db.add(db_chunk)
        
    db.commit()
    
    # Reinitialize in-memory vector store cache
    vector_store.initialize(db)
    
    # Extract entity relationships using the full document context (combine some text for Gemini)
    combined_text = "\n".join(all_chunks_text[:5]) # Extract relations from first 5 pages/chunks to keep prompts reasonably sized
    extract_and_save_relations(db, combined_text, doc.id)
    
    return {"message": f"Successfully ingested {file.filename}.", "chunks_count": len(chunks), "document_id": doc.id}

@app.post("/api/upload/drawing")
async def upload_drawing(
    file: UploadFile = File(...),
    prompt: str = Form("Analyze this engineering drawing. Identify key equipment, loop controls, and safety check valves."),
    db: Session = Depends(get_db)
):
    """Handles visual engineering drawings / P&IDs uploads, analyzing them using Gemini Vision."""
    filename = file.filename
    file_path = UPLOAD_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Read bytes for multimodal API
    file.file.seek(0)
    img_bytes = file.file.read()
    
    mime_type = "image/png"
    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        mime_type = "image/jpeg"
    elif filename.endswith(".pdf"):
        mime_type = "application/pdf"
        
    # Save drawing metadata
    doc = Document(filename=filename, filepath=str(file_path), doc_type="drawing")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Run visual analysis
    analysis_result = analyze_drawing(img_bytes, mime_type, prompt)
    
    # Extract mock relation for graph based on drawings
    # Usually, we would run another text prompt on the analysis to get actual graph edges.
    # We will seed a relationship showing the drawing references some core system
    try:
        db.add(Relation(
            source=filename,
            target="Plant System Overview",
            rel_type="references",
            description="Drawing depicts flow loops and valves connected to the main unit.",
            document_id=doc.id
        ))
        db.commit()
    except Exception as e:
        print(f"Error saving drawing relation: {e}")
        
    return {
        "filename": filename,
        "analysis": analysis_result,
        "document_id": doc.id
    }

@app.post("/api/query")
def query_rag(payload: QueryRequest, db: Session = Depends(get_db)):
    """Executes a standard RAG search and answers user questions with structured citations."""
    query = payload.query
    session_id = payload.session_id
    
    # 1. Get embedding for the query
    q_emb = get_embedding(query)
    
    # 2. Search NumPy vector store
    search_results = vector_store.search(db, q_emb, top_k=4)
    
    # 3. Build prompt context
    context_parts = []
    citations = []
    
    for i, res in enumerate(search_results):
        # Fetch document filename
        doc = db.query(Document).filter(Document.id == res["document_id"]).first()
        filename = doc.filename if doc else "Unknown Manual"
        
        context_parts.append(
            f"Reference [{i+1}] (Source: {filename}, Page {res['page_number']}):\n{res['content']}"
        )
        citations.append({
            "citation_id": i + 1,
            "filename": filename,
            "page_number": res["page_number"],
            "snippet": res["content"][:200] + "...",
            "score": res["score"]
        })
        
    context_text = "\n\n".join(context_parts)
    
    # RAG prompt
    system_instruction = (
        "You are an AI Industrial Operations Expert. Answer the user's operational query strictly based "
        "on the references provided. For every key fact, explicitly reference the source citation ID "
        "like [1], [2], etc. If the references don't contain the answer, explain that you could not find "
        "it in the manual but provide generic safe procedures."
    )
    
    prompt = f"User Query: {query}\n\nReferences:\n{context_text}\n\nExpert Answer:"
    
    answer = generate_text(prompt, system_instruction=system_instruction, model="gemini-1.5-pro")
    
    # Record to chat history
    db.add(ChatHistory(session_id=session_id, role="user", message=query))
    db.add(ChatHistory(session_id=session_id, role="assistant", message=answer))
    db.commit()
    
    return {
        "answer": answer,
        "citations": citations
    }

@app.post("/api/rca")
def run_rca(payload: RCARequest, db: Session = Depends(get_db)):
    """Runs the RCA Agent to draft a markdown 5-Whys root cause analysis report."""
    report = generate_rca_report(db, payload.description, payload.asset_id)
    return {"report": report}

@app.post("/api/compliance/audit")
def run_compliance_audit(payload: AuditRequest, db: Session = Depends(get_db)):
    """Audits an uploaded/pasted SOP draft against guidelines and returns a gap report."""
    audit_results = audit_sop(db, payload.sop_text)
    return audit_results

@app.post("/api/compliance/remediate")
def run_compliance_remediation(payload: RemediateRequest):
    """Uses Gemini to compile a gap-remediated Standard Operating Procedure."""
    remediated_sop = remediate_sop(payload.sop_text, payload.gap_description)
    return {"remediated_sop": remediated_sop}

@app.post("/api/warning-checklist")
def run_warning_checklist(payload: WarningRequest, db: Session = Depends(get_db)):
    """Checks planned task against database incidents and issues warnings & permit checklists."""
    warning_response = generate_warning_checklist(db, payload.task_description)
    return {"permit_briefing": warning_response}

@app.get("/api/graph")
def get_knowledge_graph(db: Session = Depends(get_db)):
    """Returns nodes and edges representing the database relationship network for vis-network."""
    relations = db.query(Relation).all()
    
    nodes_set = set()
    edges = []
    
    # Asset groupings for frontend color visualization
    node_types = {}
    
    for rel in relations:
        nodes_set.add(rel.source)
        nodes_set.add(rel.target)
        
        edges.append({
            "from": rel.source,
            "to": rel.target,
            "label": rel.rel_type,
            "title": rel.description
        })
        
        # Categorize node types based on keywords or relationship types
        # Standardize categories: ASSET, REGULATION, TEAM, DRAWING
        for node in [rel.source, rel.target]:
            node_lower = node.lower()
            if "osha" in node_lower or "peso" in node_lower or "regulation" in node_lower or "standard" in node_lower:
                node_types[node] = "REGULATION"
            elif "team" in node_lower or "personnel" in node_lower or "maintenance" in node_lower or "operator" in node_lower:
                node_types[node] = "TEAM"
            elif node_lower.endswith(".pdf") or node_lower.endswith(".jpg") or node_lower.endswith(".png") or "drawing" in node_lower:
                node_types[node] = "DRAWING"
            else:
                node_types[node] = "ASSET" # Default category
                
    nodes = []
    for node_name in nodes_set:
        nodes.append({
            "id": node_name,
            "label": node_name,
            "group": node_types.get(node_name, "ASSET")
        })
        
    return {"nodes": nodes, "edges": edges}

@app.get("/api/qr-scan/{asset_id}")
def qr_code_lookup(asset_id: str, db: Session = Depends(get_db)):
    """Simulates scanning a plant physical QR tag, looking up history and safety procedures."""
    # Lookup historical failures
    incidents = db.query(IncidentLog).filter(IncidentLog.asset_id == asset_id).all()
    incident_history = [
        {"title": inc.title, "severity": inc.severity, "hazard": inc.hazard_description[:150] + "..."}
        for inc in incidents
    ]
    
    # Generic asset technical specs
    asset_specs = {
        "Boiler-101": {
            "name": "High-Pressure Steam Boiler (B-101)",
            "manufacturer": "Thermax Industrial Ltd",
            "install_date": "2019-04-12",
            "operating_temp": "220 C (Max 260 C)",
            "operating_pressure": "18 Bar (Safety Valve opens at 22 Bar)",
            "critical_sop": "SOP-BL-01 (Startup & Descaling Protocols)"
        },
        "Compressor-05": {
            "name": "Rotary Screw Gas Compressor (C-05)",
            "manufacturer": "Atlas Copco",
            "install_date": "2021-08-30",
            "operating_temp": "85 C",
            "operating_pressure": "7.5 Bar",
            "critical_sop": "SOP-COMP-05 (Dynamic Seal Overhaul)"
        },
        "Pump-A": {
            "name": "Centrifugal Feedwater Pump (P-02A)",
            "manufacturer": "Kirloskar Brothers",
            "install_date": "2020-02-15",
            "operating_temp": "65 C",
            "operating_pressure": "24 Bar",
            "critical_sop": "SOP-PUMP-02 (Priming & Overheating Interlocks)"
        }
    }
    
    specs = asset_specs.get(asset_id, {
        "name": f"Generic Equipment ({asset_id})",
        "manufacturer": "Standard Plant Spec",
        "install_date": "Unknown",
        "operating_temp": "N/A",
        "operating_pressure": "N/A",
        "critical_sop": "Standard Plant Operating Manual"
    })
    
    # Pre-defined checklist matching typical field LOTO needs
    safety_guidelines = [
        "Verify Lock-Out Tag-Out (LOTO) key is inserted and logged.",
        "Perform zero-pressure bleed down checks.",
        "Equip appropriate Level 2 protective eye wear and fire-retardant suit."
    ]
    
    if asset_id == "Compressor-05":
        safety_guidelines.append("WARNING: Active ignition sources (e.g., Boiler-101) within 15 meters must be shut down or heat shielded.")
    elif asset_id == "Boiler-101":
        safety_guidelines.append("Confirm steam safety valve SV-101 mechanical override lever is cleared of scale.")
        
    return {
        "asset_id": asset_id,
        "specs": specs,
        "incidents": incident_history,
        "safety_checks": safety_guidelines
    }

@app.post("/api/download/sop")
def download_remediated_sop(payload: RemediateRequest):
    """Endpoint generating a direct downloadable Markdown file file for remediation SOP."""
    # We can generate the remediated content right here, or just save the payload and return it.
    remediated_sop = remediate_sop(payload.sop_text, payload.gap_description)
    filename = f"remediated_sop_{uuid.uuid4().hex[:6]}.md"
    return PlainTextResponse(
        remediated_sop,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/markdown"
        }
    )

# Serve Frontend SPA
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
