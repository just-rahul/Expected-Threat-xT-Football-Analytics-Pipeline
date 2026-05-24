import { useState, useCallback } from 'react';
import { analyzeFile } from '../services/api';

export default function useAnalysis() {
    const [result, setResult] = useState(null);
    const [graphData, setGraphData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [progress, setProgress] = useState(0);

    const analyze = useCallback(async (file) => {
        if (!file) return;
        setLoading(true);
        setError(null);
        setResult(null);
        setGraphData(null);
        setProgress(10);

        try {
            setProgress(30);
            const data = await analyzeFile(file, (p) => setProgress(p));
            setProgress(90);
            setResult(data.result);
            setGraphData(data.graph);
            setProgress(100);
        } catch (e) {
            const msg = e.response?.data?.detail || e.message || 'Analysis failed';
            setError(msg);
        } finally {
            setLoading(false);
            setTimeout(() => setProgress(0), 500);
        }
    }, []);

    const reset = useCallback(() => {
        setResult(null);
        setGraphData(null);
        setError(null);
        setProgress(0);
    }, []);

    return { result, graphData, loading, error, progress, analyze, reset };
}
