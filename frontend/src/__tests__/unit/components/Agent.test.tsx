import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import Agent from '../../../components/sections/Agent';

const authFetch = vi.fn();

vi.mock('../../../hooks/useAuthFetch', () => ({ useAuthFetch: () => authFetch }));
vi.mock('../../../context/useUser', () => ({
  useUser: () => ({ user: { id: 'user-1', role: '2', profile_image_url: null } }),
}));
vi.mock('../../../context/useLanguage', () => ({
  useLanguage: () => ({ t: (key: string) => key, language: 'es' }),
}));
vi.mock('../../../components/UpgradePlanScreen', () => ({ default: () => <div>upgrade</div> }));

const jsonResponse = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), {
  status,
  headers: { 'Content-Type': 'application/json' },
}));

function renderAgent() {
  return render(<MemoryRouter><Agent /></MemoryRouter>);
}

describe('Agent', () => {
  beforeEach(() => {
    authFetch.mockReset();
  });

  it('crea una conversación y envía un turno idempotente', async () => {
    authFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith('/conversations') && !options) return jsonResponse([]);
      if (url.endsWith('/conversations') && options?.method === 'POST') {
        return jsonResponse({ id: 'conv-1', title: 'Nueva conversación', message_count: 0,
          created_at: new Date().toISOString(), updated_at: new Date().toISOString() });
      }
      if (url.endsWith('/conv-1/messages')) return jsonResponse([]);
      if (url.endsWith('/conv-1/chat')) return jsonResponse({
        user_message: { id: 'u1', role: 'user', content: 'Pregunta jurídica', created_at: new Date().toISOString() },
        assistant_message: { id: 'a1', role: 'assistant', content: 'Respuesta jurídica', created_at: new Date().toISOString() },
      });
      return jsonResponse([]);
    });
    renderAgent();
    await screen.findByText('agent.noConversations');
    const input = await screen.findByPlaceholderText('agent.placeholder');
    fireEvent.change(input, { target: { value: 'Pregunta jurídica' } });
    fireEvent.click(screen.getByText('agent.send'));

    await screen.findByText('Respuesta jurídica');
    const chatCall = authFetch.mock.calls.find(([url]) => String(url).endsWith('/conv-1/chat'));
    const body = JSON.parse(String(chatCall?.[1]?.body));
    expect(body.message).toBe('Pregunta jurídica');
    expect(body.request_id).toMatch(/[0-9a-f-]{36}/);
  });

  it('restaura y conserva el contrato activo al enviar seguimientos', async () => {
    authFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith('/conversations') && !options) return jsonResponse([{
        id: 'conv-1', title: 'Contrato', message_count: 1,
        contract_id: '11111111-1111-4111-8111-111111111111', contract_name: 'alquiler.pdf',
        created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      }]);
      if (url.endsWith('/conv-1/messages')) return jsonResponse([]);
      if (url.endsWith('/conv-1/chat')) return jsonResponse({
        user_message: { id: 'u1', role: 'user', content: 'Seguimiento', contract_name: 'alquiler.pdf', created_at: new Date().toISOString() },
        assistant_message: { id: 'a1', role: 'assistant', content: 'Respuesta', created_at: new Date().toISOString() },
      });
      return jsonResponse([]);
    });
    renderAgent();
    fireEvent.click(await screen.findByText('Contrato'));
    await screen.findByText('alquiler.pdf');
    fireEvent.change(screen.getByPlaceholderText('agent.placeholder'), { target: { value: 'Seguimiento' } });
    fireEvent.click(screen.getByText('agent.send'));

    await waitFor(() => {
      const call = authFetch.mock.calls.find(([url]) => String(url).endsWith('/conv-1/chat'));
      expect(JSON.parse(String(call?.[1]?.body)).contract_id).toBe('11111111-1111-4111-8111-111111111111');
    });
  });

  it('muestra errores recuperables sin ocultar la pregunta', async () => {
    authFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith('/conversations') && !options) return jsonResponse([]);
      if (url.endsWith('/conversations') && options?.method === 'POST') {
        return jsonResponse({ id: 'conv-1', title: 'Nueva conversación', message_count: 0,
          created_at: new Date().toISOString(), updated_at: new Date().toISOString() });
      }
      if (url.endsWith('/conv-1/messages')) return jsonResponse([]);
      if (url.endsWith('/conv-1/chat')) {
        return jsonResponse({ detail: { code: 'chat_temporarily_unavailable', message: 'error' } }, 503);
      }
      return jsonResponse([]);
    });
    renderAgent();
    await screen.findByText('agent.noConversations');
    fireEvent.change(await screen.findByPlaceholderText('agent.placeholder'), { target: { value: 'Pregunta jurídica' } });
    fireEvent.click(screen.getByText('agent.send'));

    expect(await screen.findByText('Pregunta jurídica')).toBeInTheDocument();
    expect(screen.getByText('agent.retry')).toBeInTheDocument();
    expect(screen.getByText(/agent\.error/)).toBeInTheDocument();
  });
});
