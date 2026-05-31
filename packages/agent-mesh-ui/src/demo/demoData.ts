import { AgentEvent, Artifact, InvestigationResult } from '../types';

const DEMO_TIMESTAMP = '2026-05-21T18:00:00+00:00';

const DEMO_EVENTS: AgentEvent[] = [
    {
        type: 'narration',
        title: 'Starting investigation',
        text:
            'winword.exe spawning encoded PowerShell on a finance laptop is a classic post-exploitation signal. ' +
            "I'll confirm the execution, then bound the blast radius.",
        payload: {},
    },
    {
        type: 'splunk_search',
        title: 'Encoded PowerShell spawned by Office',
        text: 'Looking for powershell.exe launched with an encoded command on FIN-LAPTOP-22.',
        payload: {
            query:
                'index=endpoint host=FIN-LAPTOP-22 process_name=powershell.exe ' +
                '("-enc" OR "-EncodedCommand") | timechart span=1m count',
            purpose: 'Confirm encoded PowerShell execution and its timing.',
            type: 'timechart',
        },
    },
    {
        type: 'result_summary',
        title: 'Encoded PowerShell confirmed',
        text:
            'Six encoded-PowerShell executions clustered between 14:02 and 14:05, all parented by winword.exe. ' +
            'This matches scripted execution, not interactive use.',
        payload: {},
    },
    {
        type: 'finding',
        title: 'Office-spawned encoded PowerShell',
        text: 'winword.exe spawned powershell.exe -EncodedCommand on FIN-LAPTOP-22 for user jsmith.',
        payload: {
            host: 'FIN-LAPTOP-22',
            user: 'jsmith',
            parent_process: 'winword.exe',
            technique: 'T1059.001',
            confidence: 'high',
        },
    },
    {
        type: 'handoff',
        title: 'Reporting agent requested',
        text: 'Asking the reporting agent to turn these findings into a leadership-ready brief.',
        payload: { sub_agent: 'executive_brief', task: 'summarize_findings' },
    },
    {
        type: 'result_summary',
        title: 'Report drafted',
        text:
            'The reporting agent rated this High severity (confidence 0.87) and mapped it to T1059.001, T1027, ' +
            'and T1041, recommending host isolation and a credential reset for jsmith.',
        payload: {},
    },
    {
        type: 'final',
        title: 'Investigation complete',
        text:
            'FIN-LAPTOP-22 ran encoded PowerShell spawned by Office under jsmith, consistent with initial access ' +
            'followed by C2 setup. Recommend isolating the host and resetting credentials.',
        payload: {
            summary: 'Likely account compromise via malicious Office document on FIN-LAPTOP-22.',
            recommended_actions: [
                'Isolate FIN-LAPTOP-22 from the network',
                'Disable jsmith and force a password reset',
                'Block the external C2 domain and IP',
                "Review file-server access made with jsmith's credentials",
            ],
        },
    },
];

const DEMO_ARTIFACT: Artifact = {
    id: 'artifact-demo000000001',
    type: 'splunk_search',
    agent_id: 'spl_hunter',
    title: 'Encoded PowerShell spawned by Office',
    spl:
        'index=endpoint host=FIN-LAPTOP-22 process_name=powershell.exe ("-enc" OR "-EncodedCommand")\n' +
        '| timechart span=1m count',
    earliest: '-4h',
    latest: 'now',
    sid: 'demo-sid-0001',
    status: 'done',
    fields: ['_time', 'count'],
    rows: [
        { _time: '2026-05-21T14:02:00+00:00', count: '3' },
        { _time: '2026-05-21T14:03:00+00:00', count: '1' },
        { _time: '2026-05-21T14:05:00+00:00', count: '2' },
    ],
    messages: [],
    error: null,
    started_at: DEMO_TIMESTAMP,
    completed_at: DEMO_TIMESTAMP,
    visualization: { kind: 'timechart', reason: 'SPL uses timechart.' },
};

export const DEMO_RESULT: InvestigationResult = {
    id: 'demo-investigation-001',
    status: 'complete',
    started_at: DEMO_TIMESTAMP,
    completed_at: DEMO_TIMESTAMP,
    agent_order: ['spl_hunter'],
    agents: {
        spl_hunter: {
            agent_id: 'spl_hunter',
            display_name: 'Threat Hunter',
            status: 'completed',
            events: DEMO_EVENTS,
            markdown: '',
            model: 'claude-sonnet-4-6',
            started_at: DEMO_TIMESTAMP,
            completed_at: DEMO_TIMESTAMP,
            error: null,
            artifacts: [DEMO_ARTIFACT.id],
        },
    },
    artifacts: [DEMO_ARTIFACT],
};
