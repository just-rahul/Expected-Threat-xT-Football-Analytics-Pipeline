import { useEffect, useRef } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

export default function NetworkGraph({ data, onNodeClick }) {
    const containerRef = useRef(null);
    const networkRef = useRef(null);

    useEffect(() => {
        if (!containerRef.current || !data) return;

        const nodes = new DataSet(
            data.nodes.map((n) => ({
                id: n.id,
                label: n.label || n.id,
                color: {
                    background: n.suspicion_score > 70 ? '#FF3B3B' : n.suspicion_score > 30 ? '#FF9F1C' : 'rgba(0, 245, 255, 0.6)',
                    border: n.suspicion_score > 70 ? '#FF3B3B' : n.suspicion_score > 30 ? '#FF9F1C' : 'rgba(0, 245, 255, 0.3)',
                    highlight: { background: '#00F5FF', border: '#00F5FF' },
                    hover: { background: n.suspicion_score > 70 ? '#FF6B6B' : n.suspicion_score > 30 ? '#FFB84D' : '#60EFFF', border: '#00F5FF' },
                },
                size: n.suspicion_score > 70 ? 20 : n.suspicion_score > 30 ? 14 : 8,
                font: {
                    size: 8,
                    color: '#8B95A8',
                    face: 'JetBrains Mono, monospace',
                    strokeWidth: 3,
                    strokeColor: '#0B0F1A',
                },
                shadow: {
                    enabled: n.suspicion_score > 30,
                    color: n.suspicion_score > 70 ? 'rgba(255,59,59,0.3)' : 'rgba(255,159,28,0.2)',
                    size: 12,
                },
                _raw: n,
            }))
        );

        const edges = new DataSet(
            data.edges.map((e, i) => ({
                id: `e-${i}`,
                from: e.from,
                to: e.to,
                value: e.value,
                title: e.title,
                color: {
                    color: 'rgba(0, 245, 255, 0.1)',
                    highlight: 'rgba(0, 245, 255, 0.6)',
                    hover: 'rgba(0, 245, 255, 0.25)',
                },
                arrows: { to: { enabled: true, scaleFactor: 0.4, type: 'arrow' } },
                smooth: { type: 'curvedCW', roundness: 0.1 },
                width: 0.6,
            }))
        );

        const options = {
            physics: {
                barnesHut: {
                    gravitationalConstant: -3000,
                    centralGravity: 0.25,
                    springLength: 120,
                    springConstant: 0.035,
                    damping: 0.09,
                },
                stabilization: { iterations: 200, fit: true },
            },
            nodes: {
                shape: 'dot',
                borderWidth: 2,
                borderWidthSelected: 3,
            },
            edges: {
                width: 0.6,
                scaling: { min: 0.4, max: 3 },
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                zoomView: true,
                dragView: true,
                dragNodes: true,
                multiselect: true,
            },
        };

        const network = new Network(containerRef.current, { nodes, edges }, options);
        networkRef.current = network;

        network.on('stabilizationIterationsDone', () => {
            network.setOptions({ physics: { enabled: false } });
        });

        network.on('click', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const rawNode = data.nodes.find((n) => n.id === nodeId);
                if (rawNode && onNodeClick) onNodeClick(rawNode);
            }
        });

        return () => network.destroy();
    }, [data, onNodeClick]);

    return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
}
