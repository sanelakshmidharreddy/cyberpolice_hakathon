import React, { useState } from 'react';
import { createCase, uploadEvidenceFile } from '../api';
import { Case, EvidenceFile } from '../types';
import { X, UploadCloud, Shield, Check, FileCheck, AlertCircle } from 'lucide-react';

interface NewCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCaseCreated: (createdCase: Case) => void;
}

export const NewCaseModal: React.FC<NewCaseModalProps> = ({ isOpen, onClose, onCaseCreated }) => {
  const [caseReference, setCaseReference] = useState('');
  const [investigatorName, setInvestigatorName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseReference.trim() || !investigatorName.trim()) {
      setError('Please provide both Case Reference and Investigator Name.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Create Case
      const newCase = await createCase(investigatorName.trim(), caseReference.trim());

      // 2. Upload initial file if selected
      if (selectedFile) {
        await uploadEvidenceFile(newCase.case_id, selectedFile, (p) => {
          setUploadProgress(p);
        });
      }

      onCaseCreated(newCase);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create case');
    } finally {
      setLoading(false);
    }
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-100">Initialize Forensics Case</h3>
              <p className="text-xs text-slate-400">Creates an immutable chain of custody record</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-950/60 border border-red-800/80 text-red-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Case Reference Number / FIR ID <span className="text-emerald-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. FIR-2026-PAT-0042 / CYBER-PS05-EX-01"
              value={caseReference}
              onChange={(e) => setCaseReference(e.target.value)}
              className="w-full px-3.5 py-2 text-sm bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Lead Forensic Investigator <span className="text-emerald-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Insp. Rajesh Kumar, Cyber Crime Unit"
              value={investigatorName}
              onChange={(e) => setInvestigatorName(e.target.value)}
              className="w-full px-3.5 py-2 text-sm bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Evidence File Uploader Area */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Attach Initial Digital Evidence (Optional)
            </label>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              className="border-2 border-dashed border-slate-700 hover:border-emerald-500/60 rounded-xl p-5 text-center transition-colors bg-slate-950/40 cursor-pointer"
              onClick={() => document.getElementById('case-file-input')?.click()}
            >
              <input
                id="case-file-input"
                type="file"
                className="hidden"
                accept=".jpg,.jpeg,.png,.mp4,.avi,.wav,.mp3"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setSelectedFile(e.target.files[0]);
                  }
                }}
              />
              <UploadCloud className="w-8 h-8 mx-auto text-slate-400 mb-2" />
              {selectedFile ? (
                <div className="flex items-center justify-center gap-2 text-xs font-medium text-emerald-400">
                  <FileCheck className="w-4 h-4" />
                  <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                </div>
              ) : (
                <>
                  <p className="text-xs text-slate-300 font-medium">Click or drag & drop evidence file here</p>
                  <p className="text-[11px] text-slate-500 mt-1">JPEG, PNG, MP4, AVI, WAV, MP3</p>
                </>
              )}
            </div>
          </div>

          {/* Upload Progress Bar */}
          {uploadProgress > 0 && uploadProgress < 100 && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Streaming & computing SHA-256...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full rounded-full transition-all duration-150" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-xs font-medium rounded-lg text-slate-300 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-50 shadow-lg shadow-emerald-950/40"
            >
              {loading ? (
                <span>Registering Case...</span>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  <span>Initialize & Lock Chain of Custody</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
