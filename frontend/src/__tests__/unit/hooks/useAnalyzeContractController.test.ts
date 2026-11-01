import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAnalyzeContractController } from '../../../components/sections/analyzeContract/useAnalyzeContractController';
import * as api from '../../../components/sections/analyzeContract/api';

const authFetchMock = vi.fn();

vi.mock('../../../context/useLanguage', () => ({ useLanguage: () => ({ t: (key: string) => key }) }));
vi.mock('../../../context/useNotifications', () => ({ useNotifications: () => ({ refreshNotifications: vi.fn() }) }));
vi.mock('../../../context/useUser', () => ({ useUser: () => ({ token: 'token' }) }));
vi.mock('../../../hooks/useAuthFetch', () => ({ useAuthFetch: () => authFetchMock }));
vi.mock('../../../hooks/useUsage', () => ({ useUsage: () => ({ usage: null, remainingAnalyses: 3, refresh: vi.fn() }) }));
vi.mock('react-router-dom', () => ({ useNavigate: () => vi.fn() }));
vi.mock('../../../components/sections/analyzeContract/api', async importOriginal => ({
  ...(await importOriginal<typeof api>()),
  listContracts: vi.fn(),
  streamContractEvents: vi.fn((_token: string, _onEvent: unknown, signal?: AbortSignal) => new Promise<void>(resolve => {
    signal?.addEventListener('abort', () => resolve(), { once: true });
  })),
}));

describe('useAnalyzeContractController', () => {
  beforeEach(() => vi.mocked(api.listContracts).mockResolvedValue([]));

  it('loads contracts and exposes the empty result', async () => {
    const { result } = renderHook(() => useAnalyzeContractController());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.analyzedContracts).toEqual([]);
    expect(api.listContracts).toHaveBeenCalled();
  });

  it('filters and paginates loaded contracts', async () => {
    vi.mocked(api.listContracts).mockResolvedValue([{
      id: '1', filename: 'Lease.pdf', uploadDate: '01/01/2026', status: 'completed',
      riskLevel: 'low', riskCount: 0, positiveCount: 1,
    }]);
    const { result } = renderHook(() => useAnalyzeContractController());
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.setSearchTerm('missing'));
    expect(result.current.filteredContracts).toEqual([]);
  });

  it('opens and closes the delete modal', async () => {
    vi.mocked(api.listContracts).mockResolvedValue([{
      id: '1', filename: 'Lease.pdf', uploadDate: '01/01/2026', status: 'pending',
      riskLevel: 'low', riskCount: 0, positiveCount: 0,
    }]);
    const { result } = renderHook(() => useAnalyzeContractController());
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.deleteContract('1'));
    expect(result.current.deleteModalOpen).toBe(true);
    act(() => result.current.cancelDelete());
    expect(result.current.deleteModalOpen).toBe(false);
  });
});
