export default function ForensicCard({ node, onClose }) {
    if (!node) return null;

    const score = node.suspicion_score;
    const riskLevel = score > 70 ? 'HIGH' : score > 30 ? 'MEDIUM' : 'LOW';
    const riskColor = score > 70 ? '#E74C3C' : score > 30 ? '#F39C12' : '#00b8d4';

    return (
        <div className="forensic-backdrop" onClick={onClose}>
            <div
                className="glass-panel p-7 w-full max-w-md mx-4"
                style={{ borderColor: riskColor + '30' }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div
                            className="w-3.5 h-3.5 rounded-full"
                            style={{ background: riskColor, boxShadow: `0 0 14px ${riskColor}50` }}
                        />
                        <span
                            className="text-base font-bold"
                            style={{ fontFamily: 'var(--font-code)', color: 'var(--color-accent-primary)' }}
                        >
                            {node.id}
                        </span>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-lg leading-none cursor-pointer hover:opacity-60 transition-opacity"
                        style={{ color: 'var(--color-text-dim)' }}
                    >
                        ✕
                    </button>
                </div>

                {/* Score */}
                <div className="mb-6 p-5 rounded-xl" style={{ background: 'rgba(0,0,0,0.35)' }}>
                    <div className="text-xs uppercase tracking-[3px] mb-3" style={{ color: 'var(--color-text-dim)', fontFamily: 'var(--font-code)' }}>
                        Suspicion Score
                    </div>
                    <div className="flex items-end gap-3 mb-3">
                        <span
                            className="text-4xl font-extrabold leading-none"
                            style={{ fontFamily: 'var(--font-code)', color: riskColor, textShadow: `0 0 20px ${riskColor}30` }}
                        >
                            {score}
                        </span>
                        <span
                            className="text-[0.6rem] font-bold px-2 py-0.5 rounded-full mb-0.5"
                            style={{ background: riskColor + '15', color: riskColor, border: `1px solid ${riskColor}40` }}
                        >
                            {riskLevel}
                        </span>
                    </div>
                    <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)' }}>
                        <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{ width: `${score}%`, background: `linear-gradient(90deg, ${riskColor}60, ${riskColor})` }}
                        />
                    </div>
                </div>

                {/* Patterns */}
                <div className="mb-5">
                    <div className="text-xs uppercase tracking-[3px] mb-3" style={{ color: 'var(--color-text-dim)', fontFamily: 'var(--font-code)' }}>
                        Detected Patterns
                    </div>
                    {node.detected_patterns.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                            {node.detected_patterns.map((p) => (
                                <span key={p} className="pattern-tag">{p}</span>
                            ))}
                        </div>
                    ) : (
                        <p className="text-xs" style={{ color: 'var(--color-text-dim)' }}>None</p>
                    )}
                </div>

                {/* Explanation */}
                {node.explanation && (
                    <div className="mb-5">
                        <div className="text-xs uppercase tracking-[3px] mb-3" style={{ color: 'var(--color-text-dim)', fontFamily: 'var(--font-code)' }}>
                            Explanation
                        </div>
                        <div
                            className="p-3.5 rounded-lg text-xs leading-relaxed"
                            style={{
                                background: 'rgba(0,0,0,0.30)',
                                color: 'var(--color-text-main)',
                                fontFamily: 'var(--font-code)',
                                fontSize: '0.72rem',
                                border: '1px solid rgba(255,255,255,0.04)',
                            }}
                        >
                            {node.explanation}
                        </div>
                    </div>
                )}

                {/* Rings */}
                {node.ring_ids?.length > 0 && (
                    <div>
                        <div className="text-xs uppercase tracking-[3px] mb-3" style={{ color: 'var(--color-text-dim)', fontFamily: 'var(--font-code)' }}>
                            Associated Rings
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {node.ring_ids.map((r) => (
                                <span
                                    key={r}
                                    className="text-xs px-2.5 py-1 rounded-md font-bold"
                                    style={{
                                        background: 'rgba(231,76,60,0.08)',
                                        color: '#E74C3C',
                                        border: '1px solid rgba(231,76,60,0.2)',
                                        fontFamily: 'var(--font-code)',
                                        fontSize: '0.68rem',
                                    }}
                                >
                                    {r}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
