import { useUser } from '../context/useUser';
import { useCallback } from 'react';
import { getAccessToken } from '../services/authTokenStore';

export const useAuthFetch = () => {
  const { token, logout, refreshAccessToken } = useUser();

  const authFetch = useCallback(
    async (url: string, options: RequestInit = {}): Promise<Response> => {
      const headers: Record<string, string> = {
        ...(options.headers as Record<string, string>),
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(url, {
        ...options,
        headers,
        credentials: options.credentials ?? 'include',
      });

      if (response.status === 401) {
        try {
          await refreshAccessToken();
        } catch {
          throw new Error('Session expired. Please login again.');
        }
        const freshToken = getAccessToken();
        const retryHeaders: Record<string, string> = {
          ...(options.headers as Record<string, string>),
        };
        if (freshToken) {
          retryHeaders['Authorization'] = `Bearer ${freshToken}`;
        }
        const retryResponse = await fetch(url, {
          ...options,
          headers: retryHeaders,
          credentials: options.credentials ?? 'include',
        });
        if (retryResponse.status === 401) {
          logout();
          throw new Error('Session expired. Please login again.');
        }
        return retryResponse;
      }

      return response;
    },
    [token, logout, refreshAccessToken]
  );

  return authFetch;
};
