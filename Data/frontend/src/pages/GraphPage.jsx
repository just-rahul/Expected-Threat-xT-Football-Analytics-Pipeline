import { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../App';
import NetworkGraph from '../components/NetworkGraph';
import NodeDetailPanel from '../components/NodeDetailPanel';

export default function GraphPage() {
    const { result, graphData, setSelectedNode, selectedNode } = useAppContext();
    const navigate = useNavigate();
    const [filter, setFilter] = useState('all');

    if (!result || !graphData) {
        navigate('/');
        return null;
    }

    const filteredData = useMemo(() => {
        if (filter === 'all') return graphData;
        const threshold = filter === 'high' ? 70 : filter === 'medium' ? 30 : 0;
        const maxThreshold = filter === 'high' ? 101 : filter === 'medium' ? 70 : 30;
        const filteredNodes = graphData.nodes.filter(
            (n) => n.suspicion_score >= threshold && n.suspicion_score < maxThreshold
        );
        const nodeIds = new Set(filteredNodes.map((n) => n.id));
        const filteredEdges = graphData.edges.filter(
            (e) => nodeIds.has(e.from) || nodeIds.has(e.to)
        );
        return { nodes: filteredNodes, edges: filteredEdges };
    }, [graphData, filter]);

    const onNodeClick = useCallback((nodeData) => {
        setSelectedNode(nodeData);
    }, [setSelectedNode]);

    return (
        <div className="max-w-[1560px] mx-auto px-6 py-6">
            {/* Header */}
            <motion.div
                className="flex items-center justify-between mb-6"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
            >
                <div>
                    <h1 style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '1.4rem', letterSpacing: '0.1em' }}>
                        <span style={{ color: 'var(--color-accent)' }}>TRANSACTION</span> NETWORK
                    </h1>
                    <p style={{ color: 'var(--color-text-dim)', fontSize: '0.72rem', marginTop: '4px' }}>
                        Interactive graph visualization · Click nodes for details
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {[
                        { key: 'all', label: 'All Nodes' },
                        { key: 'high', label: 'High Risk' },
                        { key: 'medium', label: 'Medium' },
                        { key: 'low', label: 'Low Risk' },
                    ].map((f) => (
                        <button
                            key={f.key}
                            onClick={() => setFilter(f.key)}
                            className={`btn-primary ${filter === f.key ? '' : ''}`}
                            style={{
                                padding: '6px 12px',
                                fontSize: '0.7rem',
                                background: filter === f.key ? 'rgba(0, 245, 255, 0.2)' : 'rgba(0, 245, 255, 0.05)',
                            }}
                        >
                            {f.label}
                        </button>
                    ))}
                </div>
            </motion.div>

            {/* Legend */}
            <motion.div
                className="flex items-center gap-6 mb-4"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.1 }}
            >
                <span className="flex items-center gap-2" style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                    <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#00FF94', display: 'inline-block' }} /> Safe
                </span>
                <span className="flex items-center gap-2" style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                    <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#FF9F1C', display: 'inline-block' }} /> Suspicious
                </span>
                <span className="flex items-center gap-2" style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                    <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#FF3B3B', display: 'inline-block' }} /> High Risk
                </span>
            </motion.div>

            {/* Graph */}
            <motion.div
                className="glass-card overflow-hidden mb-6"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
            >
                <div className="graph-container" style={{ height: 'calc(100vh - 280px)', minHeight: '500px' }}>
                    <NetworkGraph data={filteredData} onNodeClick={onNodeClick} />
                </div>
            </motion.div>

            {/* Stats Bar */}
            <motion.div
                className="grid grid-cols-2 md:grid-cols-4 gap-3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
            >
                <div className="glass-card p-3 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-accent)' }}>
                        {filteredData.nodes.length}
                    </div>
                    <div className="metric-label">Nodes</div>
                </div>
                <div className="glass-card p-3 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text-secondary)' }}>
                        {filteredData.edges.length}
                    </div>
                    <div className="metric-label">Edges</div>
                </div>
                <div className="glass-card p-3 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-risk-red)' }}>
                        {graphData.nodes.filter(n => n.suspicion_score > 70).length}
                    </div>
                    <div className="metric-label">High Risk Nodes</div>
                </div>
                <div className="glass-card p-3 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-risk-green)' }}>
                        {graphData.nodes.filter(n => n.suspicion_score === 0).length}
                    </div>
                    <div className="metric-label">Safe Nodes</div>
                </div>
            </motion.div>

            {/* Node Detail Side Panel */}
            <AnimatePresence>
                {selectedNode && (
                    <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
                )}
            </AnimatePresence>
        </div>
    );
}
