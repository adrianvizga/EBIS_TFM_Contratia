import { useState, useEffect, useCallback } from 'react';
import { useUser } from '../context/useUser';
import { useAuthFetch } from './useAuthFetch';
import { API_ORIGIN } from '../config/api';

export interface UsageData {
  plan: string;
  role: string;
  period_start: string;
  generation_reset_date: string | null;
  analysis_reset_date: string | null;
  contracts_generated: number;
  contracts_generated_limit: number | null;
  contracts_analyzed: number;
  contracts_analyzed_limit: number | null;
  ai_modifications: Record<string, number>;
  ai_modifications_per_contract_limit: number | null;
  agent_access: boolean;
}

const API_BASE = API_ORIGIN;

export function useUsage() {
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const { user, token } = useUser();
  const authFetch = useAuthFetch();

  const fetchUsage = useCallback(async () => {
    if (!token) return;
    try {
      const res = await authFetch(`${API_BASE}/api/usage`);
      if (res.ok) {
        const data = await res.json();
        setUsage(data);
      }
    } catch (e) {
      console.error('Error fetching usage:', e);
    } finally {
      setLoading(false);
    }
  }, [token, authFetch]);

  useEffect(() => {
    if (user && token) {
      fetchUsage();
    }
  }, [user, token, fetchUsage]);

  const refresh = useCallback(() => {
    fetchUsage();
  }, [fetchUsage]);

  const isAdmin = usage?.role === '0';

  const remainingGenerations = usage
    ? usage.contracts_generated_limit === null
      ? Infinity
      : Math.max(0, usage.contracts_generated_limit - usage.contracts_generated)
    : null;

  const remainingAnalyses = usage
    ? usage.contracts_analyzed_limit === null
      ? Infinity
      : Math.max(0, usage.contracts_analyzed_limit - usage.contracts_analyzed)
    : null;

  const getAiModsRemaining = (contractId: string): number | null => {
    if (!usage) return null;
    if (usage.ai_modifications_per_contract_limit === null) return Infinity;
    const used = usage.ai_modifications[contractId] || 0;
    return Math.max(0, usage.ai_modifications_per_contract_limit - used);
  };

  const getAiModsUsed = (contractId: string): number => {
    if (!usage) return 0;
    return usage.ai_modifications[contractId] || 0;
  };

  return {
    usage,
    loading,
    refresh,
    isAdmin,
    remainingGenerations,
    remainingAnalyses,
    getAiModsRemaining,
    getAiModsUsed,
  };
}
