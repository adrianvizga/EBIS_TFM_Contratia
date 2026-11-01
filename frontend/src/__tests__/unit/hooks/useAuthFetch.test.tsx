import { describe, it, expect } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { UserProvider } from '../../../context/UserContext';
import { useUser } from '../../../context/useUser';
import { LanguageProvider } from '../../../context/LanguageContext';
import { useAuthFetch } from '../../../hooks/useAuthFetch';
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

describe('useAuthFetch', () => {
  const renderAuthFetch = async () => {
    const rendered = renderHook(() => ({
      authFetch: useAuthFetch(),
      user: useUser(),
    }), { wrapper: Wrapper });

    await waitFor(() => expect(rendered.result.current.user.isLoading).toBe(false));
    return rendered;
  };

  it('injects_bearer_token — authFetch adds Authorization header', async () => {
    const { result } = await renderAuthFetch();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    let response: Response | null = null;
    await act(async () => {
      response = await result.current.authFetch('http://localhost:8000/api/auth/me');
    });

    expect(response!.status).toBe(200);
  });

  it('401_triggers_logout — 401 response triggers logout and throws', async () => {
    server.use(
      http.get('http://localhost:8000/api/test-401', () => {
        return HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 });
      }),
    );

    const { result } = await renderAuthFetch();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    expect(result.current.user.isAuthenticated).toBe(true);

    let error: Error | null = null;
    await act(async () => {
      try {
        await result.current.authFetch('http://localhost:8000/api/test-401');
      } catch (e) {
        error = e as Error;
      }
    });

    expect(error).not.toBeNull();
    expect(error!.message).toContain('Session expired');
    expect(result.current.user.isAuthenticated).toBe(false);
  });

  it('non_401_no_logout — non-401 error does NOT trigger logout', async () => {
    server.use(
      http.get('http://localhost:8000/api/test-403', () => {
        return HttpResponse.json({ detail: 'Forbidden' }, { status: 403 });
      }),
    );

    const { result } = await renderAuthFetch();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    let response: Response | null = null;
    await act(async () => {
      response = await result.current.authFetch('http://localhost:8000/api/test-403');
    });

    expect(response!.status).toBe(403);
    expect(result.current.user.isAuthenticated).toBe(true);
  });

  it('passes_custom_headers — custom headers are preserved alongside Authorization', async () => {
    let receivedHeaders: Record<string, string> = {};
    server.use(
      http.get('http://localhost:8000/api/test-headers', ({ request }) => {
        receivedHeaders = {
          authorization: request.headers.get('Authorization') || '',
          'x-custom': request.headers.get('X-Custom') || '',
        };
        return HttpResponse.json({ ok: true });
      }),
    );

    const { result } = await renderAuthFetch();

    await act(async () => {
      await result.current.user.login('test@test.com', 'Test1234');
    });

    await act(async () => {
      await result.current.authFetch('http://localhost:8000/api/test-headers', {
        headers: { 'X-Custom': 'my-value' },
      });
    });

    expect(receivedHeaders.authorization).toContain('Bearer ');
    expect(receivedHeaders['x-custom']).toBe('my-value');
  });
});
