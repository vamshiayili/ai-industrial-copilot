import { ApiService } from './api.js';
import { GraphVisualizer } from './graph.js';
import { QRScannerSim } from './qr_sim.js';

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

const App = {
    init() {
        this.currentSessionId = `session-${Math.random().toString(36).substr(2, 9)}`;
        this.cacheDom();
        this.bindEvents();
        this.initTabs();
        this.initUploads();
        
        // Initialize QR Simulator
        QRScannerSim.init('qr-asset-select', 'qr-result-body', 'mobile-mic-btn', 'mobile-chat-input');
        
        console.log("AI Industrial Copilot frontend loaded. Session ID:", this.currentSessionId);
    },

    cacheDom() {
        // Tab buttons and views
        this.tabBtns = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');

        // Mobile Mode toggles
        this.mobileModeToggle = document.getElementById('mobile-mode-toggle');
        this.desktopLayout = document.getElementById('desktop-layout');
        this.mobileLayout = document.getElementById('mobile-layout');

        // Copilot / QA
        this.chatForm = document.getElementById('chat-form');
        this.chatInput = document.getElementById('chat-input');
        this.chatMessages = document.getElementById('chat-messages');
        this.citationsList = document.getElementById('citations-list');

        // Document Uploader
        this.docUploadZone = document.getElementById('doc-upload-zone');
        this.docFileInput = document.getElementById('doc-file-input');
        this.ingestionLogs = document.getElementById('ingestion-logs');

        // Drawings / P&ID
        this.drawingUploadZone = document.getElementById('drawing-upload-zone');
        this.drawingFileInput = document.getElementById('drawing-file-input');
        this.drawingPromptInput = document.getElementById('drawing-prompt-input');
        this.drawingAnalysisResult = document.getElementById('drawing-analysis-result');
        this.submitDrawingBtn = document.getElementById('submit-drawing-btn');
        this.drawingPreview = document.getElementById('drawing-preview');

        // RCA
        this.rcaForm = document.getElementById('rca-form');
        this.rcaDescription = document.getElementById('rca-description');
        this.rcaAssetId = document.getElementById('rca-asset-id');
        this.rcaReportOutput = document.getElementById('rca-report-output');

        // Compliance
        this.complianceForm = document.getElementById('compliance-form');
        this.sopTextarea = document.getElementById('sop-textarea');
        this.complianceResults = document.getElementById('compliance-results');
        
        // Warnings
        this.warningsForm = document.getElementById('warnings-form');
        this.taskDescriptionInput = document.getElementById('task-description-input');
        this.warningsOutput = document.getElementById('warnings-output');

        // Mobile QA inside Simulator
        this.mobileChatForm = document.getElementById('mobile-chat-form');
        this.mobileChatInput = document.getElementById('mobile-chat-input');
        this.mobileChatMessages = document.getElementById('mobile-chat-messages');
    },

    bindEvents() {
        // Toggle mobile mock view
        if (this.mobileModeToggle) {
            this.mobileModeToggle.addEventListener('click', () => {
                const isMobile = this.mobileLayout.classList.contains('hidden');
                if (isMobile) {
                    this.mobileLayout.classList.remove('hidden');
                    this.desktopLayout.classList.add('hidden');
                    this.mobileModeToggle.innerHTML = '🖥️ Switch to Plant Control Center';
                } else {
                    this.mobileLayout.classList.add('hidden');
                    this.desktopLayout.classList.remove('hidden');
                    this.mobileModeToggle.innerHTML = '📱 Simulate Field Tech Mobile Mode';
                }
            });
        }

        // Desktop Chat Submit
        if (this.chatForm) {
            this.chatForm.addEventListener('submit', (e) => this.handleDesktopChat(e));
        }

        // Mobile Chat Submit
        if (this.mobileChatForm) {
            this.mobileChatForm.addEventListener('submit', (e) => this.handleMobileChat(e));
        }

        // RCA Generate
        if (this.rcaForm) {
            this.rcaForm.addEventListener('submit', (e) => this.handleRCAGeneration(e));
        }

        // Compliance Audit Submit
        if (this.complianceForm) {
            this.complianceForm.addEventListener('submit', (e) => this.handleComplianceAudit(e));
        }

        // Proactive Safety Warning Permit Checklist
        if (this.warningsForm) {
            this.warningsForm.addEventListener('submit', (e) => this.handleWarningPermit(e));
        }
    },

    initTabs() {
        this.tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.getAttribute('data-tab');
                
                this.tabBtns.forEach(b => b.classList.remove('active'));
                this.tabContents.forEach(c => c.classList.add('hidden'));

                btn.classList.add('active');
                const targetEl = document.getElementById(`${targetTab}-tab`);
                if (targetEl) targetEl.classList.remove('hidden');

                // Load graph dynamically when clicking graph tab
                if (targetTab === 'graph') {
                    this.loadKnowledgeGraph();
                }
            });
        });
    },

    initUploads() {
        // Document upload drag & drop
        this.setupDragAndDrop(this.docUploadZone, this.docFileInput, (file) => this.handleDocUpload(file));
        // Drawing upload drag & drop
        this.setupDragAndDrop(this.drawingUploadZone, this.drawingFileInput, (file) => this.handleDrawingPreview(file));

        if (this.submitDrawingBtn) {
            this.submitDrawingBtn.addEventListener('click', () => {
                const file = this.drawingFileInput.files[0];
                if (file) {
                    this.handleDrawingUpload(file);
                } else {
                    alert("Please select or drop an engineering drawing first.");
                }
            });
        }
    },

    setupDragAndDrop(zone, input, onFileSelect) {
        if (!zone || !input) return;

        zone.addEventListener('click', () => input.click());

        input.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                onFileSelect(e.target.files[0]);
            }
        });

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                input.files = e.dataTransfer.files;
                onFileSelect(e.dataTransfer.files[0]);
            }
        });
    },

    // ----------------- FEATURE HANDLERS -----------------

    // Ingest Manual Document
    async handleDocUpload(file) {
        this.ingestionLogs.innerHTML = `
            <div class="flex items-center gap-2 text-slate-300 text-xs">
                <span class="pulse-indicator"></span>
                <span>Ingesting ${file.name}... Splitting PDF pages, executing embeddings pipeline.</span>
            </div>
        `;

        try {
            const res = await ApiService.uploadDocument(file);
            this.ingestionLogs.innerHTML = `
                <div class="text-green-400 text-xs border border-green-500/20 bg-green-500/5 p-3 rounded-lg space-y-1">
                    <div class="font-bold flex items-center gap-1">✓ INGESTION COMPLETE</div>
                    <div>Successfully processed: <strong>${file.name}</strong></div>
                    <div>Generated <strong>${res.chunks_count}</strong> chunks & vectorized in SQLite.</div>
                    <div class="text-[10px] text-slate-500 mt-1">AI Entity Relationship extraction triggered automatically.</div>
                </div>
            `;
        } catch (error) {
            console.error(error);
            this.ingestionLogs.innerHTML = `
                <div class="text-red-500 text-xs border border-red-500/20 bg-red-500/5 p-3 rounded-lg font-bold">
                    ✗ Ingestion Failed: ${error.message}
                </div>
            `;
        }
    },

    // Load Drawing local preview
    handleDrawingPreview(file) {
        if (!file) return;
        this.drawingPreview.innerHTML = `
            <div class="p-3 bg-slate-900/60 rounded border border-slate-800 text-xs flex justify-between items-center">
                <span class="text-slate-300 font-mono">${file.name}</span>
                <span class="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">${(file.size / 1024).toFixed(1)} KB</span>
            </div>
        `;
        this.submitDrawingBtn.disabled = false;
        this.submitDrawingBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    },

    // Ingest and Analyze Engineering Drawing (Multimodal)
    async handleDrawingUpload(file) {
        const prompt = this.drawingPromptInput.value || "Analyze this engineering drawing. Identify key equipment, loop controls, and safety check valves.";
        this.drawingAnalysisResult.innerHTML = `
            <div class="space-y-3">
                <div class="skeleton-loader h-4 w-3/4 rounded"></div>
                <div class="skeleton-loader h-4 w-1/2 rounded"></div>
                <div class="skeleton-loader h-24 w-full rounded"></div>
            </div>
        `;

        try {
            const res = await ApiService.uploadDrawing(file, prompt);
            this.drawingAnalysisResult.innerHTML = `
                <div class="border border-slate-800 bg-slate-900/20 rounded-lg p-4 prose-custom max-h-[500px] overflow-y-auto">
                    <div class="text-xs text-orange-400 uppercase tracking-widest font-bold mb-2 flex justify-between items-center">
                        <span>Gemini Vision drawing Analysis</span>
                        <span class="bg-orange-500/10 px-2 py-0.5 rounded text-[10px]">${res.filename}</span>
                    </div>
                    <div>${this.formatMarkdown(res.analysis)}</div>
                </div>
            `;
        } catch (error) {
            console.error(error);
            this.drawingAnalysisResult.innerHTML = `<div class="text-red-500 text-sm">Failed to analyze drawing: ${error.message}</div>`;
        }
    },

    // Desktop QA Chat
    async handleDesktopChat(e) {
        e.preventDefault();
        const query = this.chatInput.value.trim();
        if (!query) return;

        // Render user message
        this.appendMessage('user', query, this.chatMessages);
        this.chatInput.value = '';

        // Show loading state
        const botMsgDiv = this.appendMessage('assistant', `
            <div class="flex items-center gap-1.5 py-1">
                <span class="pulse-indicator"></span>
                <span class="text-slate-400 text-xs font-mono">Retrieving manual references...</span>
            </div>
        `, this.chatMessages);

        try {
            const res = await ApiService.queryRAG(query, this.currentSessionId);
            
            // Format answer with markdown
            botMsgDiv.querySelector('.msg-text').innerHTML = this.formatMarkdown(res.answer);
            
            // Populate citations panel
            this.renderCitations(res.citations);
        } catch (error) {
            console.error(error);
            botMsgDiv.querySelector('.msg-text').innerHTML = `<span class="text-red-500">Error connecting to RAG service: ${error.message}</span>`;
        }
    },

    // Mobile QA Chat (inside QR/mobile view)
    async handleMobileChat(e) {
        e.preventDefault();
        const query = this.mobileChatInput.value.trim();
        if (!query) return;

        this.appendMessage('user', query, this.mobileChatMessages, true);
        this.mobileChatInput.value = '';

        const botMsgDiv = this.appendMessage('assistant', `
            <div class="flex items-center gap-1">
                <span class="pulse-indicator"></span>
                <span class="text-slate-500 text-[10px]">Processing voice query...</span>
            </div>
        `, this.mobileChatMessages, true);

        try {
            const res = await ApiService.queryRAG(query, this.currentSessionId);
            botMsgDiv.querySelector('.msg-text').innerHTML = this.formatMarkdown(res.answer);
        } catch (error) {
            console.error(error);
            botMsgDiv.querySelector('.msg-text').innerHTML = `<span class="text-red-500 text-xs">Error: ${error.message}</span>`;
        }
    },

    // Root Cause Analysis (RCA) Generator
    async handleRCAGeneration(e) {
        e.preventDefault();
        const desc = this.rcaDescription.value.trim();
        const assetId = this.rcaAssetId.value.trim();
        if (!desc) return;

        this.rcaReportOutput.innerHTML = `
            <div class="space-y-4">
                <div class="skeleton-loader h-6 w-1/3 rounded"></div>
                <div class="skeleton-loader h-4 w-3/4 rounded"></div>
                <div class="skeleton-loader h-32 w-full rounded"></div>
            </div>
        `;

        try {
            const res = await ApiService.runRCA(desc, assetId);
            this.rcaReportOutput.innerHTML = `
                <div class="bg-slate-900/20 border border-slate-800 rounded-lg p-5 prose-custom">
                    <div class="flex justify-between items-center mb-3">
                        <span class="text-[10px] bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded font-mono font-bold">RCA DRAFT VERIFIED</span>
                        <button onclick="window.print()" class="text-xs text-slate-400 hover:text-slate-200">🖨️ Export PDF / Print</button>
                    </div>
                    <div>${this.formatMarkdown(res.report)}</div>
                </div>
            `;
        } catch (error) {
            console.error(error);
            this.rcaReportOutput.innerHTML = `<div class="text-red-500 text-sm">Failed to generate RCA report: ${error.message}</div>`;
        }
    },

    // Compliance Audit & SOP Gap Remediator
    async handleComplianceAudit(e) {
        e.preventDefault();
        const sopText = this.sopTextarea.value.trim();
        if (!sopText) return;

        this.complianceResults.innerHTML = `
            <div class="space-y-4">
                <div class="skeleton-loader h-6 w-1/4 rounded"></div>
                <div class="skeleton-loader h-20 w-full rounded"></div>
            </div>
        `;

        try {
            const audit = await ApiService.auditSOP(sopText);
            
            let statusColor = 'text-green-500 border-green-500/20 bg-green-500/5';
            let statusLabel = 'COMPLIANT';
            if (audit.status === 'CRITICAL_GAP') {
                statusColor = 'text-red-500 border-red-500/20 bg-red-500/5 animate-pulse';
                statusLabel = 'CRITICAL GAP DETECTED';
            } else if (audit.status === 'MINOR_GAP') {
                statusColor = 'text-orange-500 border-orange-500/20 bg-orange-500/5';
                statusLabel = 'MINOR GAP DETECTED';
            }

            // Build Gaps List
            let gapsHtml = '';
            if (audit.gaps && audit.gaps.length > 0) {
                gapsHtml = audit.gaps.map((gap, i) => `
                    <div class="bg-slate-900/60 p-4 rounded-lg border border-slate-800 space-y-2">
                        <div class="flex justify-between items-center">
                            <span class="text-xs text-slate-400 font-mono font-bold">#${i+1} REF: ${gap.regulation_ref}</span>
                            <span class="text-[10px] text-red-400 bg-red-500/10 border border-red-500/25 px-2 py-0.25 rounded">NON-COMPLIANT</span>
                        </div>
                        <p class="text-xs text-slate-200">${gap.description}</p>
                        <div class="text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
                            <span class="font-bold text-orange-400/90">Remediation Blueprint:</span> ${gap.remediation}
                        </div>
                    </div>
                `).join('');
            } else {
                gapsHtml = `<div class="text-green-400 text-xs p-4 bg-green-500/5 border border-green-500/10 rounded">✓ No gaps identified. Proceed with normal operations.</div>`;
            }

            // Build the UI Panel
            this.complianceResults.innerHTML = `
                <div class="space-y-4">
                    <div class="flex justify-between items-center border border-slate-800 p-4 rounded-lg bg-slate-900/40">
                        <div>
                            <div class="text-xs text-slate-400 uppercase tracking-widest">Compliance Health Status</div>
                            <div class="text-sm font-bold mt-1 ${statusColor} border px-2.5 py-0.5 rounded-full inline-block font-mono">${statusLabel}</div>
                        </div>
                        <div class="text-right">
                            <div class="text-xs text-slate-400 uppercase tracking-widest">Safety Score</div>
                            <div class="text-2xl font-black font-mono text-orange-500">${audit.score}/100</div>
                        </div>
                    </div>

                    <div class="space-y-2">
                        <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Audit Findings</h4>
                        <div class="space-y-3">
                            ${gapsHtml}
                        </div>
                    </div>

                    <div class="bg-slate-900/40 p-4 rounded-lg border border-slate-800 flex justify-between items-center">
                        <div class="text-xs text-slate-400">
                            <strong>Audit Summary:</strong> ${audit.audit_summary}
                        </div>
                        ${audit.status !== 'COMPLIANT' ? `
                            <button id="remediate-sop-btn" class="bg-orange-500 hover:bg-orange-600 text-white font-bold text-xs px-4 py-2 rounded-lg transition shrink-0 ml-4">
                                Auto-Generate Remediation SOP
                            </button>
                        ` : ''}
                    </div>

                    <div id="remediation-sop-panel" class="hidden mt-4"></div>
                </div>
            `;

            // Auto-Remediate Trigger Button Click Handler
            const remediateBtn = document.getElementById('remediate-sop-btn');
            if (remediateBtn) {
                remediateBtn.addEventListener('click', async () => {
                    const gapDesc = audit.gaps.map(g => `${g.regulation_ref}: ${g.description}`).join('; ');
                    await this.handleSOPRemediation(sopText, gapDesc);
                });
            }

        } catch (error) {
            console.error(error);
            this.complianceResults.innerHTML = `<div class="text-red-500 text-sm">Failed to audit SOP: ${error.message}</div>`;
        }
    },

    async handleSOPRemediation(sopText, gapDescription) {
        const panel = document.getElementById('remediation-sop-panel');
        panel.classList.remove('hidden');
        panel.innerHTML = `
            <div class="space-y-3 p-4 border border-slate-800 rounded bg-slate-900/40">
                <div class="skeleton-loader h-4 w-3/4 rounded"></div>
                <div class="skeleton-loader h-20 w-full rounded"></div>
            </div>
        `;

        try {
            const res = await ApiService.remediateSOP(sopText, gapDescription);
            panel.innerHTML = `
                <div class="bg-slate-900/60 border border-slate-800 rounded-lg p-5 mt-4 space-y-4">
                    <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                        <h3 class="text-sm font-bold text-slate-200">Draft Remediated Compliance SOP</h3>
                        <button id="download-sop-btn" class="bg-green-600 hover:bg-green-700 text-white text-xs font-bold px-3 py-1.5 rounded transition">
                            📥 Download SOP File (.md)
                        </button>
                    </div>
                    <div class="prose-custom max-h-[400px] overflow-y-auto">
                        ${this.formatMarkdown(res.remediated_sop)}
                    </div>
                </div>
            `;

            // Download Trigger
            const downloadBtn = document.getElementById('download-sop-btn');
            if (downloadBtn) {
                downloadBtn.addEventListener('click', () => {
                    this.triggerSOPFileDownload(sopText, gapDescription);
                });
            }

        } catch (error) {
            console.error(error);
            panel.innerHTML = `<div class="text-red-500 text-xs p-4">Failed to remediate: ${error.message}</div>`;
        }
    },

    // Triggers direct download from backend endpoint
    triggerSOPFileDownload(sopText, gapDescription) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/api/download/sop';
        form.target = '_blank';

        const jsonInput = document.createElement('input');
        jsonInput.type = 'hidden';
        jsonInput.name = 'payload'; // FastAPI reads JSON from body, standard HTML form posts differently.
        
        // We will make a direct fetch download instead of form post to comply with JSON payloads
        fetch('/api/download/sop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sop_text: sopText, gap_description: gapDescription })
        })
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `remediated_sop_${Math.random().toString(36).substr(2, 5)}.md`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        })
        .catch(err => alert("Download failed: " + err.message));
    },

    // Proactive Warning Permit Checklist
    async handleWarningPermit(e) {
        e.preventDefault();
        const taskText = this.taskDescriptionInput.value.trim();
        if (!taskText) return;

        this.warningsOutput.innerHTML = `
            <div class="space-y-4">
                <div class="skeleton-loader h-6 w-1/4 rounded"></div>
                <div class="skeleton-loader h-32 w-full rounded"></div>
            </div>
        `;

        try {
            const res = await ApiService.runWarningChecklist(taskText);
            this.warningsOutput.innerHTML = `
                <div class="bg-slate-900/20 border border-slate-800 rounded-lg p-5 prose-custom">
                    ${this.formatMarkdown(res.permit_briefing)}
                </div>
            `;
        } catch (error) {
            console.error(error);
            this.warningsOutput.innerHTML = `<div class="text-red-500 text-sm">Failed to generate permit guidelines: ${error.message}</div>`;
        }
    },

    // Knowledge Graph loading
    loadKnowledgeGraph() {
        GraphVisualizer.init('graph-container', (selectedNodeId) => {
            // Callback when double clicking nodes
            // 1. Switch to Copilot tab
            const copilotTabBtn = document.querySelector('[data-tab="copilot"]');
            if (copilotTabBtn) copilotTabBtn.click();
            
            // 2. Set search query & trigger
            if (this.chatInput) {
                this.chatInput.value = `Explain the layout placement, safety parameters, and procedures for ${selectedNodeId}`;
                this.chatForm.dispatchEvent(new Event('submit', { bubbles: true }));
            }
        });
    },

    // ----------------- UTILITY FUNCTIONS -----------------

    appendMessage(role, text, container, isMobile = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `flex flex-col gap-1.5 max-w-[85%] rounded-xl p-3 text-xs ${
            role === 'user' 
                ? 'self-end bg-orange-600/10 border border-orange-500/25 text-slate-100 ml-auto' 
                : 'self-start bg-slate-900/70 border border-slate-800/80 text-slate-300'
        }`;
        
        msgDiv.innerHTML = `
            <div class="flex justify-between items-center text-[9px] font-mono tracking-wide text-slate-500">
                <span>${role === 'user' ? 'TECHNICIAN' : 'OPERATIONS BRAIN'}</span>
                <span>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <div class="msg-text leading-relaxed whitespace-pre-wrap">${text}</div>
        `;
        
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;
        return msgDiv;
    },

    renderCitations(citations) {
        if (!this.citationsList) return;
        
        if (!citations || citations.length === 0) {
            this.citationsList.innerHTML = `<p class="text-slate-500 text-xs py-4">No specific manual references retrieved.</p>`;
            return;
        }

        this.citationsList.innerHTML = citations.map(cit => `
            <div class="p-3 bg-slate-900/40 rounded-lg border border-slate-800/80 space-y-1 hover:border-orange-500/35 transition cursor-pointer">
                <div class="flex justify-between text-[10px] font-mono">
                    <span class="text-orange-400 font-bold">Citation [${cit.citation_id}]</span>
                    <span class="text-slate-500">Score: ${(cit.score * 100).toFixed(0)}%</span>
                </div>
                <div class="text-[11px] font-semibold text-slate-300 truncate">${cit.filename} (Page ${cit.page_number})</div>
                <div class="text-[10px] text-slate-500 italic leading-snug line-clamp-2">${cit.snippet}</div>
            </div>
        `).join('');
    },

    formatMarkdown(text) {
        if (!text) return '';
        
        let formatted = text
            // Escape tags
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            // Headers
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            // Bold
            .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
            // Code block
            .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
            // Inline code
            .replace(/`([^`]+)`/gim, '<code>$1</code>')
            // Checklist markdown
            .replace(/^- \[ \] (.*$)/gim, '<label class="flex items-center gap-2 py-0.5"><input type="checkbox" disabled class="rounded border-slate-800 bg-slate-950 text-orange-500 focus:ring-0"> <span>$1</span></label>')
            .replace(/^- \[x\] (.*$)/gim, '<label class="flex items-center gap-2 py-0.5"><input type="checkbox" checked disabled class="rounded border-slate-800 bg-slate-950 text-orange-500 focus:ring-0"> <span class="line-through text-slate-600">$1</span></label>')
            // Bullet points
            .replace(/^- (.*$)/gim, '<li>$1</li>');

        // Wrap list items
        formatted = formatted.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
        
        return formatted;
    }
};
