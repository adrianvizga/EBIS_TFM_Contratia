import { describe, it, expect } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { UserProvider } from '../../../context/UserContext';
import { useUser } from '../../../context/useUser';
import { LanguageProvider } from '../../../context/LanguageContext';
import { ThemeProvider } from '../../../context/ThemeContext';
import { useSettings } from '../../../hooks/useSettings';
import { BrowserRouter } from 'react-router-dom';
import { server } from '../../../test/mocks/server';
import { http, HttpResponse } from 'msw';
import type { ReactNode } from 'react';

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <LanguageProvider>
        <ThemeProvider>
          <UserProvider>{children}</UserProvider>
        </ThemeProvider>
      </LanguageProvider>
    </BrowserRouter>
  );
}

describe('useSettings', () => {
  const renderSettings = async () => {
    const rendered = renderHook(() => ({
      settings: useSettings(),
      user: useUser(),
    }), { wrapper: Wrapper });

    await waitFor(() => expect(rendered.result.current.user.isLoading).toBe(false));
    return rendered;
  };

  it('load_applies_theme — loadSettings applies theme from API', async () => {
    server.use(
      http.get('http://localhost:8000/api/settings', () => {
        return HttpResponse.json({
          id: 'settings-1', user_id: 'usr-test-001',
          theme: 'dark', language: 'es', currency: 'EUR',
          email_notifications: true, push_notifications: false, allow_analytics: true,
          created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
        });
      }),
    );

    const { result } = await renderSettings();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    await waitFor(() => expect(result.current.settings.settings).not.toBeNull());

    expect(result.current.settings.settings!.theme).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('load_applies_language — loadSettings applies language from API', async () => {
    server.use(
      http.get('http://localhost:8000/api/settings', () => {
        return HttpResponse.json({
          id: 'settings-1', user_id: 'usr-test-001',
          theme: 'light', language: 'en', currency: 'EUR',
          email_notifications: true, push_notifications: false, allow_analytics: true,
          created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
        });
      }),
    );

    const { result } = await renderSettings();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    await waitFor(() => expect(result.current.settings.settings).not.toBeNull());

    expect(result.current.settings.settings!.language).toBe('en');
    expect(localStorage.getItem('language')).toBe('en');
  });

  it('update_sends_put — updateSettings sends PUT to /api/settings', async () => {
    let putBody: Record<string, unknown> | null = null;
    server.use(
      http.put('http://localhost:8000/api/settings', async ({ request }) => {
        putBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'settings-1', user_id: 'usr-test-001',
          theme: putBody.theme ?? 'light', language: putBody.language ?? 'es',
          currency: putBody.currency ?? 'EUR',
          email_notifications: true, push_notifications: false, allow_analytics: true,
          created_at: '2026-01-01T00:00:00Z', updated_at: '2026-02-22T00:00:00Z',
        });
      }),
    );

    const { result } = await renderSettings();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    await waitFor(() => expect(result.current.settings.settings).not.toBeNull());

    let updateResult: boolean | undefined;
    await act(async () => {
      updateResult = await result.current.settings.updateSettings({ theme: 'dark' });
    });

    expect(updateResult).toBe(true);
    expect(putBody).not.toBeNull();
    expect(putBody!.theme).toBe('dark');
  });
});
