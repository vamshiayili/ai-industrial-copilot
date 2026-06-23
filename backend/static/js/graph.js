// Knowledge Graph Visualizer using vis-network
import { ApiService } from './api.js';

let networkInstance = null;

export const GraphVisualizer = {
    async init(containerId, onNodeSelected) {
        const container = document.getElementById(containerId);
        if (!container) return;

        try {
            const data = await ApiService.getGraphData();
            
            // Map group types to color configurations (Obsidian dark + safety highlights)
            const groupStyles = {
                ASSET: {
                    color: { background: '#1e1b18', border: '#f97316', hover: { background: '#2c251f', border: '#f97316' }, highlight: { background: '#362a20', border: '#f97316' } },
                    shape: 'box',
                    font: { color: '#f3f4f6' }
                },
                REGULATION: {
                    color: { background: '#1c151b', border: '#ec4899', hover: { background: '#251b24', border: '#ec4899' }, highlight: { background: '#2f202d', border: '#ec4899' } },
                    shape: 'ellipse',
                    font: { color: '#f3f4f6' }
                },
                TEAM: {
                    color: { background: '#121e1a', border: '#10b981', hover: { background: '#1a2a24', border: '#10b981' }, highlight: { background: '#20352d', border: '#10b981' } },
                    shape: 'database',
                    font: { color: '#f3f4f6' }
                },
                DRAWING: {
                    color: { background: '#111c24', border: '#0ea5e9', hover: { background: '#172733', border: '#0ea5e9' }, highlight: { background: '#1e3242', border: '#0ea5e9' } },
                    shape: 'dot',
                    font: { color: '#f3f4f6' }
                }
            };

            const nodes = data.nodes.map(node => {
                const style = groupStyles[node.group] || groupStyles.ASSET;
                return {
                    id: node.id,
                    label: node.label,
                    title: `Type: ${node.group}`,
                    ...style,
                    borderWidth: 2,
                    shadow: true
                };
            });

            const edges = data.edges.map(edge => {
                return {
                    from: edge.from,
                    to: edge.to,
                    label: edge.label,
                    arrows: 'to',
                    color: { color: '#38384d', highlight: '#f97316', hover: '#555577' },
                    font: { color: '#94a3b8', size: 10, strokeWidth: 0, align: 'middle' },
                    smooth: { type: 'cubicBezier', roundness: 0.5 }
                };
            });

            const graphData = {
                nodes: new vis.DataSet(nodes),
                edges: new vis.DataSet(edges)
            };

            const options = {
                physics: {
                    stabilization: true,
                    barnesHut: {
                        gravitationalConstant: -2000,
                        centralGravity: 0.3,
                        springLength: 95,
                        springConstant: 0.04
                    }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 200,
                    selectable: true,
                    selectConnectedEdges: true
                }
            };

            if (networkInstance) {
                networkInstance.destroy();
            }

            networkInstance = new vis.Network(container, graphData, options);

            // Double click handler -> searches the node in the system
            networkInstance.on("doubleClick", (params) => {
                if (params.nodes.length > 0) {
                    const nodeId = params.nodes[0];
                    if (onNodeSelected) {
                        onNodeSelected(nodeId);
                    }
                }
            });

        } catch (error) {
            console.error("Error drawing knowledge graph:", error);
            container.innerHTML = `<div class="text-red-500 p-4">Error loading knowledge graph data: ${error.message}</div>`;
        }
    }
};
