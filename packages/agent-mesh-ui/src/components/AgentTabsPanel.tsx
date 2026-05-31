import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import TabLayout from '@splunk/react-ui/TabLayout';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import Message from '@splunk/react-ui/Message';
import { AgentDescriptor, AgentOutput, AgentRunStatus, InvestigationResult } from '../types';
import MarkdownView from './MarkdownView';
import AgentStatusBadge from './AgentStatusBadge';

interface Props {
    descriptors: AgentDescriptor[];
    result: InvestigationResult | null;
    running: boolean;
}

const Container = styled.div`
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    background: ${variables.backgroundColorNavigation};
    padding: ${variables.spacingSmall};
`;

const PanelBody = styled.div`
    padding: ${variables.spacingMedium};
    min-height: 200px;
`;

const PanelMeta = styled.div`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    margin-bottom: ${variables.spacingSmall};
`;

const PendingState = styled.div`
    color: ${variables.contentColorMuted};
    font-style: italic;
`;

function effectiveStatus(running: boolean, output: AgentOutput | undefined): AgentRunStatus {
    if (output) {return output.status;}
    return running ? 'running' : 'pending';
}

const AgentTabsPanel: React.FC<Props> = ({ descriptors, result, running }) => {
    const [active, setActive] = useState<string | undefined>(undefined);

    useEffect(() => {
        if (descriptors.length > 0 && !active) {
            setActive(descriptors[0].id);
        }
    }, [descriptors, active]);

    if (descriptors.length === 0) {
        return (
            <Container>
                <PanelBody>
                    <Message type="info">
                        No agents configured. Add agent stanzas to agents.conf in the Splunk app.
                    </Message>
                </PanelBody>
            </Container>
        );
    }

    return (
        <Container>
            <TabLayout
                activePanelId={active}
                onChange={(_e: unknown, data: { activePanelId?: string }) => {
                    if (data.activePanelId) {setActive(data.activePanelId);}
                }}
            >
                {descriptors.map((d) => {
                    const output = result?.agents[d.id];
                    const status = effectiveStatus(running, output);
                    return (
                        <TabLayout.Panel
                            key={d.id}
                            panelId={d.id}
                            label={
                                <span>
                                    {d.display_name}
                                    <AgentStatusBadge status={status} />
                                </span>
                            }
                        >
                            <PanelBody>
                                {d.description && <PanelMeta>{d.description}</PanelMeta>}
                                {!output && running && (
                                    <PendingState>
                                        <WaitSpinner size="medium" /> Running…
                                    </PendingState>
                                )}
                                {!output && !running && (
                                    <PendingState>
                                        Run an investigation to populate this agent.
                                    </PendingState>
                                )}
                                {output && output.status === 'error' && (
                                    <Message type="error">{output.error || output.markdown}</Message>
                                )}
                                {output && output.status !== 'error' && (
                                    <MarkdownView content={output.markdown} />
                                )}
                            </PanelBody>
                        </TabLayout.Panel>
                    );
                })}
            </TabLayout>
        </Container>
    );
};

export default AgentTabsPanel;
