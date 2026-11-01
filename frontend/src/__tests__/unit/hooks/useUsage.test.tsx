import { describe, it, expect } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { UserProvider } from '../../../context/UserContext';
import { useUser } from '../../../context/useUser';
import { LanguageProvider } from '../../../context/LanguageContext';
import { useUsage } from '../../../hooks/useUsage';
import { BrowserRouter } from 'react-router-dom';
import { server } from '../../../test/mocks/server';
import { http, HttpResponse } from 'msw';
import type { ReactNode } from 'react';

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <LanguageProvider>
        <UserProvider>{children}</UserProvider>
      </LanguageProvider>
    </BrowserRouter>
  );
}

describe('useUsage', () => {
  const renderUsage = async () => {
    const rendered = renderHook(() => ({
      usage: useUsage(),
      user: useUser(),
    }), { wrapper: Wrapper });

    await waitFor(() => expect(rendered.result.current.user.isLoading).toBe(false));
    return rendered;
  };

  it('remaining_generations — calculates remaining correctly', async () => {
    const { result } = await renderUsage();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    await waitFor(() => expect(result.current.usage.usage).not.toBeNull());

    expect(result.current.usage.remainingGenerations).toBe(1);
  });

  it('remaining_clamped_zero — remaining is clamped at 0 when over limit', async () => {
    server.use(
      http.get('http://localhost:8000/api/usage', () => {
        return HttpResponse.json({
          plan: 'free', role: '1',
          period_start: '2026-02-01',
          generation_reset_date: null, analysis_reset_date: null,
          contracts_generated: 5, contracts_generated_limit: 1,
          contracts_analyzed: 0, contracts_analyzed_limit: 3,
          ai_modifications: {}, ai_modifications_per_contract_limit: 3,
          agent_access: false,
        });
      }),
    );

    const { result } = await renderUsage();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    await waitFor(() => expect(result.current.usage.usage).not.toBeNull());

    expect(result.current.usage.remainingGenerations).toBe(0);
  });

  it('admin_infinite — admin (role "0") has infinite remaining', async () => {
    server.use(
      http.get('http://localhost:8000/api/usage', () => {
        return HttpResponse.json({
          plan: 'admin', role: '0',
          period_start: '2026-02-01',
          generation_reset_date: null, analysis_reset_date: null,
          contracts_generated: 100, contracts_generated_limit: null,
          contracts_analyzed: 200, contracts_analyzed_limit: null,
          ai_modifications: {}, ai_modifications_per_contract_limit: null,
          agent_access: true,
        });
      }),
    );

    const { result } = await renderUsage();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    await waitFor(() => expect(result.current.usage.usage).not.toBeNull());

    expect(result.current.usage.isAdmin).toBe(true);
    expect(result.current.usage.remainingGenerations).toBe(Infinity);
    expect(result.current.usage.remainingAnalyses).toBe(Infinity);
  });

  it('null_limit_infinite — null limit means Infinity', async () => {
    server.use(
      http.get('http://localhost:8000/api/usage', () => {
        return HttpResponse.json({
          plan: 'pro', role: '3',
          period_start: '2026-02-01',
          generation_reset_date: null, analysis_reset_date: null,
          contracts_generated: 5, contracts_generated_limit: null,
          contracts_analyzed: 3, contracts_analyzed_limit: null,
          ai_modifications: {}, ai_modifications_per_contract_limit: null,
          agent_access: true,
        });
      }),
    );

    const { result } = await renderUsage();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    await waitFor(() => expect(result.current.usage.usage).not.toBeNull());

    expect(result.current.usage.remainingGenerations).toBe(Infinity);
    expect(result.current.usage.remainingAnalyses).toBe(Infinity);
  });

  it('ai_mods_per_contract — getAiModsUsed returns correct count', async () => {
    const { result } = await renderUsage();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    await waitFor(() => expect(result.current.usage.usage).not.toBeNull());

    expect(result.current.usage.getAiModsUsed('contract-1')).toBe(2);
    expect(result.current.usage.getAiModsUsed('nonexistent')).toBe(0);
    expect(result.current.usage.getAiModsRemaining('contract-1')).toBe(1);
  });
});
