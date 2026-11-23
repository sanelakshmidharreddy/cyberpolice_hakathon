import React from 'react';
import { AlertTriangle, CheckCircle, HelpCircle, XCircle, ShieldAlert, Award } from 'lucide-react';
import { Verdict } from '../types';

interface VerdictBadgeProps {
  verdict: Verdict | null | undefined;
}

export const VerdictBadge: React.FC<VerdictBadgeProps> = ({ verdict }) => {
  if (!verdict) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 text-center text-slate-400">
        <HelpCircle className="w-8 h-8 mx-auto mb-2 text-slate-500 animate-pulse" />
        <p className="text-sm">Awaiting forensic analysis execution...</p>
      </div>
    );
  }

  const { overall, score, top_reasons } = verdict;

  let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
  let badgeIcon = <HelpCircle className="w-6 h-6 text-slate-400" />;
  let scoreColor = 'text-slate-400';
  let title = 'INCONCLUSIVE';

  if (overall === 'AUTHENTIC') {
    badgeColor = 'bg-emerald-950/80 text-emerald-300 border-emerald-500/50 shadow-emerald-950/40';
    badgeIcon = <CheckCircle className="w-6 h-6 text-emerald-400" />;
    scoreColor = 'text-emerald-400';
    title = 'EVIDENCE AUTHENTIC';
  } else if (overall === 'SUSPICIOUS') {
    badgeColor = 'bg-amber-950/80 text-amber-300 border-amber-500/50 shadow-amber-950/40';
    badgeIcon = <AlertTriangle className="w-6 h-6 text-amber-400" />;
    scoreColor = 'text-amber-400';
    title = 'SUSPICIOUS ANOMALIES';
  } else if (overall === 'LIKELY_TAMPERED') {
    badgeColor = 'bg-rose-950/80 text-rose-300 border-rose-500/50 shadow-rose-950/40';
    badgeIcon = <XCircle className="w-6 h-6 text-rose-400" />;
    scoreColor = 'text-rose-400';
    title = 'LIKELY TAMPERED / MANIPULATED';
  }

  return (
    <div className={`rounded-xl border p-5 shadow-lg ${badgeColor} backdrop-blur-sm transition-all`}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Left: Verdict Chip & Title */}
        <div className="flex items-start space-x-3.5">
          <div className="p-2.5 rounded-lg bg-black/40 border border-white/10">
            {badgeIcon}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono font-bold text-lg tracking-wide uppercase">
                {title}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-black/40 font-mono">
                {overall}
              </span>
            </div>
            <p className="text-xs opacity-80 mt-1 max-w-xl">
              Forensic indicator derived from multi-modal algorithmic verification.
            </p>
          </div>
        </div>

        {/* Right: Score Gauge */}
        <div className="flex items-center space-x-4 bg-black/30 px-4 py-2.5 rounded-lg border border-white/5">
          <div className="text-right">
            <span className="text-[10px] uppercase font-mono tracking-wider opacity-70 block">Forensic Risk Score</span>
            <span className="text-xs opacity-60">0 (Authentic) → 100 (Tampered)</span>
          </div>
          <div className="flex items-baseline space-x-1">
            <span className={`text-3xl font-extrabold font-mono ${scoreColor}`}>
              {score.toFixed(1)}
            </span>
            <span className="text-xs opacity-50 font-mono">/100</span>
          </div>
        </div>
      </div>

      {/* Top Reasons Checklist */}
      {top_reasons && top_reasons.length > 0 && (
        <div className="mt-4 pt-3.5 border-t border-white/10">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-300 block mb-2 font-semibold">
            Key Investigative Observations & Explanations:
          </span>
          <ul className="space-y-1.5 text-xs text-slate-200">
            {top_reasons.map((reason, idx) => (
              <li key={idx} className="flex items-start space-x-2 bg-black/20 p-2 rounded border border-white/5">
                <span className="text-cyan-400 font-mono font-bold">#{idx + 1}</span>
                <span className="leading-relaxed">{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Legal Admissibility Disclaimer */}
      <div className="mt-3 pt-2 text-[11px] opacity-70 italic text-slate-300 flex items-center space-x-1.5">
        <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" />
        <span>
          Legal notice: Findings represent computational indicators with statistical confidence and do not substitute a sworn forensic examiner testimony.
        </span>
      </div>
    </div>
  );
};
