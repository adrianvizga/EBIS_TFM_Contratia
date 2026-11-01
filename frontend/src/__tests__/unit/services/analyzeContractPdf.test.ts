import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createContractAnalysisPdf } from '../../../components/sections/analyzeContract/pdfService';
import type { ContractAnalysisData } from '../../../components/sections/analyzeContract/types';

const save = vi.fn();
const createPdf = () => new Proxy({
  internal: { pageSize: { getWidth: () => 210, getHeight: () => 297 } },
  splitTextToSize: (text: string) => [text],
  getNumberOfPages: () => 1,
  save,
}, { get: (target, property) => property in target ? target[property as keyof typeof target] : vi.fn() });

const JsPdfMock = vi.fn(function JsPDF() { return createPdf(); });

vi.mock('jspdf', () => ({ default: JsPdfMock }));

const analysis: ContractAnalysisData = {
  filename: 'lease.pdf', uploadDate: '01/01/2026', status: 'completed', riskLevel: 'low',
  riskCount: 0, positiveCount: 0, missingCount: 0, clauses: [], riskFindings: [],
  positiveFindings: [], missingElements: [], relations: [],
};

describe('contract analysis PDF', () => {
  beforeEach(() => {
    save.mockReset();
  });

  it('generates and saves the report with the established filename', async () => {
    await createContractAnalysisPdf(analysis);
    expect(save).toHaveBeenCalledWith('analisis_lease.pdf');
  });

  it('propagates generator failures to the controller', async () => {
    save.mockImplementationOnce(() => { throw new Error('disk failure'); });
    await expect(createContractAnalysisPdf(analysis)).rejects.toThrow('disk failure');
  });
});
