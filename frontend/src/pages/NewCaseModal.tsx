import React, { useState, useEffect } from 'react';
import { createCase, uploadEvidenceFile, attachSample } from '../api';
import { Case } from '../types';
import {
  X,
  UploadCloud,
  Shield,
  FileCheck,
  AlertCircle,
  Copy,
  Sparkles,
  CheckCircle2,
  Trash2,
  Lock,
  Layers,
  FileText,
} from 'lucide-react';

interface NewCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCaseCreated: (createdCase: Case) => void;
  initialCase?: Case | null;
}

export const NewCaseModal: React.FC<NewCaseModalProps> = ({
  isOpen,
  onClose,
  onCaseCreated,
  initialCase,
}) => {
  // Case & Request
  const [caseId, setCaseId] = useState('');
  const [caseReference, setCaseReference] = useState('');
  const [investigatorName, setInvestigatorName] = useState('');
  const [offenseType, setOffenseType] = useState('Suspected Digital Evidence Tampering');
  const [requestorName, setRequestorName] = useState('');
  const [authorityBasis, setAuthorityBasis] = useState('Station Diary Entry / Seizure Memo');
  const [examinationScope, setExaminationScope] = useState('Verification of authenticity, metadata integrity & temporal continuity');

  // BSA Part A (Party & Device)
  const [producerName, setProducerName] = useState('');
  const [parentageAddress, setParentageAddress] = useState('');
  const [deviceSourceType, setDeviceSourceType] = useState('Mobile');
  const [makeAndModel, setMakeAndModel] = useState('');
  const [color, setColor] = useState('Black');
  const [serialOrImei, setSerialOrImei] = useState('');
  const [lawfulControlRole, setLawfulControlRole] = useState('Owned');

  // Custody & Seizure
  const [seizedAtIst, setSeizedAtIst] = useState('');
  const [seizureLocation, setSeizureLocation] = useState('');
  const [collectionMethod, setCollectionMethod] = useState('Direct Cable Logical Copy');

  // Evidence Input Mode: 'custom' or 'preset_sample'
  const [evidenceMode, setEvidenceMode] = useState<'custom' | 'sample'>('sample');
  const [selectedSampleFile, setSelectedSampleFile] = useState<string>('demo_tampered_splice.jpg');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [autoPurge, setAutoPurge] = useState(false);

  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Initialize or handle pre-filled duplication
  useEffect(() => {
    if (initialCase) {
      setCaseId(`${initialCase.case_id}-DUP`);
      setCaseReference(`${initialCase.case_reference}-COPY`);
      setInvestigatorName(initialCase.investigator_name);
      setOffenseType(initialCase.offense_type || 'Suspected Digital Evidence Tampering');
      setRequestorName(initialCase.requestor_name || initialCase.investigator_name);
      setAuthorityBasis(initialCase.authority_basis || 'Station Diary Entry / Seizure Memo');
      setExaminationScope(initialCase.examination_scope || 'Verification of authenticity, metadata integrity & temporal continuity');

      setProducerName(initialCase.producer_name || '');
      setParentageAddress(initialCase.parentage_and_address || '');
      setDeviceSourceType(initialCase.device_source_type || 'Mobile');
      setMakeAndModel(initialCase.make_and_model || '');
      setColor(initialCase.color || 'Black');
      setSerialOrImei(initialCase.serial_or_imei || '');
      setLawfulControlRole(initialCase.lawful_control_role || 'Owned');

      setSeizedAtIst(initialCase.seized_at_ist || '');
      setSeizureLocation(initialCase.seizure_location || '');
      setCollectionMethod(initialCase.collection_method || 'Direct Cable Logical Copy');

      setEvidenceMode('custom');
      setSelectedFile(null);
      setAutoPurge(true);
    } else {
      loadPresetA();
    }
  }, [initialCase, isOpen]);

  const loadPresetA = () => {
    setCaseId('DEMO-CYB-2026-0418');
    setCaseReference('FIR-2026-PAT-0418');
    setInvestigatorName('Inspector Rajeshwar Verma, Cyber PS (Demo)');
    setOffenseType('Suspected Fabricated Media / Extortion Inquiry');
    setRequestorName('Inspector Rajeshwar Verma, Cyber PS (Demo)');
    setAuthorityBasis('Station Diary Entry / Seizure Memo (Demo)');
    setExaminationScope('Check continuity, on-screen clock, and metadata anomalies');

    setProducerName('Mahesh Kumar Sinha');
    setParentageAddress('S/o Devendra Sinha, Boring Road, Patna');
    setDeviceSourceType('DVR');
    setMakeAndModel('Hikvision 8-Channel DVR (Sample Profile)');
    setColor('Black');
    setSerialOrImei('SN: DEMO-DVR-988124');
    setLawfulControlRole('Maintained & Operated');

    setSeizedAtIst('18/11/2026 14:35 IST');
    setSeizureLocation('Security Cabin, Commercial Complex (Demo)');
    setCollectionMethod('Direct USB Export (Non-Forwarded)');

    setEvidenceMode('sample');
    setSelectedSampleFile('demo_tampered_splice.jpg');
    setSelectedFile(null);
    setAutoPurge(false);
  };

  const loadPresetB = () => {
    setCaseId('DEMO-CYB-2026-0419');
    setCaseReference('FIR-2026-PAT-0419');
    setInvestigatorName('SI Ananya Deshmukh, Cyber Cell (Demo)');
    setOffenseType('Control Authenticity Verification');
    setRequestorName('SI Ananya Deshmukh, Cyber Cell (Demo)');
    setAuthorityBasis('Written Consent of Device Owner (Demo)');
    setExaminationScope('Baseline integrity & hash verification');

    setProducerName('Priya Nair');
    setParentageAddress('D/o Raghavan Nair, Kankarbagh, Patna');
    setDeviceSourceType('Mobile');
    setMakeAndModel('Samsung Galaxy S24 (Sample Profile)');
    setColor('Gray');
    setSerialOrImei('IMEI: 350000000000001 (Demo)');
    setLawfulControlRole('Owned & Operated');

    setSeizedAtIst('20/11/2026 11:10 IST');
    setSeizureLocation('Complainant Residence (Demo)');
    setCollectionMethod('Direct Cable Logical Copy');

    setEvidenceMode('sample');
    setSelectedSampleFile('demo_authentic_scene.jpg');
    setSelectedFile(null);
    setAutoPurge(false);
  };

  const resetBlankCustom = () => {
    setCaseId(`CASE-${Date.now().toString().slice(-6)}`);
    setCaseReference('');
    setInvestigatorName('');
    setOffenseType('Suspected Digital Evidence Tampering');
    setRequestorName('');
    setAuthorityBasis('Station Diary Entry / Seizure Memo');
    setExaminationScope('Verification of authenticity, metadata integrity & temporal continuity');

    setProducerName('');
    setParentageAddress('');
    setDeviceSourceType('Mobile');
    setMakeAndModel('');
    setColor('Black');
    setSerialOrImei('');
    setLawfulControlRole('Owned');

    setSeizedAtIst(new Date().toLocaleDateString('en-GB') + ' 12:00 IST');
    setSeizureLocation('Patna, Bihar');
    setCollectionMethod('Direct Cable Logical Copy');

    setEvidenceMode('custom');
    setSelectedFile(null);
    setAutoPurge(true);
  };

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
      // 1. Create Case in backend with BSA 2023 particulars
      const newCase = await createCase({
        case_id: caseId.trim() || undefined,
        case_reference: caseReference.trim(),
        investigator_name: investigatorName.trim(),
        offense_type: offenseType.trim(),
        requestor_name: requestorName.trim(),
        authority_basis: authorityBasis.trim(),
        examination_scope: examinationScope.trim(),
        producer_name: producerName.trim(),
        parentage_and_address: parentageAddress.trim(),
        device_source_type: deviceSourceType,
        make_and_model: makeAndModel.trim(),
        color: color.trim(),
        serial_or_imei: serialOrImei.trim(),
        lawful_control_role: lawfulControlRole,
        seized_at_ist: seizedAtIst.trim(),
        seizure_location: seizureLocation.trim(),
        collection_method: collectionMethod.trim(),
      });

      // 2. Attach Evidence
      if (evidenceMode === 'sample' && selectedSampleFile) {
        await attachSample(newCase.case_id, selectedSampleFile);
      } else if (evidenceMode === 'custom' && selectedFile) {
        await uploadEvidenceFile(newCase.case_id, selectedFile, autoPurge, (p) => {
          setUploadProgress(p);
        });
      }

      onCaseCreated(newCase);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to initialize case');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 w-full max-w-3xl rounded-2xl shadow-2xl overflow-hidden my-6 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/70">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <span>Digital Evidence Intake & BSA Section 63 Registration</span>
                {initialCase && (
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-700 font-normal">
                    Duplicated from {initialCase.case_reference}
                  </span>
                )}
              </h3>
              <p className="text-xs text-slate-400">
                Bharatiya Sakshya Adhiniyam, 2023 Sec 63(4)(c) Certificate & Chain of Custody Intake
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Demo Preset Selector Bar */}
        <div className="bg-slate-950/90 border-b border-slate-800 p-3 sm:px-6 flex flex-wrap items-center justify-between gap-2.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span>Load Demo Presets:</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={loadPresetA}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                caseId === 'DEMO-CYB-2026-0418'
                  ? 'bg-red-950/80 text-red-200 border-red-700 shadow-sm'
                  : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-600'
              }`}
            >
              Preset A (Tampered DVR)
            </button>
            <button
              type="button"
              onClick={loadPresetB}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                caseId === 'DEMO-CYB-2026-0419'
                  ? 'bg-emerald-950/80 text-emerald-200 border-emerald-700 shadow-sm'
                  : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-600'
              }`}
            >
              Preset B (Authentic Control)
            </button>
            <button
              type="button"
              onClick={resetBlankCustom}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200 hover:border-slate-700 transition-all"
            >
              Custom Intake
            </button>
          </div>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-4 sm:p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {error && (
            <div className="p-3.5 rounded-xl bg-red-950/70 border border-red-800 text-red-300 text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Section 1: Case & Request Details */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 pb-1 border-b border-slate-800">
              <FileText className="w-4 h-4 text-cyan-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                1. Case & Official Request Details
              </h4>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Case ID (Tracking ID)
                </label>
                <input
                  type="text"
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                  placeholder="e.g. DEMO-CYB-2026-0418"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Case Reference / FIR No. <span className="text-cyan-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={caseReference}
                  onChange={(e) => setCaseReference(e.target.value)}
                  placeholder="e.g. FIR-2026-PAT-0418"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Lead Investigator / Examiner <span className="text-cyan-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={investigatorName}
                  onChange={(e) => setInvestigatorName(e.target.value)}
                  placeholder="Full name & Rank (e.g. Inspector Rajeshwar Verma, Cyber PS)"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Offense Type / Inquiry Matter
                </label>
                <input
                  type="text"
                  value={offenseType}
                  onChange={(e) => setOffenseType(e.target.value)}
                  placeholder="e.g. Suspected Fabricated Media / Extortion Inquiry"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Authority Basis (Seizure / Consent)
                </label>
                <input
                  type="text"
                  value={authorityBasis}
                  onChange={(e) => setAuthorityBasis(e.target.value)}
                  placeholder="e.g. Station Diary Entry / Seizure Memo"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Examination Scope
                </label>
                <input
                  type="text"
                  value={examinationScope}
                  onChange={(e) => setExaminationScope(e.target.value)}
                  placeholder="e.g. Check continuity, on-screen clock, and metadata anomalies"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>

          {/* Section 2: BSA Section 63 Part A (Party & Device Particulars) */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 pb-1 border-b border-slate-800">
              <Layers className="w-4 h-4 text-emerald-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                2. BSA 2023 Sec 63 Part A (Party & Source Device Particulars)
              </h4>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Producer / Custodian Full Name
                </label>
                <input
                  type="text"
                  value={producerName}
                  onChange={(e) => setProducerName(e.target.value)}
                  placeholder="Full name as per Aadhaar (no initials, e.g. Mahesh Kumar Sinha)"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500"
                />
                <span className="text-[10px] text-slate-500">Statutory: Full name required without initials</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Parentage & Address
                </label>
                <input
                  type="text"
                  value={parentageAddress}
                  onChange={(e) => setParentageAddress(e.target.value)}
                  placeholder="e.g. S/o Devendra Sinha, Boring Road, Patna"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Device Source Type
                </label>
                <select
                  value={deviceSourceType}
                  onChange={(e) => setDeviceSourceType(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-emerald-500"
                >
                  <option value="Computer / Storage Media">Computer / Storage Media</option>
                  <option value="DVR">DVR (Digital Video Recorder)</option>
                  <option value="Mobile">Mobile Phone / Smartphone</option>
                  <option value="Flash Drive">Flash Drive / Memory Card</option>
                  <option value="CD/DVD">CD / DVD Optical Media</option>
                  <option value="Server">Server / Data Center</option>
                  <option value="Cloud">Cloud Storage / Hosted Service</option>
                  <option value="Other">Other Electronic Device</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Device Make & Model
                </label>
                <input
                  type="text"
                  value={makeAndModel}
                  onChange={(e) => setMakeAndModel(e.target.value)}
                  placeholder="e.g. Hikvision 8-Channel DVR / Samsung Galaxy S24"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Device Color & Serial / IMEI / MAC
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <input
                    type="text"
                    value={color}
                    onChange={(e) => setColor(e.target.value)}
                    placeholder="Color (Black)"
                    className="col-span-1 px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-emerald-500"
                  />
                  <input
                    type="text"
                    value={serialOrImei}
                    onChange={(e) => setSerialOrImei(e.target.value)}
                    placeholder="SN: DEMO-DVR-988124 / IMEI"
                    className="col-span-2 px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Lawful Control Role
                </label>
                <select
                  value={lawfulControlRole}
                  onChange={(e) => setLawfulControlRole(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-emerald-500"
                >
                  <option value="Owned">Owned</option>
                  <option value="Maintained">Maintained</option>
                  <option value="Managed">Managed</option>
                  <option value="Operated">Operated</option>
                  <option value="Maintained & Operated">Maintained & Operated</option>
                  <option value="Owned & Operated">Owned & Operated</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Acquisition Time (IST)
                </label>
                <input
                  type="text"
                  value={seizedAtIst}
                  onChange={(e) => setSeizedAtIst(e.target.value)}
                  placeholder="Format: DD/MM/YYYY HH:MM IST (e.g. 18/11/2026 14:35 IST)"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Collection Method & Location
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={collectionMethod}
                    onChange={(e) => setCollectionMethod(e.target.value)}
                    placeholder="e.g. Direct USB Export"
                    className="px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-emerald-500"
                  />
                  <input
                    type="text"
                    value={seizureLocation}
                    onChange={(e) => setSeizureLocation(e.target.value)}
                    placeholder="e.g. Security Cabin, Patna"
                    className="px-3 py-2 text-xs bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: Evidence Media Attachment */}
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-1 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-4 h-4 text-indigo-400" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  3. Evidence Media Attachment
                </h4>
              </div>
              {/* Toggle custom vs sample */}
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                <button
                  type="button"
                  onClick={() => setEvidenceMode('sample')}
                  className={`px-2.5 py-1 rounded-md transition-all ${
                    evidenceMode === 'sample' ? 'bg-cyan-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Demo Sample Fixtures
                </button>
                <button
                  type="button"
                  onClick={() => setEvidenceMode('custom')}
                  className={`px-2.5 py-1 rounded-md transition-all ${
                    evidenceMode === 'custom' ? 'bg-cyan-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Upload Custom File
                </button>
              </div>
            </div>

            {evidenceMode === 'sample' ? (
              <div className="space-y-2 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <p className="text-xs text-slate-400">
                  Select a real authentic or tampered sample fixture from <code className="text-cyan-400 font-mono">samples/</code>. It executes through the exact same forensic pipeline:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
                  <label
                    onClick={() => setSelectedSampleFile('demo_tampered_splice.jpg')}
                    className={`cursor-pointer p-3 rounded-xl border flex flex-col justify-between transition-all ${
                      selectedSampleFile === 'demo_tampered_splice.jpg'
                        ? 'border-red-500 bg-red-950/30 text-red-200 shadow-md'
                        : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-bold">Tampered Image (Splice)</div>
                    <div className="text-[11px] text-slate-400 mt-1">demo_tampered_splice.jpg</div>
                    <span className="text-[10px] mt-2 px-1.5 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 w-fit">Tampered</span>
                  </label>

                  <label
                    onClick={() => setSelectedSampleFile('demo_tampered_cctv.mp4')}
                    className={`cursor-pointer p-3 rounded-xl border flex flex-col justify-between transition-all ${
                      selectedSampleFile === 'demo_tampered_cctv.mp4'
                        ? 'border-red-500 bg-red-950/30 text-red-200 shadow-md'
                        : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-bold">Tampered CCTV Video</div>
                    <div className="text-[11px] text-slate-400 mt-1">demo_tampered_cctv.mp4</div>
                    <span className="text-[10px] mt-2 px-1.5 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 w-fit">2s Cut Gap</span>
                  </label>

                  <label
                    onClick={() => setSelectedSampleFile('demo_authentic_scene.jpg')}
                    className={`cursor-pointer p-3 rounded-xl border flex flex-col justify-between transition-all ${
                      selectedSampleFile === 'demo_authentic_scene.jpg'
                        ? 'border-emerald-500 bg-emerald-950/30 text-emerald-200 shadow-md'
                        : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-bold">Authentic Image (Nikon)</div>
                    <div className="text-[11px] text-slate-400 mt-1">demo_authentic_scene.jpg</div>
                    <span className="text-[10px] mt-2 px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 w-fit">Authentic</span>
                  </label>

                  <label
                    onClick={() => setSelectedSampleFile('demo_tampered_splice.wav')}
                    className={`cursor-pointer p-3 rounded-xl border flex flex-col justify-between transition-all ${
                      selectedSampleFile === 'demo_tampered_splice.wav'
                        ? 'border-red-500 bg-red-950/30 text-red-200 shadow-md'
                        : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-bold">Tampered Audio (ENF Cut)</div>
                    <div className="text-[11px] text-slate-400 mt-1">demo_tampered_splice.wav</div>
                    <span className="text-[10px] mt-2 px-1.5 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 w-fit">Phase Jump</span>
                  </label>

                  <label
                    onClick={() => setSelectedSampleFile('demo_authentic_voice.wav')}
                    className={`cursor-pointer p-3 rounded-xl border flex flex-col justify-between transition-all ${
                      selectedSampleFile === 'demo_authentic_voice.wav'
                        ? 'border-emerald-500 bg-emerald-950/30 text-emerald-200 shadow-md'
                        : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-bold">Authentic Audio (50Hz ENF)</div>
                    <div className="text-[11px] text-slate-400 mt-1">demo_authentic_voice.wav</div>
                    <span className="text-[10px] mt-2 px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 w-fit">Authentic</span>
                  </label>

                  <label
                    onClick={() => setSelectedSampleFile('demo_authentic_cctv.mp4')}
                    className={`cursor-pointer p-3 rounded-xl border flex flex-col justify-between transition-all ${
                      selectedSampleFile === 'demo_authentic_cctv.mp4'
                        ? 'border-emerald-500 bg-emerald-950/30 text-emerald-200 shadow-md'
                        : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="text-xs font-bold">Authentic CCTV Video</div>
                    <div className="text-[11px] text-slate-400 mt-1">demo_authentic_cctv.mp4</div>
                    <span className="text-[10px] mt-2 px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 w-fit">Continuous</span>
                  </label>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                      setSelectedFile(e.dataTransfer.files[0]);
                    }
                  }}
                  className="border-2 border-dashed border-slate-700 hover:border-cyan-500 rounded-xl p-5 text-center transition-colors bg-slate-950/50 cursor-pointer"
                  onClick={() => document.getElementById('custom-file-input')?.click()}
                >
                  <input
                    id="custom-file-input"
                    type="file"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setSelectedFile(e.target.files[0]);
                      }
                    }}
                  />
                  {selectedFile ? (
                    <div className="flex items-center justify-center gap-3 text-cyan-300">
                      <FileCheck className="w-6 h-6" />
                      <div className="text-left">
                        <div className="text-xs font-semibold">{selectedFile.name}</div>
                        <div className="text-[11px] text-slate-400">
                          {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type || 'Binary'}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1.5 text-slate-400">
                      <UploadCloud className="w-7 h-7 mx-auto text-slate-500" />
                      <p className="text-xs font-medium text-slate-300">
                        Drop smartphone evidence here, or <span className="text-cyan-400 underline">browse</span>
                      </p>
                      <p className="text-[11px] text-slate-500">
                        Supports: .jpg, .jpeg, .png, .webp, .wav, .mp3, .m4a, .ogg, .mp4, .mov, .mkv, .avi
                      </p>
                    </div>
                  )}
                </div>

                {/* Auto-Purge Toggle */}
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <input
                    type="checkbox"
                    id="auto-purge-toggle"
                    checked={autoPurge}
                    onChange={(e) => setAutoPurge(e.target.checked)}
                    className="mt-0.5 rounded border-slate-700 text-cyan-500 focus:ring-0"
                  />
                  <label htmlFor="auto-purge-toggle" className="text-xs text-slate-300 cursor-pointer">
                    <span className="font-semibold text-slate-200">Auto-purge raw evidence file after report generation</span>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      Recommended for privacy: deletes raw file from server after extracting cryptographic hashes, visual heatmaps, and generating court-ready PDF.
                    </p>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Modal Actions */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
            <span className="text-[11px] text-slate-500">
              SHA-256 pre-computed on bitstream upload • Chain of custody immutably logged
            </span>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center gap-2 px-5 py-2 text-xs font-semibold rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white transition-all shadow-md shadow-cyan-950/60 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Processing Intake...</span>
                  </>
                ) : (
                  <>
                    <Shield className="w-4 h-4" />
                    <span>Initialize Forensic Case</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
