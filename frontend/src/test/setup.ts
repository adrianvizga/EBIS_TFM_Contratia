import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, afterAll } from 'vitest';
import { server } from './mocks/server';
import { setAccessToken } from '../services/authTokenStore';

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
  sessionStorage.clear();
  localStorage.clear();
  setAccessToken(null);
  document.cookie = 'contratia_refresh_token=; Max-Age=0; path=/api/auth';
  document.cookie = 'contratia_refresh_token=; Max-Age=0; path=/';
});
afterAll(() => server.close());
