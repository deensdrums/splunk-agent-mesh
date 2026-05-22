export type LLMProvider = 'anthropic' | 'openrouter' | 'openai_compatible';

// ===== New agent-mesh shape =====

export type AgentRunStatus = 'pending' | 'running' | 'completed' | 'error';

export interface AgentDescriptor {
    id: string;
    display_name: string;
    description: string;
    order: number;
    enabled: boolean;
}

export interface AgentOutput {
    agent_id: string;
    display_name: string;
    status: AgentRunStatus;
    markdown: string;
    model?: string;
    started_at?: string;
    completed_at?: string;
    error?: string | null;
}

export interface InvestigationResult {
    id: string;
    status: 'pending' | 'running' | 'complete' | 'error';
    started_at?: string;
    completed_at?: string;
    agent_order: string[];
    agents: Record<string, AgentOutput>;
}

export interface InvestigationRequest {
    description: string;
    host?: string;
    user?: string;
    alert_name?: string;
    time_range?: string;
    demo?: boolean;
}

export interface LLMSettings {
    provider: LLMProvider;
    base_url?: string;
    model: string;
    api_key_configured: boolean;
    storage_backend?: string;
}

export interface SaveSettingsRequest {
    provider: LLMProvider;
    base_url?: string;
    model: string;
    api_key?: string;
}

// ===== Legacy types — kept for archived components that will return as
// rich renderers when structured-output skills land. =====

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export interface MitreEntry {
    technique_id: string;
    name: string;
    confidence: number;
    evidence: string;
}

export interface TimelineEvent {
    time: string;
    title: string;
    description: string;
    source: 'endpoint' | 'dns' | 'auth' | 'proxy' | 'firewall';
    severity: Severity;
}

export interface EvidenceRecord {
    source: string;
    time: string;
    host: string;
    user: string;
    field: string;
    value: string;
    interpretation: string;
}

export interface ResponseAction {
    action: string;
    target: string;
    risk: string;
    requires_approval: boolean;
}

export interface DetectionRecommendationData {
    title: string;
    spl: string;
    description: string;
    severity: Severity;
    mitre: string[];
}

export interface AffectedEntities {
    users: string[];
    hosts: string[];
    domains: string[];
    ips: string[];
    files: string[];
}
