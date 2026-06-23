// QR Code simulation and mobile technician assistant
import { ApiService } from './api.js';

export const QRScannerSim = {
    init(scanSelectId, resultContainerId, voiceBtnId, queryInputId) {
        const select = document.getElementById(scanSelectId);
        const resultContainer = document.getElementById(resultContainerId);
        const voiceBtn = document.getElementById(voiceBtnId);
        const queryInput = document.getElementById(queryInputId);

        if (select) {
            select.addEventListener('change', async (e) => {
                const assetId = e.target.value;
                if (!assetId) {
                    resultContainer.innerHTML = `<p class="text-slate-400 text-center py-8">Select or scan an asset tag to load field SOPs.</p>`;
                    return;
                }
                await this.scanAsset(assetId, resultContainer);
            });
        }

        // Speech-to-Text integration (Web Speech API)
        if (voiceBtn && queryInput) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            
            if (SpeechRecognition) {
                const recognition = new SpeechRecognition();
                recognition.continuous = false;
                recognition.lang = 'en-US';
                recognition.interimResults = false;
                recognition.maxAlternatives = 1;

                voiceBtn.addEventListener('click', () => {
                    voiceBtn.classList.add('bg-red-600/30', 'text-red-500', 'animate-pulse');
                    voiceBtn.innerHTML = '🎙️ Listening...';
                    
                    try {
                        recognition.start();
                    } catch (err) {
                        console.error("Speech recognition already running", err);
                    }
                });

                recognition.onresult = (event) => {
                    const speechToText = event.results[0][0].transcript;
                    queryInput.value = speechToText;
                    
                    // Trigger a custom event or submit search if input is populated
                    queryInput.dispatchEvent(new Event('input', { bubbles: true }));
                };

                recognition.onspeechend = () => {
                    recognition.stop();
                    resetVoiceBtn();
                };

                recognition.onerror = (event) => {
                    console.error("Speech recognition error", event.error);
                    resetVoiceBtn();
                };

                recognition.onend = () => {
                    resetVoiceBtn();
                };
            } else {
                // Speech recognition not supported in browser
                voiceBtn.addEventListener('click', () => {
                    alert("Web Speech API not supported in this browser. Please type your query.");
                });
            }

            function resetVoiceBtn() {
                voiceBtn.classList.remove('bg-red-600/30', 'text-red-500', 'animate-pulse');
                voiceBtn.innerHTML = '🎙️ Tap to Speak';
            }
        }
    },

    async scanAsset(assetId, container) {
        container.innerHTML = `
            <div class="space-y-4 py-8">
                <div class="skeleton-loader h-4 w-3/4 rounded mx-auto"></div>
                <div class="skeleton-loader h-4 w-1/2 rounded mx-auto"></div>
                <div class="skeleton-loader h-20 w-5/6 rounded mx-auto"></div>
            </div>
        `;

        try {
            const data = await ApiService.getAssetQRData(assetId);
            
            // Build the specifications table
            let specsHtml = '';
            for (const [key, val] of Object.entries(data.specs)) {
                const label = key.replace('_', ' ').toUpperCase();
                specsHtml += `
                    <div class="flex justify-between border-b border-slate-800 py-1 text-xs">
                        <span class="text-slate-400">${label}</span>
                        <span class="text-slate-200 font-mono">${val}</span>
                    </div>
                `;
            }

            // Build warnings
            let warningsHtml = '';
            if (data.incidents && data.incidents.length > 0) {
                warningsHtml = `
                    <div class="bg-orange-950/20 border border-orange-500/30 rounded-lg p-3 my-3">
                        <h4 class="text-orange-500 font-bold text-xs flex items-center gap-1 mb-2">
                            ⚠️ ACTIVE RISK ALERTS (${data.incidents.length})
                        </h4>
                        <ul class="list-disc pl-4 space-y-1.5 text-xs text-orange-200">
                            ${data.incidents.map(inc => `
                                <li><strong>${inc.title}:</strong> ${inc.hazard}</li>
                            `).join('')}
                        </ul>
                    </div>
                `;
            } else {
                warningsHtml = `
                    <div class="bg-green-950/20 border border-green-500/30 rounded-lg p-3 my-3 text-xs text-green-400">
                        ✓ No active incident history warnings recorded for this specific asset.
                    </div>
                `;
            }

            // Build checklists
            let checklistsHtml = data.safety_checks.map(check => `
                <label class="flex items-start gap-2.5 text-xs text-slate-300 py-1 cursor-pointer">
                    <input type="checkbox" class="mt-0.5 rounded border-slate-700 text-orange-500 focus:ring-orange-500 bg-slate-900">
                    <span>${check}</span>
                </label>
            `).join('');

            container.innerHTML = `
                <div class="space-y-4 animate-fadeIn">
                    <div class="flex justify-between items-center bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                        <div>
                            <h3 class="text-sm font-bold text-slate-200">${data.specs.name || assetId}</h3>
                            <span class="text-[10px] bg-orange-500/10 text-orange-400 px-2 py-0.5 rounded border border-orange-500/20 font-mono">${assetId}</span>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <span class="pulse-indicator"></span>
                            <span class="text-xs text-green-400 font-mono">ONLINE</span>
                        </div>
                    </div>

                    ${warningsHtml}

                    <div class="space-y-2">
                        <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Technical Specifications</h4>
                        <div class="bg-slate-900/40 p-3 rounded-lg border border-slate-800/60 space-y-1">
                            ${specsHtml}
                        </div>
                    </div>

                    <div class="space-y-2">
                        <h4 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Field Safety Checklist</h4>
                        <div class="bg-slate-900/40 p-3 rounded-lg border border-slate-800/60 flex flex-col gap-1.5">
                            ${checklistsHtml}
                        </div>
                    </div>
                </div>
            `;

        } catch (error) {
            console.error("QR Code scanner error:", error);
            container.innerHTML = `<div class="text-red-500 text-sm p-4">Failed to resolve asset code: ${error.message}</div>`;
        }
    }
};
