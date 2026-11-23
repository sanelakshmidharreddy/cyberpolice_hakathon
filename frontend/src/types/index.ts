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
  results?: Record<string, ModuleResult> | null;
  verdict?: Verdict | null;
}

export interface Case {
  case_id: string;
  created_at: string;
  investigator_name: string;
  case_reference: string;
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
