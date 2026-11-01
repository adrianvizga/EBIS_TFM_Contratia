import { describe, it, expect, beforeEach } from 'vitest';
import { generatedContractsService } from '../../../services/generatedContracts';
import { setAccessToken } from '../../../services/authTokenStore';
import { server } from '../../../test/mocks/server';
import { http, HttpResponse } from 'msw';

describe('generatedContractsService', () => {
  beforeEach(() => {
    setAccessToken('mock-access-token');
  });

  it('getAll_calls_correct_url — getAll() fetches from /api/generated-contracts', async () => {
    const result = await generatedContractsService.getAll();
    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBeGreaterThan(0);
    expect(result[0].id).toBe('gc-1');
    expect(result[0].title).toBe('Test Contract');
  });

  it('create_sends_body — create() sends POST with contract data', async () => {
    let receivedBody: Record<string, unknown> | null = null;
    server.use(
      http.post('http://localhost:8000/api/generated-contracts', async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'gc-new',
          title: receivedBody.title,
          contract_type: receivedBody.contract_type,
          country: 'ES', language: 'es', tone: 'formal',
          status: 'pending', current_content: '',
          created_at: '2026-02-22T10:00:00Z', updated_at: '2026-02-22T10:00:00Z',
        }, { status: 201 });
      }),
    );

    const data = { title: 'Mi Contrato', contract_type: 'rental', description: 'Test desc' };
    const result = await generatedContractsService.create(data);

    expect(receivedBody).not.toBeNull();
    expect(receivedBody!.title).toBe('Mi Contrato');
    expect(receivedBody!.contract_type).toBe('rental');
    expect(result.id).toBe('gc-new');
  });

  it('update_sends_content — update() sends PUT with content and change type', async () => {
    let receivedBody: Record<string, unknown> | null = null;
    server.use(
      http.put('http://localhost:8000/api/generated-contracts/:id', async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'gc-1', title: 'Test', contract_type: 'rental',
          country: 'ES', language: 'es', tone: 'formal', status: 'completed',
          current_content: receivedBody.content,
          created_at: '2026-01-15T10:00:00Z', updated_at: '2026-02-22T10:00:00Z',
        });
      }),
    );

    await generatedContractsService.update('gc-1', 'Updated content', 'manual_edit', 'Fixed typo');

    expect(receivedBody).not.toBeNull();
    expect(receivedBody!.content).toBe('Updated content');
    expect(receivedBody!.change_type).toBe('manual_edit');
    expect(receivedBody!.change_description).toBe('Fixed typo');
  });

  it('delete_calls_delete — delete() sends DELETE request', async () => {
    let deleteCalled = false;
    server.use(
      http.delete('http://localhost:8000/api/generated-contracts/:id', () => {
        deleteCalled = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    await generatedContractsService.delete('gc-1');
    expect(deleteCalled).toBe(true);
  });

  it('generateModification_sends_prompt — generateModification sends POST with prompt', async () => {
    let receivedBody: Record<string, unknown> | null = null;
    server.use(
      http.post('http://localhost:8000/api/generated-contracts/:id/generate', async ({ request }) => {
        receivedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          id: 'gc-1', title: 'Test', contract_type: 'rental',
          country: 'ES', language: 'es', tone: 'formal', status: 'completed',
          current_content: 'AI modified content',
          created_at: '2026-01-15T10:00:00Z', updated_at: '2026-02-22T10:00:00Z',
        });
      }),
    );

    const result = await generatedContractsService.generateModification('gc-1', 'Hazlo más formal');

    expect(receivedBody).not.toBeNull();
    expect(receivedBody!.prompt).toBe('Hazlo más formal');
    expect(result.current_content).toBe('AI modified content');
  });

  it('sendToAnalysis — sendToAnalysis sends POST to /:id/send-to-analysis', async () => {
    const result = await generatedContractsService.sendToAnalysis('gc-1');

    expect(result.id).toBe('contract-analysis-1');
    expect(result.status).toBe('pending');
    expect(result.message).toBe('Contract sent to analysis');
  });

  it('includes_auth_token — requests include Authorization header from memory token store', async () => {
    let authHeader: string | null = null;
    server.use(
      http.get('http://localhost:8000/api/generated-contracts', ({ request }) => {
        authHeader = request.headers.get('Authorization');
        return HttpResponse.json([]);
      }),
    );

    await generatedContractsService.getAll();

    expect(authHeader).toBe('Bearer mock-access-token');
  });
});
  it('retry_posts_to_retry_endpoint', async () => {
    server.use(
      http.post('http://localhost:8000/api/generated-contracts/:id/retry', () =>
        HttpResponse.json({ id: 'gc-1', status: 'pending' })
      )
    );
    const result = await generatedContractsService.retry('gc-1');
    expect(result.status).toBe('pending');
  });
