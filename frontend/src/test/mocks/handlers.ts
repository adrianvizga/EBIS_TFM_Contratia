import { http, HttpResponse } from 'msw';

const API = 'http://localhost:8000/api';

const mockUser = {
  id: 'usr-test-001',
  email: 'test@test.com',
  first_name: 'Test',
  last_name: 'User',
  role: '1',
  is_active: true,
  profile_image_url: null,
  auth_provider: 'email',
};

export const handlers = [
  http.post(`${API}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as Record<string, string>;
    if (body.email === 'test@test.com' && body.password === 'Test1234') {
      return HttpResponse.json({
        access_token: 'mock-access-token',
        user: mockUser,
      });
    }
    return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 });
  }),

  http.post(`${API}/auth/register`, async ({ request }) => {
    const body = (await request.json()) as Record<string, string>;
    if (body.email === 'existing@test.com') {
      return HttpResponse.json({ detail: 'Email already registered' }, { status: 400 });
    }
    return HttpResponse.json({
      access_token: 'mock-access-token',
      user: { ...mockUser, email: body.email, first_name: body.first_name },
    });
  }),

  http.post(`${API}/auth/google-login`, async ({ request }) => {
    const body = (await request.json()) as Record<string, string>;
    if (body.token === 'invalid-token') {
      return HttpResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }
    return HttpResponse.json({
      access_token: 'mock-google-access-token',
      user: { ...mockUser, auth_provider: 'google' },
    });
  }),

  http.get(`${API}/auth/me`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    return HttpResponse.json(mockUser);
  }),

  http.post(`${API}/auth/refresh`, ({ request }) => {
    const cookie = request.headers.get('cookie') || '';
    const hasRestorableUser = sessionStorage.getItem('userData') !== null;
    if (
      cookie.includes('contratia_refresh_token=mock-refresh-token')
      || cookie.includes('contratia_refresh_token=valid-refresh')
      || hasRestorableUser
    ) {
      return HttpResponse.json({ access_token: 'mock-new-access-token' });
    }
    return HttpResponse.json({ detail: 'Invalid refresh token' }, { status: 401 });
  }),

  http.post(`${API}/auth/logout`, () => {
    return HttpResponse.json({ message: 'Logged out' });
  }),

  http.get(`${API}/usage`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    return HttpResponse.json({
      plan: 'free',
      role: '1',
      period_start: '2026-02-01',
      generation_reset_date: null,
      analysis_reset_date: null,
      contracts_generated: 0,
      contracts_generated_limit: 1,
      contracts_analyzed: 1,
      contracts_analyzed_limit: 3,
      ai_modifications: { 'contract-1': 2 },
      ai_modifications_per_contract_limit: 3,
      agent_access: false,
    });
  }),

  http.get(`${API}/settings`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    return HttpResponse.json({
      id: 'settings-1',
      user_id: 'usr-test-001',
      theme: 'light',
      language: 'es',
      currency: 'EUR',
      email_notifications: true,
      push_notifications: false,
      allow_analytics: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });
  }),

  http.put(`${API}/settings`, async ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: 'settings-1',
      user_id: 'usr-test-001',
      theme: body.theme ?? 'light',
      language: body.language ?? 'es',
      currency: body.currency ?? 'EUR',
      email_notifications: body.email_notifications ?? true,
      push_notifications: body.push_notifications ?? false,
      allow_analytics: body.allow_analytics ?? true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-02-22T00:00:00Z',
    });
  }),

  http.get(`${API}/generated-contracts`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    return HttpResponse.json([
      {
        id: 'gc-1',
        title: 'Test Contract',
        contract_type: 'rental',
        country: 'ES',
        language: 'es',
        tone: 'formal',
        status: 'completed',
        current_content: 'Contract content here',
        created_at: '2026-01-15T10:00:00Z',
        updated_at: '2026-01-15T10:00:00Z',
      },
    ]);
  }),

  http.get(`${API}/generated-contracts/:id`, ({ request, params }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    return HttpResponse.json({
      id: params.id,
      title: 'Test Contract',
      contract_type: 'rental',
      country: 'ES',
      language: 'es',
      tone: 'formal',
      status: 'completed',
      current_content: 'Contract content here',
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
    });
  }),

  http.post(`${API}/generated-contracts`, async ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: 'gc-new',
      title: body.title || 'New Contract',
      contract_type: body.contract_type || 'service',
      country: 'ES',
      language: 'es',
      tone: 'formal',
      status: 'pending',
      current_content: '',
      created_at: '2026-02-22T10:00:00Z',
      updated_at: '2026-02-22T10:00:00Z',
    }, { status: 201 });
  }),

  http.put(`${API}/generated-contracts/:id`, async ({ request, params }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: params.id,
      title: 'Test Contract',
      contract_type: 'rental',
      country: 'ES',
      language: 'es',
      tone: 'formal',
      status: 'completed',
      current_content: body.content || 'Updated content',
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-02-22T10:00:00Z',
    });
  }),

  http.delete(`${API}/generated-contracts/:id`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.get(`${API}/generated-contracts/:id/versions`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    return HttpResponse.json([
      {
        id: 'ver-1',
        version_number: 1,
        content: 'Version 1 content',
        change_type: 'creation',
        change_description: 'Initial version',
        created_at: '2026-01-15T10:00:00Z',
      },
    ]);
  }),

  http.post(`${API}/generated-contracts/:id/send-to-analysis`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    return HttpResponse.json({
      id: 'contract-analysis-1',
      filename: 'test-contract.txt',
      status: 'pending',
      message: 'Contract sent to analysis',
    });
  }),

  http.post(`${API}/generated-contracts/:id/generate`, async ({ request, params }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 });
    }
    return HttpResponse.json({
      id: params.id,
      title: 'Test Contract',
      contract_type: 'rental',
      country: 'ES',
      language: 'es',
      tone: 'formal',
      status: 'completed',
      current_content: 'AI modified content',
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-02-22T10:00:00Z',
    });
  }),
];
