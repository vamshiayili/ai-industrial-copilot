// API service wrapper for AI Industrial Copilot

const API_BASE = '/api';

export const ApiService = {
    // 1. RAG Query
    async queryRAG(query, sessionId = 'default') {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, session_id: sessionId })
        });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    },

    // 2. Upload Document PDF
    async uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/upload/document`, {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    },

    // 3. Upload Drawing
    async uploadDrawing(file, prompt) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('prompt', prompt);

        const response = await fetch(`${API_BASE}/upload/drawing`, {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    },

    // 4. Root Cause Analysis
    async runRCA(description, assetId = null) {
        const response = await fetch(`${API_BASE}/rca`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description, asset_id: assetId })
        });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    },

    // 5. Compliance Audit
    async auditSOP(sopText) {
        const response = await fetch(`${API_BASE}/compliance/audit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sop_text: sopText })
        });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    },

    // 6. Remediation
    async remediateSOP(sopText, gapDescription) {
        const response = await fetch(`${API_BASE}/compliance/remediate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sop_text: sopText, gap_description: gapDescription })
        });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    },

    // 7. Lessons Learned Checklist
    async runWarningChecklist(taskDescription) {
        const response = await fetch(`${API_BASE}/warning-checklist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_description: taskDescription })
        });
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    },

    // 8. Fetch Knowledge Graph
    async getGraphData() {
        const response = await fetch(`${API_BASE}/graph`);
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    },

    // 9. QR Scan Lookup
    async getAssetQRData(assetId) {
        const response = await fetch(`${API_BASE}/qr-scan/${assetId}`);
        if (!response.ok) throw new Error(await response.text());
        return response.json();
    }
};
