import { useState, useEffect } from 'react';
import { generatedContractsService, type ContractTypeCoverage } from '../services/generatedContracts';

let cache: ContractTypeCoverage[] | null = null;
let fetchPromise: Promise<ContractTypeCoverage[]> | null = null;

export function useContractTypes() {
  const [contractTypes, setContractTypes] = useState<ContractTypeCoverage[]>(cache ?? []);

  useEffect(() => {
    if (cache) return;

    if (!fetchPromise) {
      fetchPromise = generatedContractsService.getContractTypes().catch(() => []);
    }

    fetchPromise.then((types) => {
      cache = types;
      setContractTypes(types);
    });
  }, []);

  const getLabel = (id: string): string =>
    contractTypes.find((t) => t.id === id)?.label ?? id;

  return { contractTypes, getLabel };
}
