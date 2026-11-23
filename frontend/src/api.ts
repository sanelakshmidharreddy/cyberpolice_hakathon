import { Case, AuditEntry, EvidenceFile, Verdict, ModuleResult } from './types';

const API_BASE = '/api';

export async function createCase(investigatorName: string, caseReference: string): Promise<Case> {
  const res = await fetch(`${API_BASE}/cases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      investigator_name: investigatorName,
      case_reference: caseReference,
    }),
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
    xhr.send(formData);
  });
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
  // Extract artifact filename from local filesystem path or URL
  const name = artifactPath.split(/[\/\\]/).pop() || 'artifact.png';
  return `${API_BASE}/cases/${caseId}/artifacts/${fileId}/${name}`;
}

export function getContentUrl(caseId: string, fileId: string): string {
  return `${API_BASE}/cases/${caseId}/files/${fileId}/content`;
}
