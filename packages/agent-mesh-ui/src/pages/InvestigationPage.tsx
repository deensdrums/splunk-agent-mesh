import React, { useCallback, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import Button from '@splunk/react-ui/Button';
import TextArea from '@splunk/react-ui/TextArea';
import Text from '@splunk/react-ui/Text';
import Message from '@splunk/react-ui/Message';
import { AgentDescriptor, InvestigationRequest, InvestigationResult } from '../types';
import InvestigationReport from '../components/InvestigationReport';
import { apiClient, createInvestigationStream } from '../services/apiClient';
import { DEMO_RESULT } from '../demo/demoData';

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

const InvestigationPage: React.FC = () => {
    const [description, setDescription] = useState('');
    const [host, setHost] = useState('');
    const [user, setUser] = useState('');
    const [alertName, setAlertName] = useState('');
    const [timeRange, setTimeRange] = useState('-24h');
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState<InvestigationResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [descriptors, setDescriptors] = useState<AgentDescriptor[]>([]);
    const streamRef = useRef<{ close: () => void } | null>(null);

    useEffect(() => {
        apiClient
            .getAgents()
            .then((res) => setDescriptors(res.agents))
            .catch(() => {});
        return () => {
            streamRef.current?.close();
        };
    }, []);

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
            setResult(current);
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
        (id: string): Promise<void> =>
            new Promise((resolve, reject) => {
                const stream = createInvestigationStream(id, {
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
                    onAgentComplete: (agentId, output) => {
                        setResult((prev) => {
                            if (!prev) return prev;
                            const updated = {
                                ...prev,
                                agents: { ...prev.agents, [agentId]: output },
                            };
                            return updated;
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
                    onComplete: (status, completedAt) => {
                        streamRef.current = null;
                        apiClient
                            .getInvestigation(id)
                            .then((full) => {
                                setResult(full);
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

    const runInvestigation = async (isDemo: boolean, override?: InvestigationRequest) => {
        setRunning(true);
        setError(null);
        setResult(null);
        streamRef.current?.close();

        try {
            const req: InvestigationRequest =
                override || {
                    description,
                    host: host || undefined,
                    user: user || undefined,
                    alert_name: alertName || undefined,
                    time_range: timeRange || undefined,
                    demo: isDemo,
                };
            const start = await apiClient.startInvestigation(req).catch((startErr) => {
                if (isDemo) return null;
                throw startErr;
            });

            if (start) {
                setResult({
                    id: start.id,
                    status: 'running',
                    owner: start.owner,
                    started_at: start.started_at,
                    agent_order: [],
                    agents: {},
                });

                try {
                    await streamInvestigation(start.id);
                } catch {
                    await pollInvestigation(start.id);
                }
            } else {
                const investigationResult = await apiClient
                    .runInvestigation(req)
                    .catch(() => DEMO_RESULT);
                setResult(investigationResult);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Investigation failed. Check backend connection.');
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
                        label="Load Suspicious PowerShell Demo"
                        appearance="secondary"
                        disabled={running}
                        onClick={() => {
                            loadDemoForm();
                            setTimeout(() => runInvestigation(true, DEMO_FORM), 50);
                        }}
                    />
                    {result && (
                        <Button
                            label="Clear"
                            appearance="secondary"
                            onClick={() => {
                                setResult(null);
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

            <InvestigationReport descriptors={descriptors} result={result} running={running} />
        </div>
    );
};

export default InvestigationPage;
