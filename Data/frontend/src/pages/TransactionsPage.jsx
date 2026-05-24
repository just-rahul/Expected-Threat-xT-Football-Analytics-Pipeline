import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../App';

export default function TransactionsPage() {
    const { result } = useAppContext();
    const navigate = useNavigate();
    const [search, setSearch] = useState('');
    const [filterRisk, setFilterRisk] = useState('all');
    const [sortBy, setSortBy] = useState('score');
    const [sortDir, setSortDir] = useState('desc');

    if (!result) { navigate('/'); return null; }

    const accounts = useMemo(() => {
        let list = [...(result.suspicious_accounts || [])];

        if (search) {
            const q = search.toLowerCase();
            list = list.filter((a) =>
                a.account_id.toLowerCase().includes(q) ||
                a.detected_patterns.some((p) => p.toLowerCase().includes(q)) ||
                (a.ring_id && a.ring_id.toLowerCase().includes(q))
            );
        }

        if (filterRisk !== 'all') {
            list = list.filter((a) => {
                if (filterRisk === 'high') return a.suspicion_score > 70;
                if (filterRisk === 'medium') return a.suspicion_score > 30 && a.suspicion_score <= 70;
                if (filterRisk === 'low') return a.suspicion_score <= 30;
                return true;
            });
        }

        list.sort((a, b) => {
            let va, vb;
            if (sortBy === 'score') { va = a.suspicion_score; vb = b.suspicion_score; }
            else if (sortBy === 'id') { va = a.account_id; vb = b.account_id; }
            else if (sortBy === 'ring') { va = a.ring_id || ''; vb = b.ring_id || ''; }
            else { va = a.detected_patterns.length; vb = b.detected_patterns.length; }
            if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
            return sortDir === 'asc' ? va - vb : vb - va;
        });

        return list;
    }, [result, search, filterRisk, sortBy, sortDir]);

    const exportJSON = () => {
        const output = {
            suspicious_accounts: (result.suspicious_accounts || []).map((a) => ({
                account_id: a.account_id,
                suspicion_score: a.suspicion_score,
                detected_patterns: a.detected_patterns || [],
                ring_id: a.ring_id || null,
            })),
            fraud_rings: (result.fraud_rings || []).map((r) => ({
                ring_id: r.ring_id,
                member_accounts: r.member_accounts || r.accounts || [],
                pattern_type: r.pattern_type || r.type || 'unknown',
                risk_score: r.risk_score ?? r.score ?? 0,
            })),
            summary: {
                total_accounts_analyzed: result.summary?.total_accounts_analyzed ?? 0,
                suspicious_accounts_flagged: result.summary?.suspicious_accounts_flagged ?? (result.suspicious_accounts || []).length,
                fraud_rings_detected: result.summary?.fraud_rings_detected ?? (result.fraud_rings || []).length,
                processing_time_seconds: result.summary?.processing_time_seconds ?? 0,
            },
        };
        const jsonStr = JSON.stringify(output, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'analysis_results.json';
        a.click();
        URL.revokeObjectURL(url);
    };

    const toggleSort = (col) => {
        if (sortBy === col) setSortDir((d) => d === 'asc' ? 'desc' : 'asc');
        else { setSortBy(col); setSortDir('desc'); }
    };

    const SortIcon = ({ col }) => (
        <span style={{ color: sortBy === col ? 'var(--color-accent)' : 'var(--color-text-dim)', marginLeft: 4, fontSize: '0.6rem' }}>
            {sortBy === col ? (sortDir === 'asc' ? '▲' : '▼') : '⬍'}
        </span>
    );

    return (
        <div className="max-w-[1560px] mx-auto px-6 py-6">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <h1 style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '1.4rem', letterSpacing: '0.1em' }}>
                    <span style={{ color: 'var(--color-accent)' }}>SUSPICIOUS</span> ACCOUNTS
                </h1>
                <p style={{ color: 'var(--color-text-dim)', fontSize: '0.72rem', marginTop: '4px' }}>
                    {accounts.length} accounts · Filterable, sortable, exportable
                </p>
            </motion.div>

            {/* Controls */}
            <motion.div
                className="glass-card p-4 mt-6 mb-6 flex flex-wrap items-center gap-4"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
            >
                <div className="flex-1 min-w-[200px]">
                    <input
                        type="text"
                        placeholder="Search accounts, patterns, rings..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        style={{
                            width: '100%',
                            background: 'rgba(0, 245, 255, 0.04)',
                            border: '1px solid var(--color-border)',
                            borderRadius: '8px',
                            padding: '10px 14px',
                            color: 'var(--color-text-primary)',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.78rem',
                            outline: 'none',
                        }}
                    />
                </div>
                <div className="flex items-center gap-2">
                    {['all', 'high', 'medium', 'low'].map((r) => (
                        <button
                            key={r}
                            onClick={() => setFilterRisk(r)}
                            className="btn-primary"
                            style={{
                                padding: '6px 12px',
                                fontSize: '0.68rem',
                                background: filterRisk === r ? 'rgba(0, 245, 255, 0.2)' : 'rgba(0, 245, 255, 0.05)',
                                textTransform: 'capitalize',
                            }}
                        >
                            {r === 'all' ? 'All Risk' : `${r} Risk`}
                        </button>
                    ))}
                </div>
                <button className="btn-primary" onClick={exportJSON} style={{ padding: '6px 14px', fontSize: '0.7rem' }}>
                    ⬇ Export JSON
                </button>
            </motion.div>

            {/* Table */}
            <motion.div
                className="glass-card overflow-hidden"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
            >
                <div style={{ maxHeight: 'calc(100vh - 320px)', overflow: 'auto' }}>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th onClick={() => toggleSort('id')} style={{ cursor: 'pointer' }}>
                                    Account ID <SortIcon col="id" />
                                </th>
                                <th onClick={() => toggleSort('score')} style={{ cursor: 'pointer' }}>
                                    Fraud Score <SortIcon col="score" />
                                </th>
                                <th onClick={() => toggleSort('patterns')} style={{ cursor: 'pointer' }}>
                                    Patterns <SortIcon col="patterns" />
                                </th>
                                <th onClick={() => toggleSort('ring')} style={{ cursor: 'pointer' }}>
                                    Ring ID <SortIcon col="ring" />
                                </th>
                                <th>Risk Level</th>
                                <th>Explanation</th>
                            </tr>
                        </thead>
                        <tbody>
                            {accounts.map((a) => (
                                <tr key={a.account_id}>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.75rem' }}>
                                        {a.account_id}
                                    </td>
                                    <td>
                                        <div className="flex items-center gap-2">
                                            <span className={`badge ${a.suspicion_score > 70 ? 'badge-high' : a.suspicion_score > 30 ? 'badge-medium' : 'badge-low'}`}>
                                                {a.suspicion_score}
                                            </span>
                                            <div style={{ flex: 1, maxWidth: 80, height: 4, background: 'rgba(0,245,255,0.08)', borderRadius: 2 }}>
                                                <div
                                                    style={{
                                                        height: '100%',
                                                        width: `${a.suspicion_score}%`,
                                                        borderRadius: 2,
                                                        background: a.suspicion_score > 70 ? 'var(--color-risk-red)' : a.suspicion_score > 30 ? 'var(--color-risk-orange)' : 'var(--color-risk-green)',
                                                    }}
                                                />
                                            </div>
                                        </div>
                                    </td>
                                    <td>
                                        <div className="flex flex-wrap gap-1">
                                            {a.detected_patterns.map((p) => (
                                                <span key={p} className="pattern-chip">{p}</span>
                                            ))}
                                        </div>
                                    </td>
                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-accent)' }}>
                                        {a.ring_id || '—'}
                                    </td>
                                    <td>
                                        <span className={`badge ${a.suspicion_score > 70 ? 'badge-high' : a.suspicion_score > 30 ? 'badge-medium' : 'badge-low'}`}>
                                            {a.suspicion_score > 70 ? 'HIGH RISK' : a.suspicion_score > 30 ? 'SUSPICIOUS' : 'LOW'}
                                        </span>
                                    </td>
                                    <td style={{ fontSize: '0.68rem', color: 'var(--color-text-dim)', maxWidth: '220px', fontFamily: 'var(--font-mono)' }}>
                                        {a.explanation || '—'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </motion.div>
        </div>
    );
}
