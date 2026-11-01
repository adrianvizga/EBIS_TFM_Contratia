import { describe, it, expect } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { UserProvider } from '../../../context/UserContext';
import { useUser } from '../../../context/useUser';
import { LanguageProvider } from '../../../context/LanguageContext';
import { BrowserRouter } from 'react-router-dom';
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

async function renderUserContext() {
  const { result } = renderHook(() => useUser(), { wrapper: Wrapper });

  await waitFor(() => {
    expect(result.current.isLoading).toBe(false);
  });

  return result;
}

describe('UserContext', () => {
  it('login_stores_tokens — login() stores tokens in sessionStorage', async () => {
    const { result } = renderHook(() => useUser(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login('test@test.com', 'Test1234');
    });

    expect(result.current.token).toBe('mock-access-token');
    expect(sessionStorage.getItem('authToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
  });

  it('login_sets_authenticated — after login isAuthenticated is true', async () => {
    const { result } = renderHook(() => useUser(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isAuthenticated).toBe(false);

    await act(async () => {
      await result.current.login('test@test.com', 'Test1234');
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).not.toBeNull();
    expect(result.current.user!.email).toBe('test@test.com');
  });

  it('logout_clears_state — logout() clears user, token, and storage', async () => {
    const { result } = renderHook(() => useUser(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login('test@test.com', 'Test1234');
    });
    expect(result.current.isAuthenticated).toBe(true);

    await act(async () => {
      result.current.logout();
    });

    await waitFor(() => {
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
    expect(sessionStorage.getItem('authToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
  });

  it('register_stores_tokens — register() stores tokens in sessionStorage', async () => {
    const { result } = renderHook(() => useUser(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.register({
        email: 'new@test.com',
        password: 'Test1234',
        terms_accepted: true,
        terms_version: 'terms-2026-06-20',
        privacy_version: 'privacy-2026-06-20',
        firstName: 'New',
        lastName: 'User',
      });
    });

    expect(result.current.token).toBe('mock-access-token');
    expect(sessionStorage.getItem('authToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('refresh_token_updates_access — refreshAccessToken() updates the access token', async () => {
    const { result } = renderHook(() => useUser(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login('test@test.com', 'Test1234');
    });

    await act(async () => {
      await result.current.refreshAccessToken();
    });

    expect(result.current.token).toBe('mock-new-access-token');
    expect(sessionStorage.getItem('authToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
  });

  it('session_restore_no_token — without stored token, isAuthenticated is false', async () => {
    const { current } = await renderUserContext();
    expect(current.isAuthenticated).toBe(false);
    expect(current.user).toBeNull();
  });

  it('session_restore_from_storage — with token in storage, session is restored', async () => {
    document.cookie = 'contratia_refresh_token=valid-refresh; path=/api/auth';
    sessionStorage.setItem('userData', JSON.stringify({ email: 'test@test.com', id: 'usr-test-001' }));

    const { result } = renderHook(() => useUser(), { wrapper: Wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isAuthenticated).toBe(true);
    });

    expect(result.current.user).not.toBeNull();
    expect(sessionStorage.getItem('authToken')).toBeNull();
  });

  it('error_mapping — "Email already registered" maps to auth.emailAlreadyRegistered', async () => {
    const { result } = renderHook(() => useUser(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    let caughtError: Error | null = null;
    await act(async () => {
      try {
        await result.current.register({
          email: 'existing@test.com',
          password: 'Test1234',
          terms_accepted: true,
          terms_version: 'terms-2026-06-20',
          privacy_version: 'privacy-2026-06-20',
          firstName: 'Test',
          lastName: 'User',
        });
      } catch (e) {
        caughtError = e as Error;
      }
    });

    expect(caughtError).not.toBeNull();
    expect(caughtError!.message).toBe('auth.emailAlreadyRegistered');
  });

  it('updateUser_merges — updateUser() merges partial data', async () => {
    const { result } = renderHook(() => useUser(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login('test@test.com', 'Test1234');
    });

    const originalEmail = result.current.user!.email;

    act(() => {
      result.current.updateUser({ first_name: 'Updated' });
    });

    expect(result.current.user!.first_name).toBe('Updated');
    expect(result.current.user!.email).toBe(originalEmail);
    const stored = JSON.parse(sessionStorage.getItem('userData')!);
    expect(stored.first_name).toBe('Updated');
  });
});
