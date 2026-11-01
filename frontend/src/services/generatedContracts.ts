
import { API_ORIGIN } from '../config/api';
import { getAccessToken } from './authTokenStore';

const API_URL = API_ORIGIN;

export interface GeneratedContract {
    id: string;
    title: string;
    contract_type: string;
    country: string;
    language: string;
    tone: string;
    status: string;
    current_content: string;
    error_message?: string | null;
    generation_prompt_version?: string | null;
    model_name?: string | null;
    contract_details?: GeneratedContractDetails;
    created_at: string;
    updated_at: string;
}

export interface GeneratedContractDetails {
    parties?: {
        partyA?: string;
        partyB?: string;
    };
    description?: string;
    [key: string]: unknown;
}

export interface CreateGeneratedContractPayload {
    title: string;
    contract_type: string;
    country?: string;
    language?: string;
    tone?: string;
    description?: string;
    contract_details?: GeneratedContractDetails;
}

export interface ContractTypeCoverage {
    id: string;
    label: string;
    enabled: boolean;
    coverage_level: 'full' | 'partial' | 'full_general';
    legal_sources: string[];
    coverage_notice: string;
}

export interface ContractVersion {
    id: string;
    version_number: number;
    content: string;
    change_type: string;
    change_description?: string;
    created_at: string;
}

export const generatedContractsService = {
    async getContractTypes(): Promise<ContractTypeCoverage[]> {
        const response = await fetch(`${API_URL}/api/contract-types`);
        if (!response.ok) throw new Error('Failed to fetch contract types');
        return response.json();
    },
    async getAll(): Promise<GeneratedContract[]> {
        const token = getAccessToken();
        const response = await fetch(`${API_URL}/api/generated-contracts`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) throw new Error('Failed to fetch contracts');
        return response.json();
    },

    async getById(id: string): Promise<GeneratedContract> {
        const token = getAccessToken();
        const response = await fetch(`${API_URL}/api/generated-contracts/${id}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) throw new Error('Failed to fetch contract');
        return response.json();
    },

    async create(data: CreateGeneratedContractPayload): Promise<GeneratedContract> {
        const token = getAccessToken();
        const response = await fetch(`${API_URL}/api/generated-contracts`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const errorBody = await response.json().catch(() => null);
            const detail = errorBody?.detail || 'Failed to create contract';
            throw new Error(detail);
        }
        return response.json();
    },

    async update(id: string, content: string, changeType: string, changeDescription?: string): Promise<GeneratedContract> {
        const token = getAccessToken();
        const response = await fetch(`${API_URL}/api/generated-contracts/${id}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content, change_type: changeType, change_description: changeDescription })
        });
        if (!response.ok) {
            const errorBody = await response.text();
            throw new Error(`Failed to update contract: ${response.status} - ${errorBody}`);
        }
        return response.json();
    },

    async getVersions(id: string): Promise<ContractVersion[]> {
        const token = getAccessToken();
        const response = await fetch(`${API_URL}/api/generated-contracts/${id}/versions`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) throw new Error('Failed to fetch versions');
        return response.json();
    },

    async delete(id: string): Promise<void> {
        const token = getAccessToken();
        const response = await fetch(`${API_URL}/api/generated-contracts/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) throw new Error('Failed to delete contract');
    },

    async sendToAnalysis(id: string): Promise<{ id: string; filename: string; status: string; message: string }> {
        const token = getAccessToken();
        const response = await fetch(`${API_URL}/api/generated-contracts/${id}/send-to-analysis`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) throw new Error('Failed to send contract to analysis');
        return response.json();
    },

    async generateModification(id: string, prompt: string): Promise<GeneratedContract> {
        const token = getAccessToken();
        const response = await fetch(`${API_URL}/api/generated-contracts/${id}/generate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt })
        });
        if (!response.ok) {
            const errorBody = await response.json().catch(() => null);
            const detail = errorBody?.detail || `Error ${response.status}`;
            throw new Error(detail);
        }
        return response.json();
    },

    async retry(id: string): Promise<GeneratedContract> {
        const token = getAccessToken();
        const response = await fetch(`${API_URL}/api/generated-contracts/${id}/retry`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            const body = await response.json().catch(() => null);
            throw new Error(body?.detail || 'No se pudo reintentar la generación');
        }
        return response.json();
    }
};
