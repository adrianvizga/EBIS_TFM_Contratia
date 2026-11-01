import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  createNotification,
  deleteContractRequest,
  listContracts,
  uploadContract,
  streamContractEvents,
  retryContractAnalysis,
} from '../../../components/sections/analyzeContract/api';

afterEach(() => vi.unstubAllGlobals());

describe('analyze contract API', () => {
  it('lists contracts through authenticated fetch', async () => {
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify([{ id: '1' }]), { status: 200 }));
    expect(await listContracts(request)).toEqual([{ id: '1' }]);
    expect(request).toHaveBeenCalledWith('/api/contracts', expect.any(Object));
  });

  it('propagates HTTP errors while listing', async () => {
    const request = vi.fn().mockResolvedValue(new Response(null, { status: 500, statusText: 'Failed' }));
    await expect(listContracts(request)).rejects.toThrow('Error 500: Failed');
  });

  it('uploads the file as multipart form data', async () => {
    const request = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    const file = new File(['contract'], 'contract.txt');
    await uploadContract(request, file);
    const options = request.mock.calls[0][1] as RequestInit;
    expect(request.mock.calls[0][0]).toBe('/api/contracts/upload');
    expect((options.body as FormData).get('file')).toBe(file);
  });

  it('uses the backend upload error detail', async () => {
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Invalid file' }), { status: 400 }));
    await expect(uploadContract(request, new File(['x'], 'x.txt'))).rejects.toThrow('Invalid file');
  });

  it('deletes a contract with its bearer token', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetchMock);
    await deleteContractRequest('abc', 'token');
    expect(fetchMock).toHaveBeenCalledWith('/api/contracts/abc', expect.objectContaining({ method: 'DELETE' }));
  });

  it('retries a failed analysis through authenticated fetch', async () => {
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'pending' }), { status: 200 }));
    await retryContractAnalysis(request, 'abc');
    expect(request).toHaveBeenCalledWith('/api/contracts/abc/retry', { method: 'POST' });
  });

  it('uses the backend retry error detail', async () => {
    const request = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Not retryable' }), { status: 409 }));
    await expect(retryContractAnalysis(request, 'abc')).rejects.toThrow('Not retryable');
  });

  it('serializes notification payloads', async () => {
    const request = vi.fn().mockResolvedValue(new Response(null, { status: 201 }));
    await createNotification(request, {
      title: 'Uploaded', message: 'Done', notification_type: 'success', related_entity_type: 'contract',
    });
    expect(JSON.parse((request.mock.calls[0][1] as RequestInit).body as string)).toMatchObject({ title: 'Uploaded' });
  });

  it('parses SSE events split across response chunks', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"contract_'));
        controller.enqueue(encoder.encode('id":"1","status":"completed"}\n'));
        controller.close();
      },
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream, { status: 200 })));
    const onEvent = vi.fn();
    await streamContractEvents('token', onEvent);
    expect(onEvent).toHaveBeenCalledWith({ contract_id: '1', status: 'completed' });
  });

  it('fails when the SSE endpoint rejects the connection', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 503 })));
    await expect(streamContractEvents('token', vi.fn())).rejects.toThrow('SSE connection failed');
  });
});
