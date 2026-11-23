import React, { useState, useEffect } from 'react';
import { Case, EvidenceFile } from '../types';
import {
  triggerAnalysis,
  getAnalysisStatus,
  uploadEvidenceFile,
  simulateForward,
} from '../api';
import { VerdictBadge } from '../components/VerdictBadge';
import { ImageForensicViewer } from '../components/ImageForensicViewer';
import { VideoForensicViewer } from '../components/VideoForensicViewer';
import { AudioForensicViewer } from '../components/AudioForensicViewer';
import { FindingsTable } from '../components/FindingsTable';
import { ChainOfCustodyPanel } from '../components/ChainOfCustodyPanel';
import {
  FileText,
  Play,
  RotateCw,
  Plus,
  Image as ImageIcon,
  Video,
  Volume2,
  Clock,
  CheckCircle2,
  AlertCircle,
  Download,
  Fingerprint,
  Layers,
  FileCheck,
  Copy,
  Share2,
  FileCode2,
  ShieldCheck,
} from 'lucide-react';

interface DashboardProps {
  currentCase: Case;
  onRefreshCase: () => void;
  onDuplicateCase?: (c: Case) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  currentCase,
  onRefreshCase,
  onDuplicateCase,
}) => {
  const [selectedFileId, setSelectedFileId] = useState<string | null>(
    currentCase.files.length > 0 ? currentCase.files[0].file_id : null
  );
  const [activeTab, setActiveTab] = useState<'viewer' | 'findings' | 'custody'>('viewer');
  const [analyzing, setAnalyzing] = useState(false);
  const [simulatingForward, setSimulatingForward] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadPercent, setUploadPercent] = useState(0);

  // Keep selected file in sync if files change
  useEffect(() => {
    if (!selectedFileId && currentCase.files.length > 0) {
      setSelectedFileId(currentCase.files[0].file_id);
    }
  }, [currentCase.files, selectedFileId]);

  const selectedFile = currentCase.files.find((f) => f.file_id === selectedFileId);

  // Auto-poll status if current selected file is running
  useEffect(() => {
    if (!selectedFile || selectedFile.status !== 'running') return;

    const interval = setInterval(async () => {
      try {
        const stat = await getAnalysisStatus(currentCase.case_id, selectedFile.file_id);
        if (stat.overall_status === 'done' || stat.overall_status === 'failed') {
          onRefreshCase();
        }
      } catch (e) {
        console.error('Polling status error', e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [selectedFile, currentCase.case_id, onRefreshCase]);

  const handleStartAnalysis = async () => {
    if (!selectedFile) return;
    setAnalyzing(true);
    try {
      await triggerAnalysis(currentCase.case_id, selectedFile.file_id);
      onRefreshCase();
    } catch (err: any) {
      alert(`Error starting analysis: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSimulateForward = async () => {
    if (!selectedFile) return;
    setSimulatingForward(true);
    try {
      const fwdFile = await simulateForward(currentCase.case_id, selectedFile.file_id);
      onRefreshCase();
      setSelectedFileId(fwdFile.file_id);
      // Run analysis immediately on the simulated forward file
      await triggerAnalysis(currentCase.case_id, fwdFile.file_id);
      onRefreshCase();
    } catch (err: any) {
      alert(`Messaging forward simulation error: ${err.message}`);
    } finally {
      setSimulatingForward(false);
    }
  };

  const handleDownloadAppendix = async () => {
    try {
      const res = await fetch(`/api/cases/${currentCase.case_id}/appendix.json`);
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const cleanRef = (currentCase.case_reference || currentCase.case_id).replace(/[^a-zA-Z0-9_-]/g, '_');
      a.download = `FORGE_Technical_Appendix_${cleanRef}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(`Could not download appendix: ${err.message}`);
    }
  };

  const handleQuickUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];
    setIsUploading(true);
    setUploadPercent(0);

    try {
      const uploaded = await uploadEvidenceFile(
        currentCase.case_id,
        file,
        false,
        (p: number) => setUploadPercent(p)
      );
      onRefreshCase();
      setSelectedFileId(uploaded.file_id);
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      setUploadPercent(0);
      e.target.value = '';
    }
  };

  const getMediaIcon = (type: string) => {
    switch (type) {
      case 'image':
        return <ImageIcon className="w-4 h-4 text-emerald-400" />;
      case 'video':
        return <Video className="w-4 h-4 text-cyan-400" />;
      case 'audio':
        return <Volume2 className="w-4 h-4 text-indigo-400" />;
      default:
        return <FileCheck className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'done':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'running':
        return <RotateCw className="w-3.5 h-3.5 text-cyan-400 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-3.5 h-3.5 text-red-400" />;
      case 'queued':
      default:
        return <Clock className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Case Header Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-bold text-slate-100">{currentCase.case_reference}</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800">
              Cyber Hackathon 2026 (PS-05)
            </span>
            {currentCase.device_source_type && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                Source: {currentCase.device_source_type} ({currentCase.make_and_model || 'Standard Device'})
              </span>
            )}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-slate-400">
            <span>Investigator: <strong className="text-slate-200">{currentCase.investigator_name}</strong></span>
            <span>Registered: <strong className="text-slate-200">{new Date(currentCase.created_at).toLocaleString()}</strong></span>
            <span>Case ID: <code className="text-slate-300 font-mono">{currentCase.case_id.slice(0, 16)}...</code></span>
            {currentCase.producer_name && (
              <span>Device Custodian: <strong className="text-slate-200">{currentCase.producer_name}</strong> ({currentCase.lawful_control_role || 'Custodian'})</span>
            )}
          </div>
        </div>

        {/* Global Case Actions */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Duplicate Case Details */}
          <button
            onClick={() => onDuplicateCase?.(currentCase)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors shadow-md"
            title="Clone all filled case, custody, and device particulars into a fresh submission form"
          >
            <Copy className="w-3.5 h-3.5 text-emerald-400" />
            <span>Duplicate Case Details</span>
          </button>

          {/* Download Official Forensic PDF Report */}
          <a
            href={`/api/cases/${currentCase.case_id}/report.pdf`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-cyan-950/80 hover:bg-cyan-900 text-cyan-200 border border-cyan-700/80 transition-colors shadow-md"
            title="Download court-ready BSA 2023 Section 63(4)(c) Certificate & Technical Report (ReportLab PDF)"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Forensic PDF Report</span>
          </a>

          {/* Download Technical Appendix JSON */}
          <button
            onClick={handleDownloadAppendix}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors shadow-md"
            title="Download raw technical metrics, EXIF tags, and audit trail as a machine-readable JSON appendix"
          >
            <FileCode2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Technical Appendix (JSON)</span>
          </button>
        </div>
      </div>

      {/* Evidence Files Selector Row */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-400 px-1">
          <span>Evidence Items ({currentCase.files.length})</span>
          {isUploading && <span className="text-emerald-400 animate-pulse">Uploading evidence... {uploadPercent}%</span>}
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
          {currentCase.files.map((file) => {
            const isSelected = file.file_id === selectedFileId;
            return (
              <button
                key={file.file_id}
                onClick={() => setSelectedFileId(file.file_id)}
                className={`flex items-center gap-2.5 px-3.5 py-2 rounded-xl text-xs font-medium transition-all shrink-0 border ${
                  isSelected
                    ? 'bg-slate-800 border-cyan-500/80 text-white shadow-lg shadow-cyan-950/20'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                {getMediaIcon(file.media_type)}
                <span className="max-w-[140px] truncate">{file.original_name}</span>
                {file.is_forward_simulation && (
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-950 text-amber-400 border border-amber-800">
                    FWD
                  </span>
                )}
                <span className="flex items-center gap-1">{getStatusIcon(file.status)}</span>
              </button>
            );
          })}

          {/* Quick Add Evidence Button */}
          <label className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium bg-slate-950 hover:bg-slate-900 text-slate-400 hover:text-slate-200 border border-dashed border-slate-800 hover:border-slate-700 transition-colors cursor-pointer shrink-0">
            <Plus className="w-4 h-4 text-emerald-400" />
            <span>Add Evidence</span>
            <input
              type="file"
              className="hidden"
              accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.mkv,.avi,.wav,.mp3,.m4a,.ogg"
              onChange={handleQuickUpload}
            />
          </label>
        </div>
      </div>

      {/* Main Analysis Workspace */}
      {selectedFile ? (
        <div className="space-y-6">
          {/* Action & Status Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2.5 text-xs text-slate-400">
              <span className="font-semibold text-slate-200">{selectedFile.original_name}</span>
              <span>•</span>
              <span className="uppercase font-mono text-[11px] bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300">
                {selectedFile.media_type}
              </span>
              <span>•</span>
              <span>{(selectedFile.size_bytes / 1024).toFixed(1)} KB</span>
              <span>•</span>
              <span className="font-mono text-slate-400" title={selectedFile.sha256_at_upload}>
                SHA: {selectedFile.sha256_at_upload.slice(0, 16)}...
              </span>
              {selectedFile.auto_purge && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                  Auto-Purged (Privacy Compliant)
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              {/* Simulate Messaging Forward Demo Button (Available for Image/Video) */}
              {(selectedFile.media_type === 'image' || selectedFile.media_type === 'video') && (
                <button
                  onClick={handleSimulateForward}
                  disabled={simulatingForward || analyzing}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-950/50 hover:bg-amber-900/60 text-amber-300 border border-amber-700/70 transition-colors shadow-sm disabled:opacity-50"
                  title="Simulate WhatsApp/messaging re-compression and EXIF stripping to demonstrate why forwarded media fails BSA Section 63 integrity checks"
                >
                  <Share2 className="w-3.5 h-3.5 text-amber-400" />
                  <span>
                    {simulatingForward ? 'Simulating Forward...' : 'Duplicate & Simulate Messaging Forward'}
                  </span>
                </button>
              )}

              {selectedFile.status === 'queued' && (
                <button
                  onClick={handleStartAnalysis}
                  disabled={analyzing}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white transition-colors shadow-lg shadow-cyan-950/40"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span>Run Forensic Pipeline</span>
                </button>
              )}

              {selectedFile.status === 'running' && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyan-950/60 border border-cyan-800/80 text-cyan-300 text-xs font-medium">
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Multi-modal analyzers running...</span>
                </div>
              )}

              {selectedFile.status === 'done' && (
                <button
                  onClick={handleStartAnalysis}
                  disabled={analyzing}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                  <span>Re-analyze</span>
                </button>
              )}
            </div>
          </div>

          {/* Forward Simulation Warning Callout */}
          {selectedFile.is_forward_simulation && (
            <div className="bg-amber-950/40 border border-amber-700/70 rounded-xl p-4 text-xs text-amber-200 space-y-2 shadow-lg">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                <span className="font-bold text-amber-300 text-sm">
                  Simulated Social Messaging Forward (WhatsApp / Telegram Transcoding)
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-900 text-amber-200 border border-amber-700">
                  EXIF STRIPPED • RE-QUANTIZED
                </span>
              </div>
              <p className="text-slate-300 text-xs leading-relaxed">
                This evidence item demonstrates the destructive impact of messaging network forwards on judicial admissibility.
                The server applied a genuine re-compression pass and stripped device metadata. Notice that the cryptographic hash
                differs completely from the source capture, breaking the statutory Chain of Custody required under <strong>Bharatiya Sakshya Adhiniyam (BSA), 2023 Section 63</strong>.
              </p>
              {selectedFile.forward_source_hash && (
                <div className="mt-2 p-2.5 bg-slate-950/70 rounded-lg border border-slate-800 font-mono text-[11px] space-y-1">
                  <div className="text-slate-400">
                    Source Evidence SHA-256: <span className="text-slate-200 font-bold">{selectedFile.forward_source_hash}</span>
                  </div>
                  <div className="text-amber-400">
                    Forwarded Copy SHA-256: <span className="font-bold">{selectedFile.sha256_at_upload}</span> (INTEGRITY FAILED)
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Verdict Banner (If Done) */}
          {selectedFile.verdict && (
            <VerdictBadge verdict={selectedFile.verdict} />
          )}

          {/* Forensic Workspace Tabs */}
          <div className="border-b border-slate-800 flex items-center gap-2">
            <button
              onClick={() => setActiveTab('viewer')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === 'viewer'
                  ? 'border-cyan-500 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Forensic Inspector & Visual Artifacts</span>
            </button>
            <button
              onClick={() => setActiveTab('findings')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === 'findings'
                  ? 'border-cyan-500 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Checks Matrix</span>
            </button>
            <button
              onClick={() => setActiveTab('custody')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === 'custody'
                  ? 'border-cyan-500 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Fingerprint className="w-4 h-4" />
              <span>Chain of Custody & Audit Trail</span>
            </button>
          </div>

          {/* Tab Content Display */}
          <div>
            {activeTab === 'viewer' && (
              <div>
                {selectedFile.media_type === 'image' && (
                  <ImageForensicViewer caseId={currentCase.case_id} file={selectedFile} />
                )}
                {selectedFile.media_type === 'video' && (
                  <VideoForensicViewer caseId={currentCase.case_id} file={selectedFile} />
                )}
                {selectedFile.media_type === 'audio' && (
                  <AudioForensicViewer caseId={currentCase.case_id} file={selectedFile} />
                )}
              </div>
            )}

            {activeTab === 'findings' && (
              <FindingsTable results={selectedFile.results} />
            )}

            {activeTab === 'custody' && (
              <ChainOfCustodyPanel caseId={currentCase.case_id} file={selectedFile} />
            )}
          </div>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
          <FileCheck className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-200">No Evidence Uploaded</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Attach digital evidence (images, CCTV video, or audio recordings) to start forensic authenticity verification.
          </p>
          <label className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer shadow-lg shadow-emerald-950/40">
            <Plus className="w-4 h-4" />
            <span>Upload Evidence</span>
            <input
              type="file"
              className="hidden"
              accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.mkv,.avi,.wav,.mp3,.m4a,.ogg"
              onChange={handleQuickUpload}
            />
          </label>
        </div>
      )}
    </div>
  );
};
export default Dashboard;
