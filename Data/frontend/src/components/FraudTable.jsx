export default function FraudTable({ rings }) {
    if (!rings || rings.length === 0) {
        return <p className="text-sm" style={{ color: 'var(--color-text-dim)' }}>No fraud rings detected.</p>;
    }

    const sorted = [...rings].sort((a, b) => b.risk_score - a.risk_score);

    return (
        <div className="overflow-x-auto">
            <table className="threat-table">
                <thead>
                    <tr>
                        <th>Ring ID</th>
                        <th>Pattern</th>
                        <th>Members</th>
                        <th>Risk Score</th>
                        <th>Account IDs</th>
                    </tr>
                </thead>
                <tbody>
                    {sorted.map((ring) => (
                        <tr key={ring.ring_id}>
                            <td style={{ fontFamily: 'var(--font-code)', fontWeight: 700, fontSize: '0.78rem' }}>
                                {ring.ring_id}
                            </td>
                            <td className="capitalize" style={{ fontSize: '0.8rem' }}>
                                {ring.pattern_type.replace(/_/g, ' ')}
                            </td>
                            <td className="text-center" style={{ fontFamily: 'var(--font-code)' }}>
                                {ring.member_accounts.length}
                            </td>
                            <td>
                                <div className="flex items-center gap-2.5">
                                    {/* Thin progress bar */}
                                    <div className="w-14 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)' }}>
                                        <div
                                            className="h-full rounded-full"
                                            style={{
                                                width: `${ring.risk_score}%`,
                                                background: ring.risk_score > 70 ? '#E74C3C' : ring.risk_score > 40 ? '#F39C12' : '#00b8d4',
                                            }}
                                        />
                                    </div>
                                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${ring.risk_score > 70 ? 'risk-high' : ring.risk_score > 40 ? 'risk-med' : 'risk-low'
                                        }`}>
                                        {ring.risk_score}
                                    </span>
                                </div>
                            </td>
                            <td>
                                <div className="flex flex-wrap gap-1">
                                    {ring.member_accounts.slice(0, 6).map((id) => (
                                        <span key={id} className="pattern-tag">{id}</span>
                                    ))}
                                    {ring.member_accounts.length > 6 && (
                                        <span className="text-xs" style={{ color: 'var(--color-text-dim)' }}>
                                            +{ring.member_accounts.length - 6}
                                        </span>
                                    )}
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
