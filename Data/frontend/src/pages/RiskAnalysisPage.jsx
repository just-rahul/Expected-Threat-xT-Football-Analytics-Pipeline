import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import { useAppContext } from '../App';

const COLORS = ['#FF3B3B', '#FF9F1C', '#00F5FF', '#00FF94', '#8B5CF6', '#EC4899', '#F59E0B', '#6366F1'];

export default function RiskAnalysisPage() {
    const { result } = useAppContext();
    const navigate = useNavigate();

    if (!result) { navigate('/'); return null; }

    const accounts = result.suspicious_accounts || [];
    const rings = result.fraud_rings || [];

    /* ── Chart Data ── */
    const scoreDistribution = useMemo(() => {
        const buckets = [
            { range: '0-10', count: 0 }, { range: '10-20', count: 0 }, { range: '20-30', count: 0 },
            { range: '30-40', count: 0 }, { range: '40-50', count: 0 }, { range: '50-60', count: 0 },
            { range: '60-70', count: 0 }, { range: '70-80', count: 0 }, { range: '80-90', count: 0 },
            { range: '90-100', count: 0 },
        ];
        accounts.forEach((a) => {
            const idx = Math.min(Math.floor(a.suspicion_score / 10), 9);
            buckets[idx].count++;
        });
        return buckets;
    }, [accounts]);

    const top10 = useMemo(() =>
        [...accounts].sort((a, b) => b.suspicion_score - a.suspicion_score).slice(0, 10).map((a) => ({
            name: a.account_id.length > 12 ? a.account_id.slice(0, 12) + '…' : a.account_id,
            score: a.suspicion_score,
            fullId: a.account_id,
        })),
        [accounts]
    );

    const patternDist = useMemo(() => {
        const counts = {};
        accounts.forEach((a) => a.detected_patterns.forEach((p) => { counts[p] = (counts[p] || 0) + 1; }));
        return Object.entries(counts).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
    }, [accounts]);

    const ringTypeData = useMemo(() => {
        const counts = {};
        rings.forEach((r) => { counts[r.pattern_type] = (counts[r.pattern_type] || 0) + 1; });
        return Object.entries(counts).map(([name, value]) => ({ name, value }));
    }, [rings]);

    const ringSizeData = useMemo(() =>
        rings.map((r) => ({
            name: r.ring_id,
            members: r.member_accounts.length,
            risk: r.risk_score,
        })),
        [rings]
    );

    const CustomTooltip = ({ active, payload, label }) => {
        if (!active || !payload?.length) return null;
        return (
            <div style={{
                background: 'rgba(11, 15, 26, 0.95)',
                border: '1px solid rgba(0, 245, 255, 0.2)',
                borderRadius: 8,
                padding: '8px 12px',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.7rem',
                color: 'var(--color-text-primary)',
            }}>
                <p style={{ color: 'var(--color-accent)', fontWeight: 600, marginBottom: 4 }}>{label}</p>
                {payload.map((p, i) => (
                    <p key={i} style={{ color: p.color || 'var(--color-text-secondary)' }}>
                        {p.name}: {p.value}
                    </p>
                ))}
            </div>
        );
    };

    return (
        <div className="max-w-[1560px] mx-auto px-6 py-6">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <h1 style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '1.4rem', letterSpacing: '0.1em' }}>
                    <span style={{ color: 'var(--color-accent)' }}>RISK</span> ANALYSIS
                </h1>
                <p style={{ color: 'var(--color-text-dim)', fontSize: '0.72rem', marginTop: '4px' }}>
                    Statistical analysis of fraud detection results
                </p>
            </motion.div>

            {/* Grid of Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-8">
                {/* Fraud Score Distribution */}
                <motion.div
                    className="glass-card p-5"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                >
                    <h3 style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: 16, letterSpacing: '0.06em' }}>
                        FRAUD SCORE DISTRIBUTION
                    </h3>
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={scoreDistribution}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,245,255,0.06)" />
                            <XAxis dataKey="range" tick={{ fontSize: 10, fill: '#8B95A8' }} />
                            <YAxis tick={{ fontSize: 10, fill: '#8B95A8' }} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                {scoreDistribution.map((entry, i) => (
                                    <Cell key={i} fill={i >= 7 ? '#FF3B3B' : i >= 3 ? '#FF9F1C' : '#00FF94'} fillOpacity={0.75} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </motion.div>

                {/* Top 10 High Risk */}
                <motion.div
                    className="glass-card p-5"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <h3 style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: 16, letterSpacing: '0.06em' }}>
                        TOP 10 HIGH RISK ACCOUNTS
                    </h3>
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={top10} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,245,255,0.06)" />
                            <XAxis type="number" tick={{ fontSize: 10, fill: '#8B95A8' }} domain={[0, 100]} />
                            <YAxis dataKey="name" type="category" tick={{ fontSize: 9, fill: '#8B95A8' }} width={110} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                                {top10.map((entry, i) => (
                                    <Cell key={i} fill={entry.score > 70 ? '#FF3B3B' : entry.score > 30 ? '#FF9F1C' : '#00FF94'} fillOpacity={0.8} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </motion.div>

                {/* Pattern Distribution Pie */}
                <motion.div
                    className="glass-card p-5"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                >
                    <h3 style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: 16, letterSpacing: '0.06em' }}>
                        DETECTED PATTERN TYPES
                    </h3>
                    <div className="flex items-center gap-4">
                        <div style={{ flex: 1 }}>
                            <ResponsiveContainer width="100%" height={250}>
                                <PieChart>
                                    <Pie
                                        data={patternDist}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={60}
                                        outerRadius={95}
                                        paddingAngle={3}
                                        dataKey="value"
                                    >
                                        {patternDist.map((entry, i) => (
                                            <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.8} />
                                        ))}
                                    </Pie>
                                    <Tooltip content={<CustomTooltip />} />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="flex flex-col gap-2" style={{ minWidth: 140 }}>
                            {patternDist.slice(0, 8).map((p, i) => (
                                <div key={p.name} className="flex items-center gap-2" style={{ fontSize: '0.68rem' }}>
                                    <span style={{ width: 8, height: 8, borderRadius: 2, background: COLORS[i % COLORS.length], display: 'inline-block', flexShrink: 0 }} />
                                    <span style={{ color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>{p.name}</span>
                                    <span style={{ marginLeft: 'auto', color: 'var(--color-text-dim)', fontFamily: 'var(--font-mono)' }}>{p.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </motion.div>

                {/* Ring Size Distribution */}
                <motion.div
                    className="glass-card p-5"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                >
                    <h3 style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: 16, letterSpacing: '0.06em' }}>
                        RING SIZE & RISK SCORES
                    </h3>
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={ringSizeData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,245,255,0.06)" />
                            <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#8B95A8' }} />
                            <YAxis tick={{ fontSize: 10, fill: '#8B95A8' }} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="members" fill="#00F5FF" fillOpacity={0.6} radius={[4, 4, 0, 0]} name="Members" />
                            <Bar dataKey="risk" fill="#FF3B3B" fillOpacity={0.6} radius={[4, 4, 0, 0]} name="Risk Score" />
                        </BarChart>
                    </ResponsiveContainer>
                </motion.div>

                {/* Ring Types Pie */}
                <motion.div
                    className="glass-card p-5"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                >
                    <h3 style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: 16, letterSpacing: '0.06em' }}>
                        MULE TYPES DETECTED
                    </h3>
                    <div className="flex items-center justify-center gap-8">
                        <ResponsiveContainer width="60%" height={220}>
                            <PieChart>
                                <Pie
                                    data={ringTypeData}
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={80}
                                    dataKey="value"
                                    label={({ name, value }) => `${name}: ${value}`}
                                >
                                    {ringTypeData.map((entry, i) => (
                                        <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.8} />
                                    ))}
                                </Pie>
                                <Tooltip content={<CustomTooltip />} />
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="flex flex-col gap-3">
                            {ringTypeData.map((r, i) => (
                                <div key={r.name} className="flex items-center gap-2" style={{ fontSize: '0.75rem' }}>
                                    <span style={{ width: 10, height: 10, borderRadius: 3, background: COLORS[i % COLORS.length] }} />
                                    <span style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', fontWeight: 500 }}>{r.name}</span>
                                    <span className="badge badge-medium" style={{ marginLeft: 4 }}>{r.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </motion.div>

                {/* Summary Stats Card */}
                <motion.div
                    className="glass-card p-5"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                >
                    <h3 style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: 16, letterSpacing: '0.06em' }}>
                        INTELLIGENCE SUMMARY
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                            { label: 'Total Accounts', value: result.summary.total_accounts_analyzed, color: 'var(--color-accent)' },
                            { label: 'Flagged', value: result.summary.suspicious_accounts_flagged, color: 'var(--color-text-primary)' },
                            { label: 'Mandatory BLOCK', value: accounts.filter(a => a.decision === 'BLOCK').length, color: 'var(--color-risk-red)' },
                            { label: 'Manual REVIEW', value: accounts.filter(a => a.decision === 'REVIEW').length, color: 'var(--color-risk-orange)' },
                            { label: 'Fraud Rings', value: result.summary.fraud_rings_detected, color: 'var(--color-risk-orange)' },
                            { label: 'Processing', value: `${result.summary.processing_time_seconds.toFixed(2)}s`, color: 'var(--color-risk-green)' },
                            { label: 'Avg ML Score', value: accounts.length ? (accounts.reduce((s, a) => s + a.suspicion_score, 0) / accounts.length).toFixed(1) : '0', color: 'var(--color-accent)' },
                            { label: 'Hub Nodes', value: accounts.filter(a => a.role === 'HUB').length, color: '#9B59B6' },
                        ].map((s) => (
                            <div key={s.label} className="glass-card p-3 text-center">
                                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.3rem', fontWeight: 700, color: s.color }}>{s.value}</div>
                                <div className="metric-label">{s.label}</div>
                            </div>
                        ))}
                    </div>
                </motion.div>
            </div>

            {/* Suspicious Accounts Detailed Table */}
            <motion.div
                className="glass-card p-5 mt-5"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
            >
                <h3 style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: 16, letterSpacing: '0.06em' }}>
                    SUSPICIOUS ACCOUNTS INDEX
                </h3>
                <div style={{ maxHeight: 400, overflow: 'auto' }}>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Account ID</th>
                                <th>Score</th>
                                <th>Role</th>
                                <th>Decision</th>
                                <th>Flags</th>
                                <th>Ring ID</th>
                                <th>GAT %</th>
                                <th>LSTM %</th>
                                <th>EIF %</th>
                                <th>xMLT Threat</th>
                                <th>Markov Flow %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {accounts.map((acc, i) => (
                                <tr key={i}>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-accent)' }}>{acc.account_id}</td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 'bold' }}>{acc.suspicion_score.toFixed(1)}</td>
                                    <td><span className={`px-2 py-1 text-[10px] rounded font-mono border uppercase ${acc.role === 'HUB' ? 'bg-purple-500/20 text-purple-400 border-purple-500/30' : acc.role === 'BRIDGE' ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' : 'bg-slate-500/20 text-slate-400 border-slate-500/30'}`}>{acc.role || 'LEAF'}</span></td>
                                    <td>
                                        <span className={`px-2 py-1 text-[10px] rounded font-mono border uppercase ${acc.decision === 'BLOCK' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : acc.decision === 'REVIEW' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' : 'bg-green-500/20 text-green-400 border border-green-500/30'}`}>
                                            {acc.decision || 'APPROVE'}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="flex gap-1 flex-wrap">
                                            {(acc.flag_hits || []).map(f => <span key={f} className="pattern-chip" style={{fontSize: '0.65rem', padding: '2px 4px', whiteSpace: 'nowrap'}}>{f}</span>)}
                                        </div>
                                    </td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--color-text-dim)' }}>{acc.ring_id || 'NONE'}</td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>{acc.ml_scores?.gat?.toFixed(1) || '0.0'}</td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>{acc.ml_scores?.lstm?.toFixed(1) || '0.0'}</td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>{acc.ml_scores?.eif?.toFixed(1) || '0.0'}</td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: '#FF3B3B', fontWeight: 'bold' }}>{acc.xmlt_score?.toFixed(1) || '0.0'}</td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: '#00F5FF', fontWeight: 'bold' }}>{(acc.markov_flow || 0.0).toFixed(1)}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </motion.div>
        </div>
    );
}
