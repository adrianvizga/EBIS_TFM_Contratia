import type { AnalyzedContract, ContractAnalysisData, ContractStreamEvent } from './types';

export type AuthFetch = (input: string, init?: RequestInit) => Promise<Response>;

export interface NotificationPayload {
  title: string;
  message: string;
  notification_type: 'success' | 'error';
  related_entity_type: 'contract';
  related_entity_id?: string;
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
  return response.json() as Promise<T>;
}

export async function listContracts(authFetch: AuthFetch): Promise<AnalyzedContract[]> {
  return readJson(await authFetch('/api/contracts', { headers: { 'Content-Type': 'application/json' } }));
}

export async function getContractAnalysis(contractId: string, token: string): Promise<ContractAnalysisData> {
  const response = await fetch(`/api/contracts/${contractId}/analysis`, {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  });
  return readJson(response);
}

export async function uploadContract(authFetch: AuthFetch, file: File): Promise<void> {
  const body = new FormData();
  body.append('file', file);
  const response = await authFetch('/api/contracts/upload', { method: 'POST', body });
  if (!response.ok) {
    const error = await response.json() as { detail?: string };
    throw new Error(error.detail || `Error uploading ${file.name}`);
  }
}

export async function deleteContractRequest(contractId: string, token: string): Promise<void> {
  const response = await fetch(`/api/contracts/${contractId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
}

export async function retryContractAnalysis(authFetch: AuthFetch, contractId: string): Promise<void> {
  const response = await authFetch(`/api/contracts/${contractId}/retry`, { method: 'POST' });
  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(error.detail || `Error retrying contract ${contractId}`);
  }
}

export async function createNotification(
  request: AuthFetch,
  payload: NotificationPayload,
): Promise<Response> {
  return request('/api/notifications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function createTokenNotification(
  token: string,
  payload: NotificationPayload,
): Promise<Response> {
  return fetch('/api/notifications', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function streamContractEvents(
  token: string,
  onEvent: (event: ContractStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch('/api/contracts/stream', {
    headers: { Authorization: `Bearer ${token}`, Accept: 'text/event-stream' },
    signal,
  });
  if (!response.ok) throw new Error('SSE connection failed');
  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let pending = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    pending += decoder.decode(value, { stream: true });
    const lines = pending.split('\n');
    pending = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      try {
        onEvent(JSON.parse(line.slice(6)) as ContractStreamEvent);
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    }
  }
}
