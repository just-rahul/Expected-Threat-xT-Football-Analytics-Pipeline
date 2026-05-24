import { useMemo, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../App';
import FraudRingTable from '../components/FraudRingTable';
import MiniGraph from '../components/MiniGraph';
import RiskGauge from '../components/RiskGauge';

function AnimatedNumber({ value, duration = 1200 }) {
    const [display, setDisplay] = useState(0);
    useEffect(() => {
        const num = typeof value === 'number' ? value : parseFloat(value) || 0;
        const start = performance.now();
        const step = (now) => {
            const p = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            setDisplay(Math.round(eased * num));
            if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }, [value, duration]);
    return <>{display.toLocaleString()}</>;
}

const stagger = { hidden: {}, visible: { transition: { staggerChildren: 0.08 } } };
const fadeUp = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0, transition: { duration: 0.5 } } };

export default function Dashboard() {
    const { result, graphData } = useAppContext();
    const navigate = useNavigate();
    const s = result?.summary;

    const stats = useMemo(() => {
        if (!result) return null;
        const accounts = result.suspicious_accounts || [];
        const rings = result.fraud_rings || [];
        const highRisk = accounts.filter(a => a.suspicion_score > 70).length;
        const blocks = accounts.filter(a => a.decision === 'BLOCK').length;
        const reviews = accounts.filter(a => a.decision === 'REVIEW').length;
        const avgScore = accounts.length > 0
            ? (accounts.reduce((sum, a) => sum + a.suspicion_score, 0) / accounts.length).toFixed(1)
            : '0.0';
        const totalRingMembers = rings.reduce((sum, r) => sum + r.member_accounts.length, 0);
        return { highRisk, blocks, reviews, avgScore, totalRingMembers, accounts, rings };
    }, [result]);

    if (!result) {
        navigate('/');
        return null;
    }

    return (
        <div className="max-w-[1560px] mx-auto px-6 py-6">
            {/* Header */}
            <motion.div
                className="mb-8"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <h1 style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '1.4rem', letterSpacing: '0.1em' }}>
                    <span style={{ color: 'var(--color-accent)' }}>THREAT</span> DASHBOARD
                </h1>
                <p style={{ color: 'var(--color-text-dim)', fontSize: '0.75rem', marginTop: '4px' }}>
                    MoneyMal v2.0 — Graph-Native & ML-Powered Financial Forensics
                </p>
            </motion.div>

            {/* Metric Cards - Bento Grid */}
            <motion.div
                className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8"
                variants={stagger}
                initial="hidden"
                animate="visible"
            >
                <motion.div className="metric-card glass-card-glow" variants={fadeUp}>
                    <div className="metric-value"><AnimatedNumber value={s.total_accounts_analyzed} /></div>
                    <div className="metric-label">Total Accounts</div>
                </motion.div>

                <motion.div className="metric-card glass-card-glow" variants={fadeUp}>
                    <div className="metric-value text-cyan-400"><AnimatedNumber value={s.suspicious_accounts_flagged} /></div>
                    <div className="metric-label">Flagged Accounts</div>
                </motion.div>
                
                <motion.div className="metric-card glass-card-glow border-[1px] border-red-500/20 bg-red-500/5" variants={fadeUp}>
                    <div className="metric-value text-red-500"><AnimatedNumber value={stats.blocks} /></div>
                    <div className="metric-label">Mandatory BLOCK</div>
                </motion.div>
                
                <motion.div className="metric-card glass-card-glow border-[1px] border-yellow-500/20 bg-yellow-500/5" variants={fadeUp}>
                    <div className="metric-value text-yellow-500"><AnimatedNumber value={stats.reviews} /></div>
                    <div className="metric-label">Manual REVIEW</div>
                </motion.div>

                <motion.div className="metric-card glass-card-glow" variants={fadeUp}>
                    <div className="metric-value warning"><AnimatedNumber value={stats.highRisk} /></div>
                    <div className="metric-label">High Risk Mules</div>
                </motion.div>

                <motion.div className="metric-card glass-card-glow" variants={fadeUp}>
                    <div className="metric-value"><AnimatedNumber value={s.fraud_rings_detected} /></div>
                    <div className="metric-label">Fraud Rings</div>
                </motion.div>

                <motion.div className="metric-card glass-card-glow" variants={fadeUp}>
                    <div className="metric-value success">{stats.avgScore}</div>
                    <div className="metric-label">Avg Fraud Score</div>
                </motion.div>
            </motion.div>

            {/* Bento Layout: Fraud Ring Summary + Graph + Gauge */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
                {/* Fraud Ring Summary */}
                <motion.div
                    className="lg:col-span-2 glass-card p-5"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <h2 style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.9rem', color: 'var(--color-text-primary)', letterSpacing: '0.06em' }}>
                            FRAUD RING SUMMARY
                        </h2>
                        <span className="badge badge-high">{result.fraud_rings.length} rings</span>
                    </div>
                    <FraudRingTable rings={result.fraud_rings} accounts={result.suspicious_accounts} />
                </motion.div>

                {/* Right Column: Mini Graph + Gauge */}
                <motion.div
                    className="flex flex-col gap-5"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 }}
                >
                    {/* Mini Transaction Network */}
                    <div
                        className="glass-card p-4 cursor-pointer"
                        onClick={() => navigate('/graph')}
                        style={{ flex: 1 }}
                    >
                        <h3 style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '8px', letterSpacing: '0.06em' }}>
                            TRANSACTION NETWORK
                        </h3>
                        <div className="graph-container" style={{ height: '180px' }}>
                            <MiniGraph data={graphData} />
                        </div>
                        <p style={{ color: 'var(--color-text-dim)', fontSize: '0.65rem', textAlign: 'center', marginTop: '8px', fontFamily: 'var(--font-mono)' }}>
                            Click to expand →
                        </p>
                    </div>

                    {/* Risk Gauge */}
                    <div className="glass-card p-5 flex flex-col items-center justify-center">
                        <h3 style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '12px', letterSpacing: '0.06em' }}>
                            THREAT LEVEL
                        </h3>
                        <RiskGauge score={parseFloat(stats.avgScore)} />
                    </div>
                </motion.div>
            </div>

            {/* Soccer Analytics Integration Bento Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
                {/* Column 1: Layering Possession Chains */}
                <motion.div
                    className="glass-card p-5"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <h2 style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.9rem', color: 'var(--color-text-primary)', letterSpacing: '0.06em' }}>
                            <span style={{ color: 'var(--color-accent)' }}>LAYERING</span> PATHS (POSSESSION CHAINS)
                        </h2>
                        <span className="badge badge-medium">soccer-inspired</span>
                    </div>
                    <div className="overflow-y-auto max-h-[300px]">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Fund Flow Chain Path</th>
                                    <th>Hops</th>
                                    <th>Cumulative xMLT Threat</th>
                                </tr>
                            </thead>
                            <tbody>
                                {result.layering_chains && result.layering_chains.map((chain, idx) => (
                                    <tr key={idx}>
                                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: '#00F5FF' }}>
                                            {chain.path.join(' → ')}
                                        </td>
                                        <td style={{ fontFamily: 'var(--font-mono)' }}>{chain.length - 1}</td>
                                        <td>
                                            <span className="badge badge-high" style={{ background: 'rgba(255, 59, 59, 0.15)', border: '1px solid rgba(255, 59, 59, 0.25)', color: '#FF3B3B' }}>
                                                +{chain.cumulative_xmlt}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                                {(!result.layering_chains || result.layering_chains.length === 0) && (
                                    <tr>
                                        <td colSpan={3} style={{ textAlign: 'center', color: 'var(--color-text-dim)', fontSize: '0.72rem' }}>
                                            No long layering chains detected.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </motion.div>

                {/* Column 2: Markov Threat Vectors */}
                <motion.div
                    className="glass-card p-5"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.52 }}
                >
                    <div className="flex items-center justify-between mb-4">
                        <h2 style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.9rem', color: 'var(--color-text-primary)', letterSpacing: '0.06em' }}>
                            <span style={{ color: 'var(--color-accent)' }}>MARKOV</span> STATIONARY FLOW VECTORS
                        </h2>
                        <span className="badge badge-medium">transition matrix</span>
                    </div>
                    <div className="overflow-y-auto max-h-[300px]">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Account ID</th>
                                    <th>Steady-State Prob</th>
                                    <th>Flow Vector Weight</th>
                                </tr>
                            </thead>
                            <tbody>
                                {result.markov_flows && result.markov_flows.slice(0, 8).map((flow, idx) => (
                                    <tr key={idx}>
                                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                                            {flow.account_id}
                                        </td>
                                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>{flow.stationary_probability.toFixed(5)}</td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, minWidth: 60, position: 'relative' }}>
                                                    <div style={{ height: '100%', width: `${Math.min(100, flow.threat_vector_weight * 10)}%`, background: '#00F5FF', borderRadius: 2 }} />
                                                </div>
                                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>{flow.threat_vector_weight.toFixed(1)}%</span>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </motion.div>
            </div>

            {/* Top Suspicious Accounts Preview */}
            <motion.div
                className="glass-card p-5 mb-8"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
            >
                <div className="flex items-center justify-between mb-4">
                    <h2 style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.9rem', letterSpacing: '0.06em' }}>
                        TOP SUSPICIOUS ACCOUNTS
                    </h2>
                    <button
                        className="btn-primary"
                        style={{ padding: '6px 14px', fontSize: '0.7rem' }}
                        onClick={() => navigate('/transactions')}
                    >
                        View All →
                    </button>
                </div>
                <div className="overflow-x-auto">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Account ID</th>
                                <th>Decision</th>
                                <th>Score</th>
                                <th>Patterns</th>
                                <th>Ring</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(result.suspicious_accounts || []).slice(0, 8).map((a) => (
                                <tr key={a.account_id}>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.75rem' }}>{a.account_id}</td>
                                    <td>
                                        {a.decision === 'BLOCK' ? <span className="px-2 py-1 text-[10px] bg-red-500/20 text-red-400 border border-red-500/30 rounded dark-text">BLOCK</span> : 
                                         a.decision === 'REVIEW' ? <span className="px-2 py-1 text-[10px] bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 rounded">REVIEW</span> :
                                         <span className="px-2 py-1 text-[10px] bg-green-500/20 text-green-400 border border-green-500/30 rounded">APPROVE</span>}
                                    </td>
                                    <td>
                                        <span className={`badge ${a.suspicion_score > 70 ? 'badge-high' : a.suspicion_score > 30 ? 'badge-medium' : 'badge-low'}`}>
                                            {a.suspicion_score}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="flex flex-wrap gap-1">
                                            {a.detected_patterns && a.detected_patterns.map((p) => (
                                                <span key={p} className="pattern-chip">{p}</span>
                                            ))}
                                            {a.flag_hits && a.flag_hits.map((p) => (
                                                <span key={p} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/20 text-purple-400 border border-purple-500/30">{p}</span>
                                            ))}
                                        </div>
                                    </td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-accent)' }}>
                                        {a.ring_id || '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </motion.div>

            {/* Bottom: Quick Stats */}
            <motion.div
                className="grid grid-cols-2 md:grid-cols-4 gap-4"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
            >
                <div className="glass-card p-4 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-accent)' }}>
                        {stats.totalRingMembers}
                    </div>
                    <div className="metric-label">Accounts in Rings</div>
                </div>
                <div className="glass-card p-4 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-risk-orange)' }}>
                        {result.fraud_rings.filter(r => r.pattern_type === 'smurfing').length}
                    </div>
                    <div className="metric-label">Smurf Rings</div>
                </div>
                <div className="glass-card p-4 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-risk-red)' }}>
                        {result.fraud_rings.filter(r => r.pattern_type === 'cycle').length}
                    </div>
                    <div className="metric-label">Cycle Rings</div>
                </div>
                <div className="glass-card p-4 text-center">
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-text-secondary)' }}>
                        {`${s.processing_time_seconds.toFixed(2)}s`}
                    </div>
                    <div className="metric-label">Processing Time</div>
                </div>
            </motion.div>
        </div>
    );
}
