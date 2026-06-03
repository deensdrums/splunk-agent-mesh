import React, { useCallback, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import Button from '@splunk/react-ui/Button';
import TextArea from '@splunk/react-ui/TextArea';
import Text from '@splunk/react-ui/Text';
import Message from '@splunk/react-ui/Message';
import { AgentDescriptor, Artifact, InvestigationRequest, InvestigationResult } from '../types';
import InvestigationReport from '../components/InvestigationReport';
import { apiClient, createInvestigationStream } from '../services/apiClient';
import { canPollSplunkWebResults, pollSplunkSearchResults } from '../services/splunkSearchResults';

export interface ConsoleChromeState {
    status: InvestigationResult['status'] | null;
    owner: string | null;
    id: string | null;
    isDemo: boolean;
    canClear: boolean;
    onClear: (() => void) | null;
}

interface Props {
    onConsoleChromeChange?: (state: ConsoleChromeState) => void;
}

const PageShell = styled.div`
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    width: 100%;
    box-sizing: border-box;
    overflow: hidden;
    padding: ${variables.spacingMedium};
`;

const FormCard = styled.div`
    background: ${variables.backgroundColorNavigation};
    border: none;
    border-left: 3px solid ${variables.accentColorL10};
    border-radius: 0;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
    box-sizing: border-box;
    padding: ${variables.spacingLarge};
    margin-bottom: ${variables.spacingSmall};
    flex: 0 0 auto;
    width: 100%;
`;

const FormCardCollapsed = styled(FormCard)`
    padding: ${variables.spacingSmall} ${variables.spacingMedium};
`;

const FormSummary = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall} ${variables.spacingMedium};
    flex-wrap: wrap;
`;

const FormSummaryText = styled.div`
    flex: 1 1 320px;
    min-width: 0;
    color: ${variables.contentColorDefault};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
`;

const FormSummaryMeta = styled.div`
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
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
    flex: 0 0 auto;
    margin-bottom: ${variables.spacingSmall};
`;

const ReportRegion = styled.div`
    display: flex;
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
`;

const DEMO_FORM: InvestigationRequest = {
    description:
        'IDS flagged JNDI (jndi:ldap) lookup strings hitting public web servers web-prod-04 and web-prod-07. Possible Log4Shell exploitation.',
    host: 'web-prod-04',
    alert_name: 'Log4Shell Exploitation Attempt',
    time_range: '-4h',
    demo: true,
};

export function upsertArtifacts(current: Artifact[], updates: Artifact[]): Artifact[] {
    const byId = new Map(current.map((artifact) => [artifact.id, artifact]));
    updates.forEach((artifact) => {
        const previous = byId.get(artifact.id);
        if (previous && artifact.sid && artifact.sid !== 'demo' && artifact.rows.length === 0) {
            byId.set(artifact.id, {
                ...artifact,
                fields: previous.fields,
                rows: previous.rows,
                messages: previous.messages,
                browser_results_error: previous.browser_results_error,
            });
        } else {
            byId.set(artifact.id, artifact);
        }
    });
    return Array.from(byId.values());
}

const InvestigationPage: React.FC<Props> = ({ onConsoleChromeChange }) => {
    const [description, setDescription] = useState('');
    const [host, setHost] = useState('');
    const [user, setUser] = useState('');
    const [alertName, setAlertName] = useState('');
    const [timeRange, setTimeRange] = useState('-24h');
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState<InvestigationResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [descriptors, setDescriptors] = useState<AgentDescriptor[]>([]);
    const [inputsExpanded, setInputsExpanded] = useState(true);
    const [isDemo, setIsDemo] = useState(false);
    const streamRef = useRef<{ close: () => void } | null>(null);
    const searchPollersRef = useRef<Map<string, { close: () => void }>>(new Map());

    useEffect(() => {
        const searchPollers = searchPollersRef.current;
        apiClient
            .getAgents()
            .then((res) => setDescriptors(res.agents))
            .catch(() => {});
        return () => {
            streamRef.current?.close();
            searchPollers.forEach((poller) => poller.close());
            searchPollers.clear();
        };
    }, []);

    useEffect(() => {
        if (!canPollSplunkWebResults) {return;}
        (result?.artifacts || []).forEach((artifact) => {
            if (
                !artifact.sid
                || artifact.sid === 'demo'
                || artifact.status === 'error'
                || (artifact.status === 'done' && artifact.rows.length > 0)
                || searchPollersRef.current.has(artifact.id)
            ) {return;}
            const poller = pollSplunkSearchResults(
                artifact,
                (update) => {
                    setResult((prev) => prev ? {
                        ...prev,
                        artifacts: upsertArtifacts(prev.artifacts || [], [update]),
                    } : prev);
                },
                (message) => {
                    setResult((prev) => {
                        if (!prev) {return prev;}
                        const existing = (prev.artifacts || []).find((item) => item.id === artifact.id);
                        return existing ? {
                            ...prev,
                            artifacts: upsertArtifacts(prev.artifacts || [], [{
                                ...existing,
                                browser_results_error: message,
                            }]),
                        } : prev;
                    });
                },
            );
            searchPollersRef.current.set(artifact.id, poller);
        });
    }, [result?.artifacts]);

    const loadDemoForm = () => {
        setDescription(DEMO_FORM.description!);
        setHost(DEMO_FORM.host || '');
        setUser(DEMO_FORM.user || '');
        setAlertName(DEMO_FORM.alert_name || '');
        setTimeRange(DEMO_FORM.time_range || '-4h');
    };

    const pollInvestigation = async (id: string): Promise<InvestigationResult> => {
        const deadline = Date.now() + 120_000;
        while (Date.now() < deadline) {
            // eslint-disable-next-line no-await-in-loop
            const current = await apiClient.getInvestigation(id);
            setResult((prev) => ({
                ...current,
                artifacts: upsertArtifacts(prev?.artifacts || [], current.artifacts || []),
            }));
            if (current.status !== 'running' && current.status !== 'pending') {
                return current;
            }
            // eslint-disable-next-line no-await-in-loop
            await new Promise((resolve) => {
                setTimeout(resolve, 1500);
            });
        }
        throw new Error('Investigation timed out while waiting for results.');
    };

    const streamInvestigation = useCallback(
        (id: string, streamToken: string): Promise<void> =>
            new Promise((resolve, reject) => {
                const stream = createInvestigationStream(id, streamToken, {
                    onAgentOrder: (order) => {
                        setResult((prev) => (prev ? { ...prev, agent_order: order } : prev));
                        if (descriptors.length === 0 && order.length > 0) {
                            setDescriptors(
                                order.map((agentId) => ({
                                    id: agentId,
                                    display_name: agentId,
                                    description: '',
                                    order: 0,
                                    enabled: true,
                                }))
                            );
                        }
                    },
                    onAgentComplete: (agentId, output, artifacts) => {
                        setResult((prev) => {
                            if (!prev) {return prev;}
                            return {
                                ...prev,
                                agents: { ...prev.agents, [agentId]: output },
                                artifacts: upsertArtifacts(prev.artifacts || [], artifacts),
                            };
                        });
                        setDescriptors((prev) => {
                            const existing = prev.find((d) => d.id === agentId);
                            if (existing && existing.display_name === agentId && output.display_name) {
                                return prev.map((d) =>
                                    d.id === agentId ? { ...d, display_name: output.display_name } : d
                                );
                            }
                            return prev;
                        });
                    },
                    onAgentUpdate: (agentId, output, artifacts) => {
                        setResult((prev) => {
                            if (!prev) {return prev;}
                            return {
                                ...prev,
                                agents: { ...prev.agents, [agentId]: output },
                                artifacts: upsertArtifacts(prev.artifacts || [], artifacts),
                            };
                        });
                    },
                    onComplete: (status, completedAt) => {
                        streamRef.current = null;
                        apiClient
                            .getInvestigation(id)
                            .then((full) => {
                                setResult((prev) => ({
                                    ...full,
                                    artifacts: upsertArtifacts(prev?.artifacts || [], full.artifacts || []),
                                }));
                                resolve();
                            })
                            .catch(() => {
                                setResult((prev) =>
                                    prev
                                        ? { ...prev, status: status as InvestigationResult['status'], completed_at: completedAt }
                                        : prev
                                );
                                resolve();
                            });
                    },
                    onError: (message) => {
                        streamRef.current = null;
                        if (message === 'stream_failed') {
                            reject(new Error(message));
                        } else {
                            setError(message);
                            resolve();
                        }
                    },
                });
                streamRef.current = stream;
            }),
        [descriptors.length]
    );

    const runInvestigation = async (demoRun: boolean, override?: InvestigationRequest) => {
        setRunning(true);
        setIsDemo(demoRun);
        setError(null);
        setResult(null);
        setInputsExpanded(false);
        streamRef.current?.close();
        searchPollersRef.current.forEach((poller) => poller.close());
        searchPollersRef.current.clear();

        try {
            const req: InvestigationRequest =
                override || {
                    description,
                    host: host || undefined,
                    user: user || undefined,
                    alert_name: alertName || undefined,
                    time_range: timeRange || undefined,
                    demo: demoRun,
                };
            // Demo and live both go through /start + SSE — demo is a paced backend
            // replay, so it exercises the same path (no separate frontend fixture).
            const start = await apiClient.startInvestigation(req);
            setResult({
                id: start.id,
                status: 'running',
                owner: start.owner,
                started_at: start.started_at,
                agent_order: [],
                agents: {},
            });

            try {
                await streamInvestigation(start.id, start.stream_token);
            } catch {
                await pollInvestigation(start.id);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Investigation failed. Check backend connection.');
        } finally {
            setRunning(false);
        }
    };

    const clearInvestigation = useCallback(() => {
        streamRef.current?.close();
        searchPollersRef.current.forEach((poller) => poller.close());
        searchPollersRef.current.clear();
        setResult(null);
        setError(null);
        setIsDemo(false);
        setInputsExpanded(true);
    }, []);

    useEffect(() => {
        onConsoleChromeChange?.({
            status: result?.status ?? (running ? 'running' : null),
            owner: result?.owner ?? null,
            id: result?.id ?? null,
            isDemo,
            canClear: Boolean(result || running),
            onClear: result || running ? clearInvestigation : null,
        });
    }, [clearInvestigation, isDemo, onConsoleChromeChange, result, running]);

    const summaryMeta = [
        host && `Host ${host}`,
        user && `User ${user}`,
        alertName && `Alert ${alertName}`,
        timeRange && `Range ${timeRange}`,
    ].filter(Boolean).join(' · ');

    return (
        <PageShell>
            {inputsExpanded ? (
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
                                onChange={(_e: unknown, { value }: { value: string }) => setHost(value)}
                                placeholder="FIN-LAPTOP-22"
                            />
                        </FieldGroup>
                        <FieldGroup>
                            <FieldLabel>User</FieldLabel>
                            <Text
                                value={user}
                                onChange={(_e: unknown, { value }: { value: string }) => setUser(value)}
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
                            label="Run Demo Investigation"
                            appearance="secondary"
                            disabled={running}
                            onClick={() => {
                                loadDemoForm();
                                setTimeout(() => runInvestigation(true, DEMO_FORM), 50);
                            }}
                        />
                        {(result || running) && (
                            <Button
                                label="Hide Inputs"
                                appearance="subtle"
                                onClick={() => setInputsExpanded(false)}
                            />
                        )}
                    </ButtonRow>
                </FormCard>
            ) : (
                <FormCardCollapsed>
                    <FormSummary>
                        <FormSummaryText title={description}>{description || 'Investigation inputs'}</FormSummaryText>
                        {summaryMeta && <FormSummaryMeta>{summaryMeta}</FormSummaryMeta>}
                        <Button
                            label="Edit Inputs"
                            appearance="subtle"
                            onClick={() => setInputsExpanded(true)}
                        />
                    </FormSummary>
                </FormCardCollapsed>
            )}

            {error && (
                <SectionGap>
                    <Message type="error" appearance="fill">
                        {error}
                    </Message>
                </SectionGap>
            )}

            <ReportRegion>
                <InvestigationReport
                    descriptors={descriptors}
                    result={result}
                    running={running}
                />
            </ReportRegion>
        </PageShell>
    );
};

export default InvestigationPage;
