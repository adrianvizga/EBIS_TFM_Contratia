import type { ClauseRelation } from '../../ClauseRelationsGraph';

export interface AnalyzedContract {
  id: string;
  filename: string;
  uploadDate: string;
  status: 'completed' | 'analyzing' | 'error' | 'pending' | 'failed';
  riskLevel: 'high' | 'medium' | 'low';
  riskCount: number;
  positiveCount: number;
  errorMessage?: string;
}

export interface Clause {
  id: string; number: string; title: string; technicalText: string; plainLanguage: string;
  recommendations?: string; category: 'risk' | 'positive' | 'neutral';
}

export interface ContractAnalysisData {
  filename: string; uploadDate: string; status: string; riskLevel: string;
  riskCount: number; positiveCount: number; negativeCount: number; missingCount: number;
  contractType?: string; coverageLevel?: string; coverageNotice?: string;
  legalSources?: string[]; pagesCount?: number;
  language?: string;
  clauses: Clause[];
  riskFindings: Array<{ title: string; severity: string }>;
  positiveFindings: Array<{ title: string }>;
  negativeFindings: Array<{ title: string }>;
  missingElements: Array<{ title: string; severity: string }>;
  relations: ClauseRelation[];
  evidence?: Array<{ citation: string; lawName?: string; articleNumber?: string; score?: number }>;
}

export interface ContractStreamEvent {
  contract_id: string;
  status: AnalyzedContract['status'];
  overall_risk?: AnalyzedContract['riskLevel'];
}
