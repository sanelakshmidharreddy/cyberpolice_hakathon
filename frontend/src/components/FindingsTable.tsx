import React, { useState } from 'react';
import { Finding, FindingResult, ModuleResult } from '../types';
import { CheckCircle, AlertTriangle, AlertOctagon, HelpCircle, MinusCircle, ChevronDown, ChevronRight, Search } from 'lucide-react';

interface FindingsTableProps {
  results?: Record<string, ModuleResult> | null;
}

export const FindingsTable: React.FC<FindingsTableProps> = ({ results }) => {
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState<string>('');
  const [expandedCheck, setExpandedCheck] = useState<string | null>(null);

  if (!results || Object.keys(results).length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-500">
        No module results available yet. Run analysis to view detailed findings.
      </div>
    );
  }

  // Flatten all findings
  const allFindings: Finding[] = [];
  Object.values(results).forEach(mod => {
    if (mod.findings) {
      allFindings.push(...mod.findings);
    }
  });

  const filteredFindings = allFindings.filter(finding => {
    if (filter === 'tampered' && finding.result !== 'tampered') return false;
    if (filter === 'suspicious' && finding.result !== 'suspicious') return false;
    if (filter === 'pass' && finding.result !== 'pass') return false;
    if (filter === 'other' && (finding.result === 'tampered' || finding.result === 'suspicious' || finding.result === 'pass')) return false;

    if (search.trim()) {
      const q = search.toLowerCase();
      const inName = finding.check_name.toLowerCase().includes(q);
      const inMod = finding.module.toLowerCase().includes(q);
      const inExp = finding.explanation.toLowerCase().includes(q);
      if (!inName && !inMod && !inExp) return false;
    }

    return true;
  });

  const getResultBadge = (result: FindingResult) => {
    switch (result) {
      case 'pass':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
            <CheckCircle className="w-3 h-3" /> PASS
          </span>
        );
      case 'suspicious':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
            <AlertTriangle className="w-3 h-3" /> SUSPICIOUS
          </span>
        );
      case 'tampered':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950 text-red-400 border border-red-800">
            <AlertOctagon className="w-3 h-3" /> TAMPERED
          </span>
        );
      case 'inconclusive':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            <HelpCircle className="w-3 h-3" /> INCONCLUSIVE
          </span>
        );
      case 'not_applicable':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-900 text-slate-400 border border-slate-800">
            <MinusCircle className="w-3 h-3" /> NOT APPLICABLE
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      {/* Header and Controls */}
      <div className="p-4 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-200">Forensic Checks Matrix</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
            {filteredFindings.length} of {allFindings.length} checks
          </span>
        </div>

        {/* Filters and Search */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search checks..."
              className="pl-8 pr-3 py-1 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center rounded-lg bg-slate-950 p-0.5 border border-slate-800 text-xs">
            <button
              onClick={() => setFilter('all')}
              className={`px-2.5 py-1 rounded-md transition-colors ${filter === 'all' ? 'bg-slate-800 text-slate-100 font-medium' : 'text-slate-400 hover:text-slate-200'}`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('tampered')}
              className={`px-2.5 py-1 rounded-md transition-colors ${filter === 'tampered' ? 'bg-red-950 text-red-300 font-medium' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Tampered
            </button>
            <button
              onClick={() => setFilter('suspicious')}
              className={`px-2.5 py-1 rounded-md transition-colors ${filter === 'suspicious' ? 'bg-amber-950 text-amber-300 font-medium' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Suspicious
            </button>
            <button
              onClick={() => setFilter('pass')}
              className={`px-2.5 py-1 rounded-md transition-colors ${filter === 'pass' ? 'bg-emerald-950 text-emerald-300 font-medium' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Pass
            </button>
            <button
              onClick={() => setFilter('other')}
              className={`px-2.5 py-1 rounded-md transition-colors ${filter === 'other' ? 'bg-slate-800 text-slate-300 font-medium' : 'text-slate-400 hover:text-slate-200'}`}
            >
              N/A & Inconclusive
            </button>
          </div>
        </div>
      </div>

      {/* Findings Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-950/60 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <th className="py-3 px-4">Check Name</th>
              <th className="py-3 px-4">Module</th>
              <th className="py-3 px-4">Result</th>
              <th className="py-3 px-4">Confidence</th>
              <th className="py-3 px-4">Investigative Explanation</th>
              <th className="py-3 px-4 text-right">Evidence Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-xs">
            {filteredFindings.map((finding) => {
              const rowKey = `${finding.module}:${finding.check_name}`;
              const isExpanded = expandedCheck === rowKey;
              return (
                <React.Fragment key={rowKey}>
                  <tr className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-slate-200">
                      {finding.check_name.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono">
                      {finding.module}
                    </td>
                    <td className="py-3 px-4">
                      {getResultBadge(finding.result)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              finding.confidence > 0.75
                                ? 'bg-cyan-500'
                                : finding.confidence > 0.4
                                ? 'bg-blue-500'
                                : 'bg-slate-600'
                            }`}
                            style={{ width: `${Math.round(finding.confidence * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-slate-400">
                          {Math.round(finding.confidence * 100)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-300 max-w-md">
                      {finding.explanation}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setExpandedCheck(isExpanded ? null : rowKey)}
                        className="inline-flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors font-medium"
                      >
                        {isExpanded ? (
                          <><span>Hide</span><ChevronDown className="w-3.5 h-3.5" /></>
                        ) : (
                          <><span>View JSON</span><ChevronRight className="w-3.5 h-3.5" /></>
                        )}
                      </button>
                    </td>
                  </tr>

                  {/* Expanded Evidence JSON */}
                  {isExpanded && (
                    <tr className="bg-slate-950/80">
                      <td colSpan={6} className="py-3 px-6">
                        <div className="p-3 rounded-lg bg-black/60 border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto">
                          <div className="flex items-center justify-between mb-2 pb-1 border-b border-slate-800 text-slate-400 font-sans">
                            <span>Computed Raw Evidence Payload</span>
                            <span>Check: {finding.check_name}</span>
                          </div>
                          <pre>{JSON.stringify(finding.evidence, null, 2)}</pre>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
