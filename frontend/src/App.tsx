import React, { useState, useEffect, useCallback } from 'react';
import { Case } from './types';
import { listCases, getCase } from './api';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { NewCaseModal } from './pages/NewCaseModal';
import { Shield, Plus, FolderSearch, RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const [cases, setCases] = useState<Case[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [currentCase, setCurrentCase] = useState<Case | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isNewCaseOpen, setIsNewCaseOpen] = useState<boolean>(false);

  const fetchCases = useCallback(async () => {
    try {
      const list = await listCases();
      setCases(list);
      if (list.length > 0 && !activeCaseId) {
        setActiveCaseId(list[0].case_id);
      }
    } catch (err) {
      console.error('Failed to list cases:', err);
    } finally {
      setLoading(false);
    }
  }, [activeCaseId]);

  const fetchCurrentCase = useCallback(async () => {
    if (!activeCaseId) {
      setCurrentCase(null);
      return;
    }
    try {
      const c = await getCase(activeCaseId);
      setCurrentCase(c);
    } catch (err) {
      console.error('Failed to get active case:', err);
    }
  }, [activeCaseId]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  useEffect(() => {
    fetchCurrentCase();
  }, [fetchCurrentCase]);

  const handleCaseCreated = (newCase: Case) => {
    setCases((prev) => [newCase, ...prev]);
    setActiveCaseId(newCase.case_id);
    setCurrentCase(newCase);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Forensic Navigation Bar */}
      <Navbar
        cases={cases}
        activeCaseId={activeCaseId}
        onSelectCase={(id) => setActiveCaseId(id)}
        onNewCase={() => setIsNewCaseOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 pb-16">
        {loading ? (
          <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
            <p className="text-sm font-medium">Connecting to FORGE Forensic Engine...</p>
          </div>
        ) : currentCase ? (
          <Dashboard currentCase={currentCase} onRefreshCase={fetchCurrentCase} />
        ) : (
          <div className="max-w-xl mx-auto mt-20 text-center p-8 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl space-y-5">
            <div className="p-3 bg-cyan-950/80 border border-cyan-800/80 text-cyan-400 rounded-2xl w-fit mx-auto shadow-inner">
              <Shield className="w-10 h-10" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-100">Welcome to FORGE Platform</h2>
              <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                Digital Evidence Authenticity & Integrity Verification Platform for Cyber Hackathon 2026 (PS-05).
                No case is currently active. Register a new forensics case to begin.
              </p>
            </div>
            <button
              onClick={() => setIsNewCaseOpen(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white transition-all shadow-lg shadow-cyan-950/50"
            >
              <Plus className="w-4 h-4" />
              <span>Initialize First Case</span>
            </button>
          </div>
        )}
      </main>

      {/* Forensic Legal Disclaimer & Version Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 px-6 text-center text-slate-500 text-xs">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            FORGE v1.0.0 • Cyber Hackathon 2026 (C-DAC Patna / CCSU Bihar Police PS-05)
          </span>
          <span className="text-[11px] text-slate-600">
            Chain of custody protected under Indian Evidence Act & Section 65B compliance standards.
          </span>
        </div>
      </footer>

      {/* New Case Creation Modal */}
      <NewCaseModal
        isOpen={isNewCaseOpen}
        onClose={() => setIsNewCaseOpen(false)}
        onCaseCreated={handleCaseCreated}
      />
    </div>
  );
};
export default App;
