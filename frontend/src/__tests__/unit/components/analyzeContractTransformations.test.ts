import { describe, expect, it } from 'vitest';
import { applyStreamEvent, filterContracts, getFilenameParts, paginateContracts, splitFilename } from '../../../components/sections/analyzeContract/transformations';
import type { AnalyzedContract } from '../../../components/sections/analyzeContract/types';

const contract: AnalyzedContract = {
  id: '1', filename: 'contract.pdf', uploadDate: '2026-01-01', status: 'pending',
  riskLevel: 'low', riskCount: 0, positiveCount: 0,
};

describe('analyze contract transformations', () => {
  it('updates only the contract identified by an SSE event', () => {
    const result = applyStreamEvent([contract], { contract_id: '1', status: 'completed', overall_risk: 'high' });
    expect(result[0]).toMatchObject({ status: 'completed', riskLevel: 'high' });
  });

  it('preserves risk when an SSE event omits it', () => {
    expect(applyStreamEvent([contract], { contract_id: '1', status: 'analyzing' })[0].riskLevel).toBe('low');
  });

  it('splits and truncates filenames without losing the extension', () => {
    expect(splitFilename('averylongcontractname.pdf', 5)).toEqual({ name: 'avery...', extension: '.pdf' });
  });

  it('filters by search, status, risk and dates', () => {
    const datedContract = { ...contract, uploadDate: '01/01/2026' };
    expect(filterContracts([datedContract], {
      searchTerm: 'contract', status: 'pending', riskLevel: 'all', dateFrom: '2025-12-31', dateTo: '2026-01-02',
    })).toEqual([datedContract]);
    expect(filterContracts([datedContract], {
      searchTerm: '', status: 'completed', riskLevel: 'all', dateFrom: '', dateTo: '',
    })).toEqual([]);
  });

  it('paginates contracts and reports total pages', () => {
    const contracts = Array.from({ length: 11 }, (_, index) => ({ ...contract, id: String(index) }));
    expect(paginateContracts(contracts, 2)).toMatchObject({ totalPages: 2, contracts: [{ ...contract, id: '10' }] });
  });

  it('formats filenames for display', () => {
    expect(getFilenameParts('agreement.final.pdf', 9)).toEqual({ displayName: 'agreement…', extension: 'PDF', isTruncated: true });
  });
});
