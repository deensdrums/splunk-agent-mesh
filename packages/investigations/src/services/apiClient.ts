import { InvestigationRequest, InvestigationResult, LLMSettings, SaveSettingsRequest } from '../types';

const BASE_URL =
    (typeof window !== 'undefined' && (window as any).__SENTINEL_MESH_API_URL__) || 'http://localhost:8765';
const API_ROOT = `${BASE_URL}/api/v1`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${API_ROOT}${path}`, {
        headers: { 'Content-Type': 'application/json', ...init?.headers },
        ...init,
    });
    if (!res.ok) {
        const text = await res.text().catch(() => res.statusText);
        throw new Error(`API ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
}

export const apiClient = {
    runInvestigation(req: InvestigationRequest): Promise<InvestigationResult> {
        return request('/investigations/run', { method: 'POST', body: JSON.stringify(req) });
    },

    getSettings(): Promise<LLMSettings> {
        return request('/settings');
    },

    saveSettings(settings: SaveSettingsRequest): Promise<{ saved: boolean; api_key_configured: boolean }> {
        return request('/settings', { method: 'POST', body: JSON.stringify(settings) });
    },

    testConnection(): Promise<{ success: boolean; latency_ms?: number; model?: string; error?: string }> {
        return request('/settings/test', { method: 'POST', body: '{}' });
    },

    clearCredentials(): Promise<{ cleared: boolean }> {
        return request('/settings/credentials', { method: 'DELETE' });
    },

    healthCheck(): Promise<{ status: string }> {
        return request('/health');
    },
};
