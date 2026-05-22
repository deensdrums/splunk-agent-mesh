export type Severity = 'low' | 'medium' | 'high' | 'critical';
export type InvestigationStatus = 'idle' | 'running' | 'complete' | 'error';
export type LLMProvider = 'anthropic' | 'openrouter' | 'openai_compatible';
export type AgentName =
    | 'triage'
    | 'spl_hunter'
    | 'timeline'
    | 'blast_radius'
    | 'detection_gap'
    | 'response'
    | 'executive_brief';
export type AgentStatus = 'pending' | 'running' | 'complete' | 'error';

export interface AgentStep {
    name: AgentName;
    label: string;
    status: AgentStatus;
    message?: string;
}

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

export interface InvestigationResult {
    id: string;
    status: 'complete' | 'error';
    title: string;
    severity: 'Low' | 'Medium' | 'High' | 'Critical';
    confidence: number;
    summary: string;
    affected_entities: AffectedEntities;
    mitre: MitreEntry[];
    timeline: TimelineEvent[];
    evidence: EvidenceRecord[];
    response_plan: ResponseAction[];
    detection_recommendation: DetectionRecommendationData;
    agent_errors?: string[];
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
}

export interface SaveSettingsRequest {
    provider: LLMProvider;
    base_url?: string;
    model: string;
    api_key?: string;
}
