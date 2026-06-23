# AI Industrial Copilot (Unified Asset & Operations Brain)

An AI-powered Knowledge Intelligence Platform designed for heavy industry plants. It ingests heterogeneous documents, builds a dynamic knowledge graph, and deploys domain-expert agentic workflows for QA, safety, maintenance, compliance, and P&ID drawing analysis.

---

## 🚀 High-Impact Features (The "Wow" Factor)

1. **Multimodal P&ID / Drawing Vision Agent**
   - Upload engineering drawings (P&IDs, layout diagrams, schematics).
   - Use Gemini's multimodal vision capabilities to ask complex visual questions (e.g. identify safety check valves downstream of a pump, or verify line flow paths).

2. **Proactive Safety Warning Permit Builder (Lessons Learned)**
   - Inputs the technician's planned task (e.g., *"Replacing dynamic seals on Compressor-05 while Boiler-101 is running"*).
   - Dynamically checks past failure logs and near-miss manuals in SQLite to proactively raise alerts and generate a custom pre-job **Safe Work Permit Checklist**.

3. **Field-Tech Mobile Mode & QR Code Scanner (Speech-Enabled)**
   - Toggle a simulated smartphone view designed for operators on the plant floor.
   - Select and "scan" simulated equipment QR tags (Boiler-101, Compressor-05, Pump-A) to instantly fetch specifications, safety limits, and history.
   - Integrates browser-native **Web Speech API** for hands-free voice query input.

4. **Compliance Audit & SOP Remediation Gap Auditor**
   - Audits draft Standard Operating Procedures (SOPs) against regulatory safety guidelines (e.g., OSHA, PESO).
   - Computes a compliance health score, identifies critical safety gaps, and features an **"Auto-Generate Remediation SOP"** button to draft missing procedures.
   - Download the audit-ready final SOP as an exportable file.

5. **Dynamic Knowledge Graph Visualizer**
   - Renders an interactive 2D node-link graph of assets, regulations, maintenance teams, and documents using `vis-network`.
   - **Double-click** nodes to automatically fill the QA box and query their database manuals.

---

## 🛠️ Tech Stack & Architecture

- **Backend:** FastAPI (Python 3.14)
- **Database:** SQLite (SQLAlchemy) for metadata, incident logs, relationship graph, and chat sessions.
- **RAG & Vector Search:**
  - **Embeddings:** `text-embedding-004` (Gemini API)
  - **Vector Database:** 100% Python/NumPy native vector similarity engine (ensures zero compile errors on Windows, loaded into memory from SQLite).
- **LLM Engine:** Gemini API via Python SDK (`google-genai`) utilizing `gemini-1.5-pro` (reasoning, vision, auditing) and `gemini-1.5-flash` (permit generation, fast queries).
- **Frontend:** Responsive SPA using **Vanilla JS (ES6 modules)** and **Tailwind CSS (via CDN)**. Served statically from FastAPI with zero build steps or Node pathing issues.

---

## 📂 Directory Structure

```
ai-industrial-copilot/
├── backend/
│   ├── main.py                  # FastAPI Application + Endpoint Routing
│   ├── config.py                # Environment configs & API keys
│   ├── database.py              # SQLite schemas (Documents, Chunks, Relations, Incidents, Chats)
│   ├── requirements.txt         # Pip dependency list
│   ├── services/
│   │   ├── pdf_processor.py     # PDF parsing & text splitting (recursive page-by-page)
│   │   ├── vector_store.py      # Embedding generation & NumPy similarity engine
│   │   ├── gemini_service.py    # Core RAG, multimodal vision, and QA with citations
│   │   ├── rca_agent.py         # Root Cause Analysis agent (5-Whys)
│   │   ├── compliance_agent.py  # Regulatory compliance check & gap remediator
│   │   ├── warning_engine.py    # Incident risk analysis & safe permit checklist generator
│   │   └── graph_service.py     # Entity relationship extractor (AI-driven)
│   └── static/                  # Frontend single page app
│       ├── index.html           # Main dashboard
│       ├── css/
│       │   └── styles.css       # Obsidian-industrial design styles
│       └── js/
│           ├── app.js           # Router and main UI controller
│           ├── api.js           # API request layer
│           ├── graph.js         # Vis.js graph initializer & updater
│           └── qr_sim.js        # Simulated QR code generator & camera feed lookup
├── verify_all.py                # Integration testing verification script
└── README.md                    # Project documentation
```

---

## ⚡ Setup & Run Instructions

### 1. Install Dependencies
Make sure you have python installed, then run:
```bash
pip install -r backend/requirements.txt
```

### 2. Configure API Key
Configure your Gemini API key in your environment terminal:
- **Windows (PowerShell):** `$env:GEMINI_API_KEY="your-api-key-here"`
- **macOS/Linux:** `export GEMINI_API_KEY="your-api-key-here"`

*(Note: If no API key is specified, the application will automatically enter **mock-fallback mode**, generating simulated outputs so you can fully explore the UI.)*

### 3. Run Verification Tests
Verify all subsystems (database, NumPy search, agents) compile and pass tests:
```bash
python verify_all.py
```

### 4. Start the Application
Start the FastAPI server:
```bash
python -m uvicorn backend.main:app --reload
```

Open your browser and navigate to:
[http://localhost:8000](http://localhost:8000)

---

## 🧪 Verification Plan

- `verify_all.py` performs integration runs on database seeding, vector similarity ranking, 5-Whys generation, compliance gap analyses, and proactive permit warnings:
```
==================================================
   AI INDUSTRIAL COPILOT INTEGRATION TESTING      
==================================================

[1/6] Initializing Database & Seed Data...
  [OK] Database initialized.
  [OK] Seeded Incident Logs: 4
  [OK] Seeded Graph Relations: 7

[2/6] Testing Embedding API...
  [OK] Embedding generated successfully.
  [OK] Vector dimensions: 768

[3/6] Testing Vector Search Engine...
  [OK] Search query: 'How to prevent boiler valve lockup?'
  [OK] Found matches: 1
    - Match (Page 12) [Score: -0.0160]: 'WARNING: Boiler-101 feed lines...'

[4/6] Testing Root Cause Analysis Agent...
  [OK] RCA Report generated successfully.

[5/6] Testing Compliance Auditor Agent...
  [OK] SOP Audited successfully.
  [OK] Compliance Rating: CRITICAL_GAP (Score: 60)

[6/6] Testing Warning Permit Engine...
  [OK] Safety Permit & Warnings generated successfully.

==================================================
      ALL SERVICES INTEGRATION RUNS: PASSED       
==================================================
```