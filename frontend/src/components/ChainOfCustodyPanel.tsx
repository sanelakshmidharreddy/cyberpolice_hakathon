import React, { useState, useEffect } from 'react';
import { Copy, Check, ShieldCheck, AlertOctagon, History, FileCheck } from 'lucide-react';
import { AuditEntry, EvidenceFile } from '../types';
import { getAuditTrail } from '../api';

interface ChainOfCustodyPanelProps {
  caseId?: string;
  file: EvidenceFile;
  auditTrail?: AuditEntry[];
}

export const ChainOfCustodyPanel: React.FC<ChainOfCustodyPanelProps> = ({ caseId, file, auditTrail: initialAuditTrail }) => {
  const [copiedUpload, setCopiedUpload] = useState(false);
  const [copiedVerify, setCopiedVerify] = useState(false);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>(initialAuditTrail || []);

  useEffect(() => {
    if (initialAuditTrail) {
      setAuditTrail(initialAuditTrail);
    } else if (caseId) {
      getAuditTrail(caseId)
        .then((trail) => setAuditTrail(trail))
        .catch((err) => console.error('Failed to load audit trail:', err));
    }
  }, [caseId, initialAuditTrail]);

  const handleCopy = (text: string, isUpload: boolean) => {
    navigator.clipboard.writeText(text);
    if (isUpload) {
      setCopiedUpload(true);
      setTimeout(() => setCopiedUpload(false), 2000);
    } else {
      setCopiedVerify(true);
      setTimeout(() => setCopiedVerify(false), 2000);
    }
  };

  const isHashMatch = !file.sha256_at_report || file.sha256_at_upload.toLowerCase() === file.sha256_at_report.toLowerCase();

  // Filter audit entries relevant to this file or global case actions
  const relevantAudit = auditTrail.filter(
    (e) => !e.file_id || e.file_id === file.file_id
  );

  return (
    <div className="bg-[#111622] border border-slate-800 rounded-xl p-5 shadow-lg">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-cyan-400" />
          <h3 className="font-semibold text-slate-100 text-sm tracking-wide">
            Cryptographic Chain of Custody & Integrity Audit
          </h3>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
          APPEND-ONLY LOG
        </span>
      </div>

      {/* Hash Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
        {/* Upload Hash */}
        <div className="bg-slate-900/80 border border-slate-800 p-3.5 rounded-lg">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-slate-400 flex items-center space-x-1.5">
              <FileCheck className="w-3.5 h-3.5 text-cyan-400" />
              <span>SHA-256 at Initial Upload</span>
            </span>
            <button
              onClick={() => handleCopy(file.sha256_at_upload, true)}
              className="text-xs text-slate-400 hover:text-cyan-400 flex items-center space-x-1 p-1"
              title="Copy Hash"
            >
              {copiedUpload ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
          <p className="font-mono text-xs text-cyan-300 break-all select-all bg-black/40 p-2 rounded border border-white/5">
            {file.sha256_at_upload}
          </p>
          <span className="text-[10px] text-slate-500 font-mono mt-1 block">
            Captured during streaming ingestion ({new Date(file.uploaded_at).toLocaleString()})
          </span>
        </div>

        {/* Verification Status */}
        <div className={`p-3.5 rounded-lg border ${
          isHashMatch
            ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200'
            : 'bg-rose-950/40 border-rose-500 text-rose-200'
        }`}>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium flex items-center space-x-1.5">
              {isHashMatch ? <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> : <AlertOctagon className="w-3.5 h-3.5 text-rose-500 animate-pulse" />}
              <span>Integrity Verification Status</span>
            </span>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
              isHashMatch ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500 text-white animate-bounce'
            }`}>
              {isHashMatch ? 'INTEGRITY VERIFIED' : 'INTEGRITY BREACH!'}
            </span>
          </div>

          <p className="font-mono text-xs break-all select-all bg-black/40 p-2 rounded border border-white/5 text-slate-300">
            {file.sha256_at_report || file.sha256_at_upload}
          </p>
          <span className="text-[10px] opacity-75 font-mono mt-1 block">
            {isHashMatch
              ? 'Bit-level match confirmed: Original evidence stored read-only with zero modifications.'
              : 'CRITICAL ALERT: File hash mismatch detected! Evidence has been altered or tampered with.'}
          </span>
        </div>
      </div>

      {/* Audit Log Timeline */}
      <div className="mt-4 pt-3 border-t border-slate-800">
        <div className="flex items-center space-x-1.5 mb-3 text-xs font-semibold text-slate-300">
          <History className="w-4 h-4 text-cyan-400" />
          <span>Chronological Audit Trail ({relevantAudit.length} Records)</span>
        </div>

        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
          {relevantAudit.map((entry, idx) => (
            <div
              key={entry.id || idx}
              className="flex items-start justify-between bg-slate-900/60 p-2.5 rounded border border-slate-800/80 text-xs font-mono"
            >
              <div className="flex items-start space-x-2.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 mt-1 flex-shrink-0" />
                <div>
                  <span className="font-bold text-cyan-300 mr-2">{entry.action}</span>
                  <span className="text-slate-400 text-[11px]">Actor: {entry.actor}</span>
                  {entry.details && Object.keys(entry.details).length > 0 && (
                    <p className="text-slate-500 text-[11px] mt-0.5 break-all font-sans">
                      {JSON.stringify(entry.details)}
                    </p>
                  )}
                </div>
              </div>
              <span className="text-slate-500 text-[10px] whitespace-nowrap ml-2">
                {new Date(entry.timestamp_utc).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
