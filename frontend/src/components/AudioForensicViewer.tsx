import React, { useState } from 'react';
import { EvidenceFile } from '../types';
import { getArtifactUrl, getContentUrl } from '../api';
import { Volume2, AlertTriangle, CheckCircle, Radio, Mic, ZoomIn } from 'lucide-react';

interface AudioForensicViewerProps {
  caseId: string;
  file: EvidenceFile;
}

export const AudioForensicViewer: React.FC<AudioForensicViewerProps> = ({ caseId, file }) => {
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);

  const audioTamper = file.results?.['audio_tamper'];
  const audioDeepfake = file.results?.['audio_deepfake'];

  const enfCheck = audioTamper?.findings.find(f => f.check_name === 'enf_phase_continuity');
  const silenceCheck = audioTamper?.findings.find(f => f.check_name === 'digital_silence_runs');
  const deepfakeCheck = audioDeepfake?.findings.find(f => f.check_name === 'acoustic_spectral_flux');

  const spectrogramArtifact = audioTamper?.findings.flatMap(f => f.artifact_paths)[0];

  const silenceRuns = (silenceCheck?.evidence?.runs as Array<{ start_sec: number; end_sec: number; duration_sec: number }>) || [];
  const enfEvidence = enfCheck?.evidence || {};

  return (
    <div className="space-y-6">
      {/* Audio Playback and Key Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Native Audio Player */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-slate-300">
              <Volume2 className="w-4 h-4 text-emerald-400" />
              <span>Evidence Audio Player</span>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col items-center justify-center">
              <audio
                src={getContentUrl(caseId, file.file_id)}
                controls
                className="w-full accent-emerald-500"
              />
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
            <span>Original: {file.original_name}</span>
            <span>MIME: {file.mime}</span>
            <span>{(file.size_bytes / 1024).toFixed(1)} KB</span>
          </div>
        </div>

        {/* Forensic Acoustic Overview */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <Radio className="w-4 h-4 text-cyan-400" />
              Acoustic & ENF Integrity
            </h3>
            <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {audioTamper ? `${audioTamper.duration_ms} ms` : 'Pending'}
            </span>
          </div>

          <div className="space-y-3">
            {/* ENF Phase Continuity Card */}
            <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-300 font-medium flex items-center gap-1.5">
                  50 Hz Grid Hum (ENF) Phase Continuity
                </span>
                {enfCheck?.result === 'tampered' ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-red-950 text-red-400 border border-red-800">
                    <AlertTriangle className="w-3.5 h-3.5" /> Discontinuous
                  </span>
                ) : enfCheck?.result === 'pass' ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                    <CheckCircle className="w-3.5 h-3.5" /> Phase Continuous
                  </span>
                ) : (
                  <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                    {enfCheck?.result?.toUpperCase() || 'N/A'}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {enfCheck?.explanation || 'Extracts 48-52 Hz mains hum to verify background phase stability.'}
              </p>
              {enfEvidence.max_jump !== undefined && (
                <div className="mt-2 text-xs font-mono text-slate-400 flex items-center gap-3">
                  <span>Max Jump: <strong className="text-slate-200">{Number(enfEvidence.max_jump).toFixed(4)} rad</strong></span>
                  <span>Std Dev: <strong className="text-slate-200">{Number(enfEvidence.std_dev || 0).toFixed(6)}</strong></span>
                </div>
              )}
            </div>

            {/* Digital Silence Runs Card */}
            <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-300 font-medium">Digital Zero Silence Runs</span>
                {silenceCheck?.result === 'suspicious' || silenceCheck?.result === 'tampered' ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
                    <AlertTriangle className="w-3.5 h-3.5" /> {silenceRuns.length} Cut(s) Detected
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                    <CheckCircle className="w-3.5 h-3.5" /> Natural Ambient
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {silenceCheck?.explanation || 'Detects unnatural zero-noise slices indicative of edited segments.'}
              </p>
            </div>

            {/* Vocal Tract Deepfake Card */}
            <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-300 font-medium flex items-center gap-1.5">
                  <Mic className="w-3.5 h-3.5 text-indigo-400" /> Synthetic Speech / Deepfake
                </span>
                <span className={`px-2.5 py-0.5 rounded text-xs font-semibold ${
                  deepfakeCheck?.result === 'pass'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    : deepfakeCheck?.result === 'suspicious' || deepfakeCheck?.result === 'tampered'
                    ? 'bg-red-950 text-red-400 border border-red-800'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  {deepfakeCheck?.result?.toUpperCase() || 'INCONCLUSIVE'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {deepfakeCheck?.explanation || 'Spectral flux and biophysical vocal tract anti-spoofing analysis.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Spectrogram & Waveform Artifact */}
      {spectrogramArtifact && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h4 className="text-sm font-semibold text-slate-200">Waveform & Log-Spectrogram Analysis</h4>
              <p className="text-xs text-slate-400">
                Time-frequency energy distribution and amplitude envelope for splice and boundary visualization.
              </p>
            </div>
            <button
              onClick={() => setSelectedArtifact(getArtifactUrl(caseId, file.file_id, spectrogramArtifact))}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors border border-slate-700"
            >
              <ZoomIn className="w-3.5 h-3.5" /> Full Size
            </button>
          </div>
          <div className="bg-black/80 rounded-lg p-2 border border-slate-800 overflow-hidden flex items-center justify-center">
            <img
              src={getArtifactUrl(caseId, file.file_id, spectrogramArtifact)}
              alt="Audio Spectrogram"
              className="max-h-80 w-auto object-contain cursor-pointer hover:opacity-95 transition-opacity"
              onClick={() => setSelectedArtifact(getArtifactUrl(caseId, file.file_id, spectrogramArtifact))}
            />
          </div>
        </div>
      )}

      {/* Detected Silence Details Table */}
      {silenceRuns.length > 0 && (
        <div className="bg-slate-900 border border-amber-900/50 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> Detected Artificial Silence Segments ({silenceRuns.length})
          </h4>
          <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
            {silenceRuns.map((s, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800 text-xs">
                <span className="font-mono text-slate-300">From {s.start_sec.toFixed(3)}s to {s.end_sec.toFixed(3)}s</span>
                <span className="font-mono text-amber-400 font-semibold">Duration: {(s.duration_sec * 1000).toFixed(0)} ms</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Full Size Modal */}
      {selectedArtifact && (
        <div
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 cursor-pointer"
          onClick={() => setSelectedArtifact(null)}
        >
          <div className="max-w-6xl max-h-[90vh] bg-slate-900 p-2 rounded-xl border border-slate-700">
            <img src={selectedArtifact} alt="Full resolution spectrogram" className="max-h-[85vh] w-auto object-contain" />
          </div>
        </div>
      )}
    </div>
  );
};
