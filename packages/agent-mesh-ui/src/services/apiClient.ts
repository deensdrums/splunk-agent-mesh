import {
    AgentDescriptor,
    InvestigationRequest,
    InvestigationResult,
    InvestigationStartResponse,
    InvestigationStatus,
    LLMSettings,
    SaveSettingsRequest,
} from '../types';

const BASE_URL =
    (typeof window !== 'undefined' && (window as any).__AGENT_MESH_API_URL__) ||
    'http://localhost:8765';
const API_ROOT = `${BASE_URL}/api/v1`;

const DEFAULT_TIMEOUT_MS = 30_000;

export class ApiTimeoutError extends Error {
    constructor(ms: number) {
        super(`Request timed out after ${ms}ms`);
        this.name = 'ApiTimeoutError';
    }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(`${API_ROOT}${path}`, {
            headers: { 'Content-Type': 'application/json', ...init?.headers },
            signal: controller.signal,
            ...init,
        });
        if (!res.ok) {
            const text = await res.text().catch(() => res.statusText);
            throw new Error(`API ${res.status}: ${text}`);
        }
        return (await res.json()) as T;
    } catch (err) {
        if ((err as Error).name === 'AbortError') {
            throw new ApiTimeoutError(timeoutMs);
        }
        throw err;
    } finally {
        clearTimeout(timer);
    }
}

export const apiClient = {
    runInvestigation(req: InvestigationRequest): Promise<InvestigationResult> {
        // Investigation calls hit the LLM and can take a while.
        return request('/investigations/run', { method: 'POST', body: JSON.stringify(req) }, 120_000);
    },

    startInvestigation(req: InvestigationRequest): Promise<InvestigationStartResponse> {
        return request('/investigations/start', { method: 'POST', body: JSON.stringify(req) }, 30_000);
    },

    getInvestigationStatus(id: string): Promise<InvestigationStatus> {
        return request(`/investigations/${encodeURIComponent(id)}/status`, undefined, 10_000);
    },

    getInvestigation(id: string): Promise<InvestigationResult> {
        return request(`/investigations/${encodeURIComponent(id)}`, undefined, 30_000);
    },

    cancelInvestigation(id: string): Promise<{ id: string; status: InvestigationResult['status']; completed_at?: string }> {
        return request(`/investigations/${encodeURIComponent(id)}/cancel`, { method: 'POST', body: '{}' });
    },

    getAgents(): Promise<{ agents: AgentDescriptor[] }> {
        return request('/agents');
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
        return request('/health', undefined, 5_000);
    },
};
