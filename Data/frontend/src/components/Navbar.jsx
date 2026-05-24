import { useLocation, Link } from 'react-router-dom';
import { useAppContext } from '../App';

const links = [
    { to: '/dashboard', label: 'Dashboard', icon: '◈' },
    { to: '/graph', label: 'Network Graph', icon: '⬡' },
    { to: '/transactions', label: 'Transactions', icon: '▤' },
    { to: '/risk', label: 'Risk Analysis', icon: '◉' },
];

export default function Navbar() {
    const { pathname } = useLocation();
    const { user, logoutUser } = useAppContext();

    const getRoleColor = (role) => {
        if (role === 'admin') return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
        if (role === 'analyst') return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30';
        if (role === 'guest') return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30'; // viewer
    };

    return (
        <nav className="nav-bar">
            <div className="max-w-[1560px] mx-auto px-6 flex items-center justify-between h-14">
                <Link to="/dashboard" className="flex items-center gap-2 no-underline">
                    <span style={{ color: 'var(--color-accent)', fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '0.85rem', letterSpacing: '0.1em' }}>
                        MONEY<span style={{ color: 'var(--color-text-primary)' }}>MAL</span>
                    </span>
                    <span style={{ color: 'var(--color-text-dim)', fontSize: '0.65rem', fontFamily: 'var(--font-mono)' }}>v2.0</span>
                </Link>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1 mr-4">
                        {links.map((l) => (
                            <Link
                                key={l.to}
                                to={l.to}
                                className={`nav-link flex items-center gap-1.5 ${pathname === l.to ? 'active' : ''}`}
                            >
                                <span style={{ fontSize: '0.7rem' }}>{l.icon}</span>
                                {l.label}
                            </Link>
                        ))}
                    </div>
                    
                    {user && (
                        <div className="flex items-center gap-3 pl-4 border-l border-white/5">
                            <div className="flex flex-col items-end">
                                <span className="text-xs font-medium text-slate-300">{user.username}</span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase tracking-wider ${getRoleColor(user.role)}`}>
                                    {user.role}
                                </span>
                            </div>
                            <button 
                                onClick={logoutUser}
                                className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded transition-colors"
                                title="Sign Out"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                </svg>
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    );
}
