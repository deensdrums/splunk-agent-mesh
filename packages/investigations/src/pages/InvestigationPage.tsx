import React, { useState, useRef } from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import Button from '@splunk/react-ui/Button';
import TextArea from '@splunk/react-ui/TextArea';
import Text from '@splunk/react-ui/Text';
import ColumnLayout from '@splunk/react-ui/ColumnLayout';
import Message from '@splunk/react-ui/Message';
import { AgentStep, InvestigationResult, InvestigationRequest } from '../types';
import AgentRunPanel from '../components/AgentRunPanel';
import InvestigationSummary from '../components/InvestigationSummary';
import IncidentTimeline from '../components/IncidentTimeline';
import EvidenceTable from '../components/EvidenceTable';
import EntityGraphPlaceholder from '../components/EntityGraphPlaceholder';
import DetectionRecommendation from '../components/DetectionRecommendation';
import ResponsePlan from '../components/ResponsePlan';
import { apiClient } from '../services/apiClient';
import { DEMO_AGENT_STEPS, DEMO_RESULT } from '../demo/demoData';

const FormCard = styled.div`
    background: ${variables.backgroundColorNavigation};
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    padding: ${variables.spacingLarge};
    margin-bottom: ${variables.spacingMedium};
`;

const FieldRow = styled.div`
    display: flex;
    gap: ${variables.spacingMedium};
    margin-top: ${variables.spacingMedium};
    flex-wrap: wrap;
    align-items: flex-end;
`;

const FieldGroup = styled.div`
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    min-width: 140px;
`;

const FieldLabel = styled.label`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    font-weight: ${variables.fontWeightSemiBold};
`;

const ButtonRow = styled.div`
    display: flex;
    gap: ${variables.spacingSmall};
    margin-top: ${variables.spacingMedium};
    flex-wrap: wrap;
`;

const SectionGap = styled.div`
    margin-bottom: ${variables.spacingMedium};
`;

const DEMO_FORM: InvestigationRequest = {
    description:
        'winword.exe spawned powershell.exe with an encoded command on FIN-LAPTOP-22. User jsmith. Possible data exfiltration to external IP.',
    host: 'FIN-LAPTOP-22',
    user: 'jsmith',
    alert_name: 'Office Spawns Encoded PowerShell',
    time_range: '-4h',
    demo: true,
};

const INITIAL_STEPS: AgentStep[] = [
    { name: 'triage', label: 'Triage Agent', status: 'pending' },
    { name: 'spl_hunter', label: 'SPL Hunter Agent', status: 'pending' },
    { name: 'timeline', label: 'Timeline Agent', status: 'pending' },
    { name: 'blast_radius', label: 'Blast Radius Agent', status: 'pending' },
    { name: 'detection_gap', label: 'Detection Gap Agent', status: 'pending' },
    { name: 'response', label: 'Response Agent', status: 'pending' },
    { name: 'executive_brief', label: 'Executive Brief', status: 'pending' },
];

function delay(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

const InvestigationPage: React.FC = () => {
    const [description, setDescription] = useState('');
    const [host, setHost] = useState('');
    const [user, setUser] = useState('');
    const [alertName, setAlertName] = useState('');
    const [timeRange, setTimeRange] = useState('-24h');
    const [running, setRunning] = useState(false);
    const [agentSteps, setAgentSteps] = useState<AgentStep[]>(INITIAL_STEPS);
    const [result, setResult] = useState<InvestigationResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [showAgents, setShowAgents] = useState(false);
    const resultRef = useRef<HTMLDivElement>(null);

    const loadDemo = () => {
        setDescription(DEMO_FORM.description!);
        setHost(DEMO_FORM.host || '');
        setUser(DEMO_FORM.user || '');
        setAlertName(DEMO_FORM.alert_name || '');
        setTimeRange(DEMO_FORM.time_range || '-4h');
    };

    const animateDemoSteps = async (steps: AgentStep[]) => {
        for (let i = 0; i < steps.length; i++) {
            setAgentSteps((prev) =>
                prev.map((s, idx) => (idx === i ? { ...s, status: 'running' } : s))
            );
            await delay(400);
            setAgentSteps((prev) =>
                prev.map((s, idx) => (idx === i ? { ...steps[i], status: 'complete' } : s))
            );
        }
    };

    const runInvestigation = async (isDemo: boolean) => {
        setRunning(true);
        setError(null);
        setResult(null);
        setShowAgents(true);
        setAgentSteps(INITIAL_STEPS);

        try {
            const req: InvestigationRequest = {
                description,
                host: host || undefined,
                user: user || undefined,
                alert_name: alertName || undefined,
                time_range: timeRange || undefined,
                demo: isDemo,
            };

            if (isDemo) {
                await animateDemoSteps(DEMO_AGENT_STEPS);
                setResult(DEMO_RESULT);
            } else {
                const investigationResult = await apiClient.runInvestigation(req);
                setResult(investigationResult);
            }

            setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Investigation failed. Check backend connection.');
            setAgentSteps((prev) => prev.map((s) => (s.status === 'running' ? { ...s, status: 'error' } : s)));
        } finally {
            setRunning(false);
        }
    };

    return (
        <div>
            <FormCard>
                <FieldGroup>
                    <FieldLabel>Describe what to investigate</FieldLabel>
                    <TextArea
                        value={description}
                        onChange={(_e: unknown, { value }: { value: string }) => setDescription(value)}
                        rowsMin={3}
                        rowsMax={6}
                    />
                </FieldGroup>
                <FieldRow>
                    <FieldGroup>
                        <FieldLabel>Host</FieldLabel>
                        <Text
                            value={host}
                            onChange={(_e: unknown, { value }: { value: string }) =>
                                setHost(value)
                            }
                            placeholder="FIN-LAPTOP-22"
                        />
                    </FieldGroup>
                    <FieldGroup>
                        <FieldLabel>User</FieldLabel>
                        <Text
                            value={user}
                            onChange={(_e: unknown, { value }: { value: string }) =>
                                setUser(value)
                            }
                            placeholder="jsmith"
                        />
                    </FieldGroup>
                    <FieldGroup>
                        <FieldLabel>Alert Name</FieldLabel>
                        <Text
                            value={alertName}
                            onChange={(_e: unknown, { value }: { value: string }) =>
                                setAlertName(value)
                            }
                            placeholder="Office Spawns PowerShell"
                        />
                    </FieldGroup>
                    <FieldGroup>
                        <FieldLabel>Time Range</FieldLabel>
                        <Text
                            value={timeRange}
                            onChange={(_e: unknown, { value }: { value: string }) =>
                                setTimeRange(value)
                            }
                            placeholder="-24h"
                        />
                    </FieldGroup>
                </FieldRow>
                <ButtonRow>
                    <Button
                        label="Start Investigation"
                        appearance="primary"
                        disabled={running || !description.trim()}
                        onClick={() => runInvestigation(false)}
                    />
                    <Button
                        label="Load Suspicious PowerShell Demo"
                        appearance="secondary"
                        disabled={running}
                        onClick={() => {
                            loadDemo();
                            setTimeout(() => runInvestigation(true), 50);
                        }}
                    />
                    {result && (
                        <Button
                            label="Clear"
                            appearance="secondary"
                            onClick={() => {
                                setResult(null);
                                setShowAgents(false);
                                setAgentSteps(INITIAL_STEPS);
                                setError(null);
                            }}
                        />
                    )}
                </ButtonRow>
            </FormCard>

            {error && (
                <SectionGap>
                    <Message type="error" appearance="fill">
                        {error}
                    </Message>
                </SectionGap>
            )}

            {showAgents && (
                <SectionGap>
                    <ColumnLayout>
                        <ColumnLayout.Row>
                            <ColumnLayout.Column span={4}>
                                <AgentRunPanel steps={agentSteps} />
                            </ColumnLayout.Column>
                            <ColumnLayout.Column span={8}>
                                {result && <InvestigationSummary result={result} />}
                            </ColumnLayout.Column>
                        </ColumnLayout.Row>
                    </ColumnLayout>
                </SectionGap>
            )}

            {result && (
                <div ref={resultRef}>
                    <SectionGap>
                        <IncidentTimeline events={result.timeline} />
                    </SectionGap>

                    <SectionGap>
                        <ColumnLayout>
                            <ColumnLayout.Row>
                                <ColumnLayout.Column span={7}>
                                    <EvidenceTable evidence={result.evidence} />
                                </ColumnLayout.Column>
                                <ColumnLayout.Column span={5}>
                                    <EntityGraphPlaceholder entities={result.affected_entities} />
                                </ColumnLayout.Column>
                            </ColumnLayout.Row>
                        </ColumnLayout>
                    </SectionGap>

                    <SectionGap>
                        <ColumnLayout>
                            <ColumnLayout.Row>
                                <ColumnLayout.Column span={6}>
                                    <ResponsePlan actions={result.response_plan} />
                                </ColumnLayout.Column>
                                <ColumnLayout.Column span={6}>
                                    <DetectionRecommendation data={result.detection_recommendation} />
                                </ColumnLayout.Column>
                            </ColumnLayout.Row>
                        </ColumnLayout>
                    </SectionGap>
                </div>
            )}
        </div>
    );
};

export default InvestigationPage;
