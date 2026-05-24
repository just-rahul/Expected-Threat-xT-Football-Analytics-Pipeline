import { useState, createContext, useContext, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import useAnalysis from './hooks/useAnalysis';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import GraphPage from './pages/GraphPage';
import TransactionsPage from './pages/TransactionsPage';
import RiskAnalysisPage from './pages/RiskAnalysisPage';
import Toast from './components/Toast';
import { login, getMe } from './services/api';

export const AppContext = createContext(null);

export function useAppContext() {
  return useContext(AppContext);
}

export default function App() {
  const analysis = useAnalysis();
  const [file, setFile] = useState(null);
  const [toast, setToast] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  
  // Auth state
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    // Restore session on load
    const token = localStorage.getItem('token');
    const guest = localStorage.getItem('guest');
    
    if (guest) {
        setUser({ role: 'guest', username: 'Guest' });
        setAuthLoading(false);
    } else if (token) {
        getMe().then(data => {
            setUser(data);
        }).catch(() => {
            localStorage.removeItem('token');
        }).finally(() => {
            setAuthLoading(false);
        });
    } else {
        setAuthLoading(false);
    }
  }, []);

  const loginUser = async (username, password) => {
      if (username === 'guest') {
          localStorage.setItem('guest', 'true');
          setUser({ role: 'guest', username: 'Guest' });
          return;
      }
      
      const data = await login(username, password);
      localStorage.setItem('token', data.access_token);
      setUser({ role: data.role, username });
  };
  
  const logoutUser = () => {
      localStorage.removeItem('token');
      localStorage.removeItem('guest');
      setUser(null);
      // reset analysis on logout
      analysis.reset();
  };

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const ctx = {
    ...analysis,
    file,
    setFile,
    selectedNode,
    setSelectedNode,
    showToast,
    user,
    loginUser,
    logoutUser
  };

  if (authLoading) return <div className="min-h-screen bg-[#0A0D14] flex items-center justify-center text-cyan-500">Loading...</div>;

  return (
    <AppContext.Provider value={ctx}>
      <BrowserRouter>
        {!user ? (
            <LoginPage />
        ) : (
            <>
                {analysis.result && <Navbar />}
                <Routes>
                  <Route path="/" element={analysis.result ? <Dashboard /> : <LandingPage />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/graph" element={<GraphPage />} />
                  <Route path="/transactions" element={<TransactionsPage />} />
                  <Route path="/risk" element={<RiskAnalysisPage />} />
                  <Route path="*" element={<Navigate to="/" />} />
                </Routes>
            </>
        )}
        {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </BrowserRouter>
    </AppContext.Provider>
  );
}
