import React, { useState } from 'react';
import { EvidenceFile } from '../types';
import { getArtifactUrl, getContentUrl } from '../api';
import { Film, AlertTriangle, CheckCircle, Activity, Clock, ZoomIn } from 'lucide-react';

interface VideoForensicViewerProps {
  caseId: string;
  file: EvidenceFile;
}

export const VideoForensicViewer: React.FC<VideoForensicViewerProps> = ({ caseId, file }) => {
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);

  const videoFrames = file.results?.['video_frames'];
  const videoTimestamps = file.results?.['video_timestamps'];

  const motionTimeline = videoFrames?.findings.find(f => f.check_name === 'motion_discontinuity_timeline');
  const frameLoops = videoFrames?.findings.find(f => f.check_name === 'repeated_frame_sequences');
  const opticalFlowCuts = videoFrames?.findings.find(f => f.check_name === 'optical_flow_cuts');
  const ocrCheck = videoTimestamps?.findings.find(f => f.check_name === 'timestamp_ocr_continuity');

  const timelineArtifact = motionTimeline?.artifact_paths[0];

  const cuts = (opticalFlowCuts?.evidence?.cuts as Array<{ frame: number; time_sec: number; delta: number }>) || [];
  const loops = (frameLoops?.evidence?.repeated_runs as Array<{ start_frame: number; end_frame: number; length: number; duration_sec: number }>) || [];

  return (
    <div className="space-y-6">
      {/* Video Preview and Key Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Native Video Player */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
          <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-slate-300">
            <Film className="w-4 h-4 text-emerald-400" />
            <span>Working Copy Video Playback</span>
          </div>
          <div className="relative aspect-video bg-black rounded-lg overflow-hidden flex items-center justify-center">
            <video
              src={getContentUrl(caseId, file.file_id)}
              controls
              className="w-full h-full object-contain"
            />
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
            <span>Original: {file.original_name}</span>
            <span>Size: {(file.size_bytes / (1024 * 1024)).toFixed(2)} MB</span>
          </div>
        </div>

        {/* Forensic Motion & Continuity Overview */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                Continuity & Motion Analysis
              </h3>
              <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {videoFrames ? `${videoFrames.duration_ms} ms` : 'Pending'}
              </span>
            </div>

            <div className="space-y-3">
              {/* Optical Flow Cuts Card */}
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-300 font-medium">Inter-Frame Cut Discontinuities</span>
                  {opticalFlowCuts?.result === 'tampered' ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-red-950 text-red-400 border border-red-800">
                      <AlertTriangle className="w-3.5 h-3.5" /> {cuts.length} Jump Cut(s)
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                      <CheckCircle className="w-3.5 h-3.5" /> Continuous
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {opticalFlowCuts?.explanation || 'Awaiting optical flow frame extraction...'}
                </p>
              </div>

              {/* Loop / Freeze Frame Card */}
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-300 font-medium">Freeze / Loop Frame Sequences</span>
                  {frameLoops?.result === 'tampered' || frameLoops?.result === 'suspicious' ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
                      <AlertTriangle className="w-3.5 h-3.5" /> {loops.length} Freeze Sequence(s)
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                      <CheckCircle className="w-3.5 h-3.5" /> No Looping
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {frameLoops?.explanation || 'Checking hash variations across frame sequence...'}
                </p>
              </div>

              {/* On-screen OCR Clock Card */}
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-300 font-medium flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-cyan-400" /> CCTV Burned-in Clock OCR
                  </span>
                  <span className={`px-2.5 py-0.5 rounded text-xs font-semibold ${
                    ocrCheck?.result === 'pass'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : ocrCheck?.result === 'tampered'
                      ? 'bg-red-950 text-red-400 border border-red-800'
                      : 'bg-slate-800 text-slate-400 border border-slate-700'
                  }`}>
                    {ocrCheck?.result?.toUpperCase() || 'N/A'}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {ocrCheck?.explanation || 'OCR engine scans burned-in video timecodes for timestamps jumps.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Forensic Motion Discontinuity Timeline Chart */}
      {timelineArtifact && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h4 className="text-sm font-semibold text-slate-200">Optical Flow Motion Delta Timeline</h4>
              <p className="text-xs text-slate-400">
                Calculated mean inter-frame pixel differences across timeline with adaptive 3-sigma anomaly threshold.
              </p>
            </div>
            <button
              onClick={() => setSelectedArtifact(getArtifactUrl(caseId, file.file_id, timelineArtifact))}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors border border-slate-700"
            >
              <ZoomIn className="w-3.5 h-3.5" /> Full Size
            </button>
          </div>
          <div className="bg-black/80 rounded-lg p-2 border border-slate-800 overflow-hidden flex items-center justify-center">
            <img
              src={getArtifactUrl(caseId, file.file_id, timelineArtifact)}
              alt="Video Motion Timeline"
              className="max-h-80 w-auto object-contain cursor-pointer hover:opacity-95 transition-opacity"
              onClick={() => setSelectedArtifact(getArtifactUrl(caseId, file.file_id, timelineArtifact))}
            />
          </div>
        </div>
      )}

      {/* Detected Anomaly Details Tables */}
      {(cuts.length > 0 || loops.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {cuts.length > 0 && (
            <div className="bg-slate-900 border border-red-900/50 rounded-xl p-4">
              <h4 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> Detected Frame Cuts ({cuts.length})
              </h4>
              <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                {cuts.map((c, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800 text-xs">
                    <span className="font-mono text-slate-300">Time: {c.time_sec.toFixed(2)}s (Frame #{c.frame})</span>
                    <span className="font-mono text-red-400 font-semibold">Delta: {c.delta.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {loops.length > 0 && (
            <div className="bg-slate-900 border border-amber-900/50 rounded-xl p-4">
              <h4 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> Detected Freeze / Loop Sequences ({loops.length})
              </h4>
              <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                {loops.map((l, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800 text-xs">
                    <span className="font-mono text-slate-300">Frames {l.start_frame} → {l.end_frame}</span>
                    <span className="font-mono text-amber-400 font-semibold">{l.duration_sec.toFixed(2)}s ({l.length} frames)</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Full Screen Modal */}
      {selectedArtifact && (
        <div
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 cursor-pointer"
          onClick={() => setSelectedArtifact(null)}
        >
          <div className="max-w-6xl max-h-[90vh] bg-slate-900 p-2 rounded-xl border border-slate-700">
            <img src={selectedArtifact} alt="Full resolution forensic chart" className="max-h-[85vh] w-auto object-contain" />
          </div>
        </div>
      )}
    </div>
  );
};
