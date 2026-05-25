export type LLMProvider = 'anthropic' | 'openrouter' | 'openai_compatible';

// ===== New agent-mesh shape =====

export type AgentRunStatus = 'pending' | 'running' | 'completed' | 'error' | 'cancelled';
export type VisualizationKind = 'table' | 'timechart' | 'bar' | 'single' | 'line' | 'pie';

export interface AgentDescriptor {
    id: string;
    display_name: string;
    description: string;
    order: number;
    enabled: boolean;
    skills?: string[];
    depends_on?: string[];
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
    artifacts?: string[];
}

export interface InvestigationSection {
    id: string;
    type: 'markdown';
    title: string;
    agent_id?: string | null;
    markdown: string;
}

export interface VisualizationSpec {
    kind: VisualizationKind;
    reason: string;
}

export interface SearchArtifact {
    id: string;
    type: 'splunk_search';
    agent_id: string;
    title: string;
    spl: string;
    earliest: string;
    latest: string;
    sid?: string | null;
    status: 'pending' | 'running' | 'done' | 'error';
    fields: string[];
    rows: Record<string, unknown>[];
    messages?: string[];
    error?: string | null;
    started_at?: string;
    completed_at?: string | null;
    visualization: VisualizationSpec;
}

export type Artifact = SearchArtifact;

export interface AuditEvent {
    type: string;
    investigation_id: string;
    username: string;
    status: string;
    timestamp: string;
    details?: Record<string, unknown>;
}

export interface InvestigationResult {
    id: string;
    owner?: string;
    status: 'pending' | 'running' | 'complete' | 'error' | 'cancelled';
    started_at?: string;
    completed_at?: string;
    agent_order: string[];
    agents: Record<string, AgentOutput>;
    sections?: InvestigationSection[];
    artifacts?: Artifact[];
    audit?: AuditEvent[];
    error?: string | null;
}

export interface InvestigationRequest {
    description: string;
    host?: string;
    user?: string;
    alert_name?: string;
    time_range?: string;
    demo?: boolean;
}

export interface InvestigationStartResponse {
    id: string;
    status: InvestigationResult['status'];
    owner?: string;
    started_at?: string;
}

export interface InvestigationStatus {
    id: string;
    owner?: string;
    status: InvestigationResult['status'];
    started_at?: string;
    completed_at?: string | null;
    agent_order: string[];
    agents: Record<string, Pick<AgentOutput, 'agent_id' | 'display_name' | 'status' | 'started_at' | 'completed_at' | 'error'>>;
    artifact_count: number;
    error?: string | null;
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

// ===== SSE event types =====

export interface SSEAgentOrderEvent {
    type: 'agent_order';
    agent_order: string[];
}

export interface SSEAgentCompleteEvent {
    type: 'agent_complete';
    agent_id: string;
    output: AgentOutput;
}

export interface SSEInvestigationCompleteEvent {
    type: 'investigation_complete';
    status: string;
    completed_at?: string;
}

export interface SSEErrorEvent {
    type: 'error';
    message: string;
}

export type InvestigationSSEEvent =
    | SSEAgentOrderEvent
    | SSEAgentCompleteEvent
    | SSEInvestigationCompleteEvent
    | SSEErrorEvent;

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
