export type MediaType = 'image' | 'video' | 'audio';
export type FileStatus = 'queued' | 'running' | 'done' | 'failed';
export type FindingResult = 'pass' | 'suspicious' | 'tampered' | 'not_applicable' | 'inconclusive';
export type OverallVerdict = 'AUTHENTIC' | 'SUSPICIOUS' | 'LIKELY_TAMPERED' | 'INCONCLUSIVE';

export interface Finding {
  module: string;
  check_name: string;
  result: FindingResult;
  confidence: number;
  explanation: string;
  evidence: Record<string, any>;
  artifact_paths: string[];
}

export interface ModuleResult {
  module: string;
  version: string;
  duration_ms: number;
  findings: Finding[];
  error?: string | null;
}

export interface Verdict {
  overall: OverallVerdict;
  score: number;
  top_reasons: string[];
  per_module_scores: Record<string, number>;
}

export interface EvidenceFile {
  file_id: string;
  original_name: string;
  media_type: MediaType;
  size_bytes: number;
  mime: string;
  sha256_at_upload: string;
  sha256_at_report?: string | null;
  storage_path: string;
  status: FileStatus;
  uploaded_at: string;
  auto_purge?: boolean;
  is_forward_simulation?: boolean;
  forward_source_hash?: string | null;
  results?: Record<string, ModuleResult> | null;
  verdict?: Verdict | null;
}

export interface Case {
  case_id: string;
  created_at: string;
  investigator_name: string;
  case_reference: string;
  
  // BSA 2023 Section 63 & Custody Particulars
  offense_type?: string;
  requestor_name?: string;
  authority_basis?: string;
  examination_scope?: string;
  
  // BSA Part A (Party & Device Particulars)
  producer_name?: string;
  parentage_and_address?: string;
  device_source_type?: string;
  make_and_model?: string;
  color?: string;
  serial_or_imei?: string;
  lawful_control_role?: string;
  
  // Custody & Acquisition
  seized_at_ist?: string;
  seizure_location?: string;
  collection_method?: string;
  
  // BSA Part B (Expert Particulars)
  expert_name?: string;
  expert_designation?: string;
  lab_organization?: string;

  files: EvidenceFile[];
}

export interface AuditEntry {
  id?: number;
  timestamp_utc: string;
  case_id: string;
  file_id?: string | null;
  action: string;
  actor: string;
  details: Record<string, any>;
  sha256?: string | null;
}

export interface SampleFixture {
  filename: string;
  media_type: string;
  size_bytes: number;
  is_tampered: boolean;
  description: string;
}
