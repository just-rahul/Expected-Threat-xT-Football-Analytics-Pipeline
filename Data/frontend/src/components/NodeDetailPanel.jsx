import { motion } from 'framer-motion';
import { useAppContext } from '../App';

export default function NodeDetailPanel({ node, onClose }) {
    const { result } = useAppContext();
    if (!node) return null;

    const fullAcc = result?.suspicious_accounts?.find(a => a.account_id === node.id) || {};
    const ml_scores = fullAcc.ml_scores || {};
    const flag_hits = fullAcc.flag_hits || [];
    
    const score = node.suspicion_score || 0;
    const scoreColor = score > 70 ? 'var(--color-risk-red)' : score > 30 ? 'var(--color-risk-orange)' : 'var(--color-risk-green)';
    const riskLabel = node.decision === 'BLOCK' ? 'MANDATORY BLOCK' : node.decision === 'REVIEW' ? 'MANUAL REVIEW' : 'P-SAFE';
    const role = node.role || 'LEAF';

    const renderBar = (label, value, color) => (
        <div className="mb-3">
            <div className="flex justify-between text-[10px] uppercase font-mono text-slate-400 mb-1">
                <span>{label}</span>
                <span style={{ color }}>{value.toFixed(1)}</span>
            </div>
            <div className="h-1.5 bg-black/40 rounded-full overflow-hidden">
                <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, Math.max(0, value))}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    className="h-full rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)]"
                    style={{ backgroundColor: color }}
                />
            </div>
        </div>
    );

    return (
        <motion.div
            className="side-panel"
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        >
            {/* Close button */}
            <button
                onClick={onClose}
                style={{
                    position: 'absolute', top: 16, right: 16,
                    background: 'none', border: 'none', color: 'var(--color-text-dim)',
                    cursor: 'pointer', fontSize: '1.2rem',
                }}
            >
                ✕
            </button>

            {/* Header */}
            <div style={{ marginBottom: 24, position: 'relative' }}>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-dim)', letterSpacing: '0.1em', marginBottom: 4 }}>
                    ACCOUNT DETAILS
                </p>
                <div className="flex items-center gap-2">
                    <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-accent)' }}>
                        {node.id}
                    </h2>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border uppercase
                        ${role === 'HUB' ? 'bg-purple-500/20 text-purple-400 border-purple-500/30' : 
                          role === 'BRIDGE' ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' : 
                          'bg-slate-500/20 text-slate-400 border-slate-500/30'}`}
                    >
                        {role}
                    </span>
                </div>
            </div>

            {/* Risk Score Card */}
            <div className="glass-card p-5 mb-5" style={{ borderColor: `${scoreColor}30` }}>
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-dim)', letterSpacing: '0.08em', marginBottom: 8 }}>
                    RISK SCORE
                </p>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '2.5rem', fontWeight: 800, color: scoreColor, lineHeight: 1 }}>
                    {score}
                </div>
                <div style={{ marginTop: 10, height: 6, background: 'rgba(0,245,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${score}%` }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                        style={{ height: '100%', background: scoreColor, borderRadius: 3, boxShadow: `0 0 10px ${scoreColor}50` }}
                    />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                    <span style={{ fontSize: '0.6rem', color: 'var(--color-text-dim)', fontFamily: 'var(--font-mono)' }}>0</span>
                    <span className={`badge ${score > 70 ? 'badge-high' : score > 30 ? 'badge-medium' : 'badge-low'}`}>
                        {riskLabel}
                    </span>
                    <span style={{ fontSize: '0.6rem', color: 'var(--color-text-dim)', fontFamily: 'var(--font-mono)' }}>100</span>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-3 mb-5">
                <div className="glass-card p-3 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 700, color: 'var(--color-accent)' }}>
                        {node.in_degree ?? '—'}
                    </div>
                    <div className="metric-label">In-Degree</div>
                </div>
                <div className="glass-card p-3 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 700, color: 'var(--color-accent)' }}>
                        {node.out_degree ?? '—'}
                    </div>
                    <div className="metric-label">Out-Degree</div>
                </div>
                <div className="glass-card p-3 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-risk-green)' }}>
                        {node.total_incoming != null ? `$${node.total_incoming.toLocaleString()}` : '—'}
                    </div>
                    <div className="metric-label">Total Incoming</div>
                </div>
                <div className="glass-card p-3 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-risk-orange)' }}>
                        {node.total_outgoing != null ? `$${node.total_outgoing.toLocaleString()}` : '—'}
                    </div>
                    <div className="metric-label">Total Outgoing</div>
                </div>
            </div>

            {/* ML Subcomponents */}
            {Object.keys(ml_scores).length > 0 && (
                <div className="glass-card p-4 mb-5">
                    <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-dim)', letterSpacing: '0.08em', marginBottom: 12 }}>
                        ML PILLAR BREAKDOWN
                    </p>
                    {renderBar("GAT (Topology)", ml_scores.gat || 0, "#9B59B6")}
                    {renderBar("LSTM (Timing)", ml_scores.lstm || 0, "#3498DB")}
                    {renderBar("EIF (Anomaly)", ml_scores.eif || 0, "#F1C40F")}
                    {renderBar("RBI Rules", ml_scores.rules || 0, "#E74C3C")}
                </div>
            )}

            {/* Patterns & Flags */}
            <div className="mb-5">
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-dim)', letterSpacing: '0.08em', marginBottom: 10 }}>
                    DETECTED SIGNATURES
                </p>
                <div className="flex flex-wrap gap-2">
                    {flag_hits.map((p) => (
                        <span key={p} className="px-2 py-1 rounded text-xs font-mono bg-red-500/20 text-red-400 border border-red-500/30">{p}</span>
                    ))}
                    {(node.detected_patterns || []).map((p) => (
                        <span key={p} className="pattern-chip" style={{ padding: '4px 10px' }}>{p}</span>
                    ))}
                    {flag_hits.length === 0 && (!node.detected_patterns || node.detected_patterns.length === 0) && (
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                            No patterns detected
                        </span>
                    )}
                </div>
            </div>

            {/* Risk Classification */}
            <div className="glass-card p-4">
                <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--color-text-dim)', letterSpacing: '0.08em', marginBottom: 8 }}>
                    CLASSIFICATION
                </p>
                <div className="flex items-center gap-3">
                    <div style={{
                        width: 12, height: 12, borderRadius: '50%',
                        background: scoreColor,
                        boxShadow: `0 0 10px ${scoreColor}60`,
                    }} />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 600, color: scoreColor }}>
                        {riskLabel}
                    </span>
                </div>
                <p style={{ color: 'var(--color-text-dim)', fontSize: '0.7rem', marginTop: 8, lineHeight: 1.5 }}>
                    {score > 70
                        ? 'This account shows strong indicators of money mule activity. Immediate investigation recommended.'
                        : score > 30
                            ? 'This account has suspicious patterns warranting further review.'
                            : 'This account is within normal behavioral parameters.'
                    }
                </p>
            </div>
        </motion.div>
    );
}
