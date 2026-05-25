import {
    AgentDescriptor,
    AgentOutput,
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
export const API_ROOT = `${BASE_URL}/api/v1`;

const DEFAULT_TIMEOUT_MS = 30_000;

function getSplunkUser(): string | undefined {
    try {
        // eslint-disable-next-line global-require, @typescript-eslint/no-var-requires
        const cfg = require('@splunk/splunk-utils/config');
        if (cfg.isAvailable && cfg.username) {
            return cfg.username as string;
        }
    } catch {
        // Not running in Splunk Web — fall through.
    }
    return undefined;
}

export class ApiTimeoutError extends Error {
    constructor(ms: number) {
        super(`Request timed out after ${ms}ms`);
        this.name = 'ApiTimeoutError';
    }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const splunkUser = getSplunkUser();
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...init?.headers as Record<string, string>,
    };
    if (splunkUser) {
        headers['x-splunk-user'] = splunkUser;
    }
    try {
        const res = await fetch(`${API_ROOT}${path}`, {
            ...init,
            headers,
            signal: controller.signal,
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

export interface InvestigationStreamCallbacks {
    onAgentOrder: (order: string[]) => void;
    onAgentComplete: (agentId: string, output: AgentOutput) => void;
    onComplete: (status: string, completedAt?: string) => void;
    onError: (message: string) => void;
}

export function createInvestigationStream(
    id: string,
    callbacks: InvestigationStreamCallbacks,
): { close: () => void } {
    const url = `${API_ROOT}/investigations/${encodeURIComponent(id)}/stream`;
    const es = new EventSource(url);

    es.onmessage = (event: MessageEvent) => {
        let data: any;
        try {
            data = JSON.parse(event.data);
        } catch {
            return;
        }
        switch (data.type) {
            case 'agent_order':
                callbacks.onAgentOrder(data.agent_order);
                break;
            case 'agent_complete':
                callbacks.onAgentComplete(data.agent_id, data.output);
                break;
            case 'investigation_complete':
                callbacks.onComplete(data.status, data.completed_at);
                es.close();
                break;
            case 'error':
                callbacks.onError(data.message);
                es.close();
                break;
            default:
                break;
        }
    };

    es.onerror = () => {
        es.close();
        callbacks.onError('stream_failed');
    };

    return { close: () => es.close() };
}
