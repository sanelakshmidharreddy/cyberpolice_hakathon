import { Case, AuditEntry, EvidenceFile, Verdict, ModuleResult, SampleFixture } from './types';

const API_BASE = '/api';

export interface CreateCaseParams {
  case_id?: string;
  investigator_name: string;
  case_reference: string;
  offense_type?: string;
  requestor_name?: string;
  authority_basis?: string;
  examination_scope?: string;
  producer_name?: string;
  parentage_and_address?: string;
  device_source_type?: string;
  make_and_model?: string;
  color?: string;
  serial_or_imei?: string;
  lawful_control_role?: string;
  seized_at_ist?: string;
  seizure_location?: string;
  collection_method?: string;
  expert_name?: string;
  expert_designation?: string;
  lab_organization?: string;
}

export async function createCase(params: CreateCaseParams): Promise<Case> {
  const res = await fetch(`${API_BASE}/cases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create case');
  }
  return res.json();
}

export async function listCases(): Promise<Case[]> {
  const res = await fetch(`${API_BASE}/cases`);
  if (!res.ok) throw new Error('Failed to fetch cases list');
  return res.json();
}

export async function getCase(caseId: string): Promise<Case> {
  const res = await fetch(`${API_BASE}/cases/${caseId}`);
  if (!res.ok) throw new Error('Failed to fetch case details');
  return res.json();
}

export async function uploadEvidenceFile(
  caseId: string,
  file: File,
  autoPurge: boolean = false,
  onProgress?: (percent: number) => void
): Promise<EvidenceFile> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/cases/${caseId}/files`);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch (e) {
          reject(new Error('Invalid response from server'));
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || 'Upload failed'));
        } catch {
          reject(new Error(`Upload failed with HTTP ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => reject(new Error('Network error during file upload'));

    const formData = new FormData();
    formData.append('file', file);
    formData.append('auto_purge', String(autoPurge));
    xhr.send(formData);
  });
}

export async function listSamples(): Promise<SampleFixture[]> {
  const res = await fetch(`${API_BASE}/samples`);
  if (!res.ok) return [];
  return res.json();
}

export async function attachSample(caseId: string, filename: string): Promise<EvidenceFile> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/attach-sample/${filename}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to attach sample');
  }
  return res.json();
}

export async function simulateForward(caseId: string, sourceFileId?: string): Promise<EvidenceFile> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/simulate-forward`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_file_id: sourceFileId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to simulate messaging forward');
  }
  return res.json();
}

export async function triggerAnalysis(caseId: string, fileId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/files/${fileId}/analyze`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to start analysis');
  return res.json();
}

export async function getAnalysisStatus(caseId: string, fileId: string): Promise<{
  file_id: string;
  overall_status: string;
  modules: Record<string, string>;
}> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/files/${fileId}/status`);
  if (!res.ok) throw new Error('Failed to fetch analysis status');
  return res.json();
}

export async function getAnalysisResults(caseId: string, fileId: string): Promise<{
  file_id: string;
  status: string;
  sha256_at_upload?: string;
  is_forward_simulation?: boolean;
  forward_source_hash?: string | null;
  verdict?: Verdict | null;
  results?: Record<string, ModuleResult> | null;
}> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/files/${fileId}/results`);
  if (!res.ok) throw new Error('Failed to fetch analysis results');
  return res.json();
}

export async function getAuditTrail(caseId: string): Promise<AuditEntry[]> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/audit`);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

export function getArtifactUrl(caseId: string, fileId: string, artifactPath: string): string {
  const name = artifactPath.split(/[\/\\]/).pop() || 'artifact.png';
  return `${API_BASE}/cases/${caseId}/artifacts/${fileId}/${name}`;
}

export function getContentUrl(caseId: string, fileId: string): string {
  return `${API_BASE}/cases/${caseId}/files/${fileId}/content`;
}

export function getReportPdfUrl(caseId: string): string {
  return `${API_BASE}/cases/${caseId}/report.pdf`;
}

export function getAppendixJsonUrl(caseId: string): string {
  return `${API_BASE}/cases/${caseId}/appendix.json`;
}
