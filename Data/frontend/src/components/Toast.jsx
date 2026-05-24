import { motion, AnimatePresence } from 'framer-motion';

export default function Toast({ message, type = 'info', onClose }) {
    return (
        <AnimatePresence>
            <motion.div
                className={`toast toast-${type}`}
                initial={{ opacity: 0, y: 40, x: 0 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 40 }}
                transition={{ duration: 0.3 }}
            >
                <div className="flex items-center gap-3">
                    <span style={{ fontSize: '1.1rem' }}>
                        {type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}
                    </span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--color-text-primary)' }}>{message}</span>
                    <button
                        onClick={onClose}
                        style={{ marginLeft: 'auto', color: 'var(--color-text-dim)', cursor: 'pointer', background: 'none', border: 'none', fontSize: '1rem' }}
                    >
                        ×
                    </button>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
