import type { AnalyzedContract, ContractStreamEvent } from './types';

export const ITEMS_PER_PAGE = 10;

export interface ContractFilters {
  searchTerm: string;
  status: string;
  riskLevel: string;
  dateFrom: string;
  dateTo: string;
}

export function applyStreamEvent(contracts: AnalyzedContract[], event: ContractStreamEvent) {
  return contracts.map(contract => contract.id === event.contract_id
    ? { ...contract, status: event.status, riskLevel: event.overall_risk ?? contract.riskLevel }
    : contract);
}

export function splitFilename(filename: string, maxNameLength = 30) {
  const lastDot = filename.lastIndexOf('.');
  const extension = lastDot > 0 ? filename.slice(lastDot) : '';
  const name = lastDot > 0 ? filename.slice(0, lastDot) : filename;
  return { name: name.length > maxNameLength ? `${name.slice(0, maxNameLength)}...` : name, extension };
}

export function getFilenameParts(filename: string, maxNameLength = 30) {
  const lastDotIndex = filename.lastIndexOf('.');
  const extension = lastDotIndex !== -1 ? filename.slice(lastDotIndex + 1).toUpperCase() : '';
  const nameWithoutExtension = lastDotIndex !== -1 ? filename.slice(0, lastDotIndex) : filename;
  const isTruncated = nameWithoutExtension.length > maxNameLength;
  return {
    displayName: isTruncated ? `${nameWithoutExtension.slice(0, maxNameLength).trimEnd()}…` : nameWithoutExtension,
    extension,
    isTruncated,
  };
}

function parseUploadDate(value: string): Date {
  const hasTimezone = value.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(value);
  return new Date(hasTimezone ? value : value + 'Z');
}

export function filterContracts(contracts: AnalyzedContract[], filters: ContractFilters) {
  return contracts.filter(contract => {
    const contractDate = parseUploadDate(contract.uploadDate);
    const from = filters.dateFrom ? new Date(filters.dateFrom) : null;
    const to = filters.dateTo ? new Date(filters.dateTo) : null;
    contractDate.setHours(0, 0, 0, 0);
    from?.setHours(0, 0, 0, 0);
    to?.setHours(23, 59, 59, 999);
    return contract.filename.toLowerCase().includes(filters.searchTerm.toLowerCase())
      && (filters.status === 'all' || contract.status === filters.status)
      && (filters.riskLevel === 'all' || (contract.status === 'completed' && contract.riskLevel === filters.riskLevel))
      && (!from || contractDate >= from)
      && (!to || contractDate <= to);
  });
}

export function paginateContracts(contracts: AnalyzedContract[], page: number, pageSize = ITEMS_PER_PAGE) {
  return {
    contracts: contracts.slice((page - 1) * pageSize, page * pageSize),
    totalPages: Math.ceil(contracts.length / pageSize),
  };
}
