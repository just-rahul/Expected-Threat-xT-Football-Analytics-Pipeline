export default function FraudRingTable({ rings, accounts = [] }) {
    if (!rings || rings.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: 20, color: 'var(--color-text-dim)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                No fraud rings detected
            </div>
        );
    }

    const getDecision = (members) => {
        if (!accounts || accounts.length === 0) return 'REVIEW';
        const memberDecisions = members.map(m => {
            const acc = accounts.find(a => a.account_id === m);
            return acc ? acc.decision || 'APPROVE' : 'APPROVE';
        });
        if (memberDecisions.includes('BLOCK')) return 'BLOCK';
        if (memberDecisions.includes('REVIEW')) return 'REVIEW';
        return 'APPROVE';
    };

    return (
        <div style={{ maxHeight: 350, overflow: 'auto' }}>
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Ring ID</th>
                        <th>Members</th>
                        <th>Pattern Type</th>
                        <th>Risk Score</th>
                        <th>Recommendation</th>
                    </tr>
                </thead>
                <tbody>
                    {rings.map((ring) => (
                        <tr key={ring.ring_id}>
                            <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.78rem', color: 'var(--color-accent)' }}>
                                {ring.ring_id}
                            </td>
                            <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.8rem' }}>
                                {ring.member_accounts.length}
                            </td>
                            <td>
                                <span className="pattern-chip">{ring.pattern_type}</span>
                            </td>
                            <td>
                                <div className="flex items-center gap-2">
                                    <div style={{ width: 80, height: 6, background: 'rgba(0,245,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
                                        <div
                                            style={{
                                                height: '100%',
                                                width: `${ring.risk_score}%`,
                                                borderRadius: 3,
                                                background: ring.risk_score > 80 ? 'var(--color-risk-red)' : ring.risk_score > 50 ? 'var(--color-risk-orange)' : 'var(--color-risk-green)',
                                                transition: 'width 0.5s',
                                            }}
                                        />
                                    </div>
                                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 600, color: ring.risk_score > 80 ? 'var(--color-risk-red)' : 'var(--color-text-secondary)' }}>
                                        {ring.risk_score}%
                                    </span>
                                </div>
                            </td>
                            <td>
                                {getDecision(ring.member_accounts) === 'BLOCK' ? <span className="px-2 py-1 text-[10px] bg-red-500/20 text-red-400 border border-red-500/30 rounded dark-text">BLOCK</span> : 
                                 getDecision(ring.member_accounts) === 'REVIEW' ? <span className="px-2 py-1 text-[10px] bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 rounded">REVIEW</span> :
                                 <span className="px-2 py-1 text-[10px] bg-green-500/20 text-green-400 border border-green-500/30 rounded">APPROVE</span>}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
