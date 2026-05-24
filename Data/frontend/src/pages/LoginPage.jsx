import { useState } from 'react';
import { useAppContext } from '../App';

export default function LoginPage() {
    const { loginUser } = useAppContext();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await loginUser(username, password);
        } catch (err) {
            setError('Invalid credentials');
        } finally {
            setLoading(false);
        }
    };

    const handleGuest = () => {
        loginUser('guest', null);
    };

    return (
        <div className="min-h-screen bg-[#0A0D14] flex items-center justify-center p-4">
            <div className="max-w-md w-full bg-[#111822] p-8 rounded-xl border border-white/5 shadow-2xl relative overflow-hidden">
                {/* Decorative glow */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-64 bg-cyan-500/10 blur-[100px] pointer-events-none" />

                <div className="relative z-10">
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-cyan-500/10 text-cyan-400 mb-4 border border-cyan-500/20">
                            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">MoneyMal V2.0</h1>
                        <p className="text-slate-400">Financial Forensics Engine</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm text-center">
                                {error}
                            </div>
                        )}
                        
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1">Username</label>
                            <input 
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="w-full bg-[#0A0D14] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
                                placeholder="Enter username"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1">Password</label>
                            <input 
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-[#0A0D14] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
                                placeholder="••••••••"
                                required
                            />
                        </div>

                        <button 
                            type="submit"
                            disabled={loading}
                            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium py-2.5 rounded-lg transition-colors mt-6 disabled:opacity-50"
                        >
                            {loading ? 'Authenticating...' : 'Sign In'}
                        </button>
                    </form>

                    <div className="mt-8 pt-6 border-t border-white/5 space-y-4">
                        <p className="text-sm text-slate-500 text-center font-medium">Demo Credentials</p>
                        <div className="grid grid-cols-2 gap-3">
                            <button 
                                onClick={() => { setUsername('admin'); setPassword('Admin2026!'); }}
                                className="text-left px-4 py-2 bg-purple-500/5 hover:bg-purple-500/10 border border-purple-500/10 hover:border-purple-500/30 rounded-lg transition-colors group"
                            >
                                <div className="text-xs text-purple-400 font-semibold mb-0.5">Admin</div>
                                <div className="text-[10px] text-slate-500 group-hover:text-slate-400 truncate">admin/Admin2026!</div>
                            </button>
                            <button 
                                onClick={() => { setUsername('analyst'); setPassword('Analyst2026!'); }}
                                className="text-left px-4 py-2 bg-cyan-500/5 hover:bg-cyan-500/10 border border-cyan-500/10 hover:border-cyan-500/30 rounded-lg transition-colors group"
                            >
                                <div className="text-xs text-cyan-400 font-semibold mb-0.5">Analyst</div>
                                <div className="text-[10px] text-slate-500 group-hover:text-slate-400 truncate">analyst/Analyst2026!</div>
                            </button>
                        </div>
                        
                        <button 
                            onClick={handleGuest}
                            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors mt-4 text-sm text-slate-300"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                            Continue as Guest
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
