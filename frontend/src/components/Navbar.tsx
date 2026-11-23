import React from 'react';
import { ShieldCheck, Plus, FolderKanban, Activity, Terminal } from 'lucide-react';
import { Case } from '../types';

interface NavbarProps {
  cases: Case[];
  activeCaseId: string | null;
  onSelectCase: (caseId: string) => void;
  onNewCase?: () => void;
  onOpenNewCase?: () => void;
  backendHealthy?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  cases,
  activeCaseId,
  onSelectCase,
  onNewCase,
  onOpenNewCase,
  backendHealthy = true,
}) => {
  const handleNewCase = onNewCase || onOpenNewCase || (() => {});
  return (
    <header className="border-b border-slate-800 bg-[#0d121d]/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand & Track */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
                FORGE
              </span>
              <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800">
                PS-05 FORENSICS
              </span>
            </div>
            <p className="text-xs text-slate-400">Digital Evidence Authenticity & Integrity Platform</p>
          </div>
        </div>

        {/* Center / Right controls */}
        <div className="flex items-center space-x-4">
          {/* Active Case Selector */}
          {cases.length > 0 && (
            <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300">
              <FolderKanban className="w-4 h-4 text-cyan-400" />
              <span className="text-slate-400">Case:</span>
              <select
                value={activeCaseId || ''}
                onChange={(e) => onSelectCase(e.target.value)}
                className="bg-transparent border-none text-slate-200 font-mono focus:outline-none cursor-pointer"
              >
                {cases.map((c) => (
                  <option key={c.case_id} value={c.case_id} className="bg-slate-900 text-slate-200">
                    {c.case_reference} ({c.investigator_name})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* New Case Button */}
          <button
            onClick={handleNewCase}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-medium transition-all shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>New Case</span>
          </button>

          {/* System Health Badge */}
          <div className="hidden sm:flex items-center space-x-2 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs">
            <div className={`w-2 h-2 rounded-full ${backendHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
            <span className="text-slate-400 font-mono text-[11px]">
              {backendHealthy ? 'ENGINE ONLINE' : 'DISCONNECTED'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
