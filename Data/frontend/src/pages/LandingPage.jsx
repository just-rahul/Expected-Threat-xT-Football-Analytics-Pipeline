import { useRef, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAppContext } from '../App';

/* ── Particle Network Background ── */
function ParticleCanvas() {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let animId;
        let particles = [];

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        resize();
        window.addEventListener('resize', resize);

        class Particle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.vx = (Math.random() - 0.5) * 0.4;
                this.vy = (Math.random() - 0.5) * 0.4;
                this.r = Math.random() * 2 + 1;
                this.alpha = Math.random() * 0.5 + 0.1;
            }
            update() {
                this.x += this.vx;
                this.y += this.vy;
                if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
                if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
            }
            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(0, 245, 255, ${this.alpha})`;
                ctx.fill();
            }
        }

        for (let i = 0; i < 80; i++) particles.push(new Particle());

        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach((p) => { p.update(); p.draw(); });

            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 150) {
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.strokeStyle = `rgba(0, 245, 255, ${0.08 * (1 - dist / 150)})`;
                        ctx.lineWidth = 0.5;
                        ctx.stroke();
                    }
                }
            }
            animId = requestAnimationFrame(animate);
        }
        animate();

        return () => {
            cancelAnimationFrame(animId);
            window.removeEventListener('resize', resize);
        };
    }, []);

    return <canvas ref={canvasRef} style={{ position: 'fixed', inset: 0, zIndex: 0 }} />;
}

export default function LandingPage() {
    const { file, setFile, analyze, loading, error, progress, showToast } = useAppContext();
    const navigate = useNavigate();
    const [dragOver, setDragOver] = useState(false);

    const handleFile = useCallback((f) => {
        if (f && f.name.endsWith('.csv')) {
            setFile(f);
            showToast(`Loaded: ${f.name} (${(f.size / 1024).toFixed(0)} KB)`, 'success');
        } else {
            showToast('Please upload a CSV file', 'error');
        }
    }, [setFile, showToast]);

    const handleAnalyze = useCallback(async () => {
        if (!file) return;
        await analyze(file);
        navigate('/dashboard');
    }, [file, analyze, navigate]);

    return (
        <div className="relative min-h-screen flex items-center justify-center overflow-hidden">
            <ParticleCanvas />
            <div className="landing-gradient" />

            <motion.div
                className="relative z-10 text-center max-w-2xl mx-auto px-6"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
            >
                {/* Logo */}
                <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.2, duration: 0.6 }}
                >
                    <h1 style={{ fontFamily: 'var(--font-mono)', fontWeight: 900, fontSize: '3.2rem', letterSpacing: '0.15em', lineHeight: 1 }}>
                        <span style={{ color: 'var(--color-accent)' }}>MONEY</span>
                        <span style={{ color: 'var(--color-text-primary)' }}>MAL</span>
                    </h1>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginTop: '12px', letterSpacing: '0.04em' }}>
                        AI-Powered Graph Intelligence for Financial Crime Detection
                    </p>
                </motion.div>

                {/* Upload Section */}
                <motion.div
                    className="mt-12"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5, duration: 0.6 }}
                >
                    <div
                        className={`upload-zone ${dragOver ? 'active' : ''}`}
                        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                        onDragLeave={() => setDragOver(false)}
                        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
                        onClick={() => document.getElementById('csv-upload').click()}
                    >
                        <input
                            id="csv-upload"
                            type="file"
                            accept=".csv"
                            className="hidden"
                            onChange={(e) => handleFile(e.target.files[0])}
                        />
                        {file ? (
                            <div>
                                <div style={{ fontSize: '2rem', color: 'var(--color-risk-green)', marginBottom: '8px' }}>✓</div>
                                <p style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-accent)', fontWeight: 600, fontSize: '0.9rem' }}>
                                    {file.name}
                                </p>
                                <p style={{ color: 'var(--color-text-dim)', fontSize: '0.75rem', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
                                    {(file.size / 1024).toFixed(1)} KB — Ready to analyze
                                </p>
                            </div>
                        ) : (
                            <div>
                                <div style={{ fontSize: '2.5rem', opacity: 0.3, marginBottom: '12px' }}>⬆</div>
                                <p style={{ color: 'var(--color-text-primary)', fontSize: '0.9rem', fontWeight: 500 }}>
                                    Drop transaction CSV here or click to browse
                                </p>
                                <p style={{ color: 'var(--color-text-dim)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem', marginTop: '10px' }}>
                                    Required: transaction_id · sender_id · receiver_id · amount · timestamp
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Progress Bar */}
                    {loading && (
                        <motion.div
                            className="mt-6"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                        >
                            <div className="progress-bar-container">
                                <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
                            </div>
                            <p style={{ color: 'var(--color-accent)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', marginTop: '10px' }}>
                                Building graph · Running detection · Scoring accounts...
                            </p>
                        </motion.div>
                    )}

                    {error && (
                        <motion.div
                            className="mt-4 glass-card p-4"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            style={{ borderColor: 'rgba(255, 59, 59, 0.3)' }}
                        >
                            <span style={{ color: 'var(--color-risk-red)', fontSize: '0.8rem' }}>✕ {error}</span>
                        </motion.div>
                    )}

                    <motion.button
                        className="btn-glow mt-8"
                        disabled={!file || loading}
                        onClick={handleAnalyze}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        {loading ? '◌ ANALYZING...' : '▶ LAUNCH ANALYSIS'}
                    </motion.button>
                </motion.div>

                {/* Bottom info */}
                <motion.div
                    className="mt-16 flex justify-center gap-8"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.8 }}
                >
                    {['Cycle Detection', 'Shell Networks', 'Smurfing', 'Structuring'].map((f) => (
                        <span key={f} style={{ color: 'var(--color-text-dim)', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', letterSpacing: '0.05em' }}>
                            {f}
                        </span>
                    ))}
                </motion.div>
            </motion.div>
        </div>
    );
}
