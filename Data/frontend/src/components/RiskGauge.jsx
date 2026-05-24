import { useMemo } from 'react';

export default function RiskGauge({ score = 0 }) {
    const normalized = Math.min(100, Math.max(0, score));
    const angle = -135 + (normalized / 100) * 270;

    const getColor = (s) => {
        if (s > 70) return '#FF3B3B';
        if (s > 30) return '#FF9F1C';
        return '#00FF94';
    };

    const label = useMemo(() => {
        if (normalized > 70) return 'CRITICAL';
        if (normalized > 50) return 'HIGH';
        if (normalized > 30) return 'MODERATE';
        return 'LOW';
    }, [normalized]);

    const color = getColor(normalized);

    return (
        <div style={{ position: 'relative', width: 180, height: 110 }}>
            <svg viewBox="0 0 200 120" style={{ width: '100%', height: '100%' }}>
                {/* Background arc */}
                <path
                    d="M 20 100 A 80 80 0 1 1 180 100"
                    fill="none"
                    stroke="rgba(0, 245, 255, 0.08)"
                    strokeWidth="10"
                    strokeLinecap="round"
                />
                {/* Colored arc */}
                <path
                    d="M 20 100 A 80 80 0 1 1 180 100"
                    fill="none"
                    stroke={color}
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray={`${(normalized / 100) * 251} 251`}
                    style={{ filter: `drop-shadow(0 0 8px ${color}50)`, transition: 'stroke-dasharray 1s ease' }}
                />
                {/* Needle */}
                <line
                    x1="100"
                    y1="100"
                    x2={100 + 55 * Math.cos((angle * Math.PI) / 180)}
                    y2={100 + 55 * Math.sin((angle * Math.PI) / 180)}
                    stroke={color}
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    style={{ transition: 'all 1s ease', filter: `drop-shadow(0 0 4px ${color})` }}
                />
                {/* Center dot */}
                <circle cx="100" cy="100" r="5" fill={color} style={{ filter: `drop-shadow(0 0 6px ${color})` }} />
                {/* Score text */}
                <text x="100" y="88" textAnchor="middle" fill={color} fontFamily="var(--font-mono)" fontWeight="700" fontSize="22">
                    {normalized.toFixed(0)}
                </text>
            </svg>
            <div style={{ textAlign: 'center', marginTop: -8 }}>
                <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    color,
                    letterSpacing: '0.12em',
                }}>
                    {label}
                </span>
            </div>
        </div>
    );
}
