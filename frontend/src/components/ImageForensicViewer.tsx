import React, { useState } from 'react';
import { Sliders, MapPin, Eye, Info, Layers } from 'lucide-react';
import { EvidenceFile, ModuleResult } from '../types';
import { getArtifactUrl } from '../api';

interface ImageForensicViewerProps {
  caseId: string;
  file: EvidenceFile;
  results?: Record<string, ModuleResult> | null;
}

export const ImageForensicViewer: React.FC<ImageForensicViewerProps> = ({
  caseId,
  file,
  results,
}) => {
  const [sliderPosition, setSliderPosition] = useState(50);
  const [activeTab, setActiveTab] = useState<'ela' | 'copymove' | 'metadata'>('ela');

  const activeResults = results !== undefined ? results : file.results;
  const metaModule = activeResults?.image_metadata;
  const elaModule = activeResults?.image_ela;
  const spliceModule = activeResults?.image_splicing;

  // Extract artifact paths
  const elaArtifact = elaModule?.findings.find((f) => f.artifact_paths?.length > 0)?.artifact_paths[0];
  const copymoveArtifact = spliceModule?.findings.find((f) => f.check_name === 'copy_move_forgery' && f.artifact_paths?.length > 0)?.artifact_paths[0];
  const noiseArtifact = spliceModule?.findings.find((f) => f.check_name === 'noise_inconsistency' && f.artifact_paths?.length > 0)?.artifact_paths[0];

  // Extract GPS if available
  const gpsFinding = metaModule?.findings.find((f) => f.check_name === 'gps_validity');
  const lat = gpsFinding?.evidence?.latitude;
  const lon = gpsFinding?.evidence?.longitude;
  const osmUrl = gpsFinding?.evidence?.osm_url;

  return (
    <div className="bg-[#111622] border border-slate-800 rounded-xl p-5 shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
        <div className="flex items-center space-x-2">
          <Layers className="w-5 h-5 text-cyan-400" />
          <h3 className="font-semibold text-slate-100 text-sm tracking-wide">
            Image Forensic Analysis Artifacts
          </h3>
        </div>

        {/* Sub-tab Switcher */}
        <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setActiveTab('ela')}
            className={`px-3 py-1 rounded-md transition-all ${
              activeTab === 'ela' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ELA Heatmap
          </button>
          <button
            onClick={() => setActiveTab('copymove')}
            className={`px-3 py-1 rounded-md transition-all ${
              activeTab === 'copymove' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Copy-Move / Noise
          </button>
          <button
            onClick={() => setActiveTab('metadata')}
            className={`px-3 py-1 rounded-md transition-all ${
              activeTab === 'metadata' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Metadata & GPS
          </button>
        </div>
      </div>

      {/* 1. Interactive ELA Heatmap Slider */}
      {activeTab === 'ela' && (
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            Error Level Analysis (ELA) identifies differences in JPEG compression levels. Spliced or edited regions
            retain higher error levels (glowing hot colors) than the natural camera background.
          </p>

          {elaArtifact ? (
            <div className="flex flex-col items-center">
              <div className="relative w-full max-w-xl h-80 rounded-lg overflow-hidden border border-slate-700 select-none bg-black">
                {/* Heatmap Layer */}
                <img
                  src={getArtifactUrl(caseId, file.file_id, elaArtifact)}
                  alt="ELA Heatmap"
                  className="absolute inset-0 w-full h-full object-contain"
                />

                {/* Overlay Split Bar */}
                <div
                  className="absolute top-0 bottom-0 border-r-2 border-cyan-400 shadow-[0_0_10px_rgba(0,242,254,0.6)]"
                  style={{ left: `${sliderPosition}%` }}
                >
                  <div className="absolute top-1/2 -translate-y-1/2 -left-3.5 bg-cyan-400 text-black p-1 rounded-full shadow-md cursor-ew-resize">
                    <Sliders className="w-4 h-4" />
                  </div>
                </div>

                <div className="absolute top-2 left-2 bg-black/60 px-2 py-0.5 rounded text-[10px] font-mono text-cyan-300">
                  Heatmap Overlay ({sliderPosition}%)
                </div>
              </div>

              {/* Slider Controller */}
              <div className="w-full max-w-xl mt-3 flex items-center space-x-3">
                <span className="text-[11px] text-slate-400">Split Level:</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={sliderPosition}
                  onChange={(e) => setSliderPosition(Number(e.target.value))}
                  className="w-full accent-cyan-400 cursor-pointer"
                />
                <span className="text-[11px] font-mono text-cyan-300 w-8">{sliderPosition}%</span>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center bg-slate-900/50 rounded-lg text-slate-500 text-xs">
              ELA heatmap not applicable for lossless or non-JPEG inputs.
            </div>
          )}
        </div>
      )}

      {/* 2. Copy-Move & Noise Variance Tab */}
      {activeTab === 'copymove' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Copy-move overlay */}
          <div className="bg-slate-900/60 p-3.5 rounded-lg border border-slate-800">
            <h4 className="text-xs font-semibold text-slate-200 mb-2 flex items-center space-x-1.5">
              <Eye className="w-3.5 h-3.5 text-cyan-400" />
              <span>Copy-Move Keypoint Match Lines</span>
            </h4>
            {copymoveArtifact ? (
              <img
                src={getArtifactUrl(caseId, file.file_id, copymoveArtifact)}
                alt="Copy-Move Overlay"
                className="w-full h-56 object-contain rounded border border-slate-800 bg-black"
              />
            ) : (
              <div className="h-56 flex items-center justify-center text-xs text-slate-500 bg-black/40 rounded border border-slate-800">
                No clone-stamp or duplicated keypoints detected.
              </div>
            )}
            <p className="text-[11px] text-slate-400 mt-2">
              Yellow vectors link cloned donor and recipient clusters verified via RANSAC.
            </p>
          </div>

          {/* Noise variance map */}
          <div className="bg-slate-900/60 p-3.5 rounded-lg border border-slate-800">
            <h4 className="text-xs font-semibold text-slate-200 mb-2 flex items-center space-x-1.5">
              <Info className="w-3.5 h-3.5 text-amber-400" />
              <span>32x32 Block Noise Variance Map</span>
            </h4>
            {noiseArtifact ? (
              <img
                src={getArtifactUrl(caseId, file.file_id, noiseArtifact)}
                alt="Noise Variance Map"
                className="w-full h-56 object-contain rounded border border-slate-800 bg-black"
              />
            ) : (
              <div className="h-56 flex items-center justify-center text-xs text-slate-500 bg-black/40 rounded border border-slate-800">
                Noise variance map not available.
              </div>
            )}
            <p className="text-[11px] text-slate-400 mt-2">
              Red bounding boxes indicate blocks whose high-pass sensor noise deviates by &gt;3.5 IQR.
            </p>
          </div>
        </div>
      )}

      {/* 3. Metadata & GPS Tab */}
      {activeTab === 'metadata' && (
        <div className="space-y-4">
          {lat !== undefined && lon !== undefined && (
            <div className="p-3 bg-cyan-950/30 border border-cyan-800/50 rounded-lg flex items-center justify-between">
              <div className="flex items-center space-x-2 text-cyan-300 text-xs">
                <MapPin className="w-4 h-4 text-cyan-400" />
                <span>Geotag Coordinates: {lat.toFixed(6)}, {lon.toFixed(6)}</span>
              </div>
              {osmUrl && (
                <a
                  href={osmUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="px-2.5 py-1 rounded bg-cyan-500 text-black font-semibold text-xs hover:bg-cyan-400 transition-all"
                >
                  View OpenStreetMap
                </a>
              )}
            </div>
          )}

          {/* Metadata Findings Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-mono text-[11px] border-b border-slate-800">
                <tr>
                  <th className="p-2.5">Forensic Check</th>
                  <th className="p-2.5">Result</th>
                  <th className="p-2.5">Confidence</th>
                  <th className="p-2.5">Technical Explanation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {metaModule?.findings.map((f, i) => (
                  <tr key={i} className="hover:bg-slate-800/20">
                    <td className="p-2.5 font-mono text-slate-300">{f.check_name}</td>
                    <td className="p-2.5">
                      <span className={`px-2 py-0.5 rounded font-mono text-[10px] uppercase font-bold ${
                        f.result === 'pass'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : f.result === 'tampered'
                          ? 'bg-rose-500/20 text-rose-300'
                          : f.result === 'suspicious'
                          ? 'bg-amber-500/20 text-amber-300'
                          : 'bg-slate-800 text-slate-400'
                      }`}>
                        {f.result}
                      </span>
                    </td>
                    <td className="p-2.5 font-mono text-cyan-400">{(f.confidence * 100).toFixed(0)}%</td>
                    <td className="p-2.5 text-slate-300 leading-relaxed">{f.explanation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
