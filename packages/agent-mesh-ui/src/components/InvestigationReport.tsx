import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import Message from '@splunk/react-ui/Message';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import { AgentDescriptor, Artifact, InvestigationResult } from '../types';
import ArtifactRenderer from './ArtifactRenderer';
import MarkdownView from './MarkdownView';
import AgentStatusBadge from './AgentStatusBadge';

interface Props {
    descriptors: AgentDescriptor[];
    result: InvestigationResult | null;
    running: boolean;
}

const Container = styled.div`
    display: flex;
    flex-direction: column;
    gap: ${variables.spacingMedium};
`;

const Card = styled.section`
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    background: ${variables.backgroundColorNavigation};
    padding: ${variables.spacingMedium};
`;

const ReportHeader = styled(Card)`
    display: flex;
    justify-content: space-between;
    gap: ${variables.spacingMedium};
    align-items: center;
`;

const Title = styled.h2`
    margin: 0 0 4px;
`;

const Meta = styled.div`
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
`;

const AgentGrid = styled.div`
    display: flex;
    flex-wrap: wrap;
    gap: ${variables.spacingSmall};
`;

const AgentPill = styled.div`
    border: 1px solid ${variables.borderColor};
    border-radius: 16px;
    padding: 4px 8px;
`;

const PendingCard = styled(Card)`
    color: ${variables.contentColorMuted};
    font-style: italic;
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
`;

const SectionHeader = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
    margin-bottom: ${variables.spacingSmall};
`;

const SectionTitle = styled.span`
    font-weight: ${variables.fontWeightSemiBold};
    font-size: ${variables.fontSizeLarge};
    color: ${variables.contentColorActive};
`;

function fallbackSections(result: InvestigationResult) {
    return result.agent_order.map((agentId) => {
        const output = result.agents[agentId];
        return {
            id: `section-${agentId}`,
            type: 'markdown' as const,
            title: output?.display_name || agentId,
            agent_id: agentId,
            markdown: output?.markdown || '',
        };
    });
}

const InvestigationReport: React.FC<Props> = ({ descriptors, result, running }) => {
    if (!result && !running) {
        return (
            <Card>
                <Message type="info">Run an investigation to populate the report.</Message>
            </Card>
        );
    }

    if (!result && running) {
        return (
            <Card>
                <WaitSpinner size="medium" /> Starting investigation…
            </Card>
        );
    }

    if (!result) {
        return null;
    }

    const artifactsByAgent = new Map<string, Artifact[]>();
    (result.artifacts || []).forEach((artifact) => {
        const current = artifactsByAgent.get(artifact.agent_id) || [];
        artifactsByAgent.set(artifact.agent_id, current.concat(artifact));
    });

    const agentIds = result.agent_order.length > 0
        ? result.agent_order
        : Object.keys(result.agents);

    return (
        <Container>
            <ReportHeader>
                <div>
                    <Title>Investigation Report</Title>
                    <Meta>
                        {result.id} · {result.status}
                        {result.owner ? ` · ${result.owner}` : ''}
                    </Meta>
                </div>
                {running && <WaitSpinner size="small" />}
            </ReportHeader>

            {result.error && (
                <Message type="error" appearance="fill">
                    {result.error}
                </Message>
            )}

            {agentIds.map((agentId) => {
                const output = result.agents[agentId];
                const descriptor = descriptors.find((d) => d.id === agentId);
                const displayName = output?.display_name || descriptor?.display_name || agentId;

                if (!output) {
                    return (
                        <PendingCard key={`section-${agentId}`}>
                            <WaitSpinner size="small" />
                            {displayName} — waiting for results…
                        </PendingCard>
                    );
                }

                if (output.status === 'error') {
                    return (
                        <Card key={`section-${agentId}`}>
                            <SectionHeader>
                                <SectionTitle>{displayName}</SectionTitle>
                                <AgentStatusBadge status="error" />
                            </SectionHeader>
                            <Message type="error">{output.error || output.markdown}</Message>
                        </Card>
                    );
                }

                return (
                    <Card key={`section-${agentId}`}>
                        <SectionHeader>
                            <SectionTitle>{displayName}</SectionTitle>
                            <AgentStatusBadge status={output.status} />
                        </SectionHeader>
                        <MarkdownView content={output.markdown} />
                        {(artifactsByAgent.get(agentId) || []).map((artifact) => (
                            <ArtifactRenderer key={artifact.id} artifact={artifact} />
                        ))}
                    </Card>
                );
            })}

            <Card>
                <Title>Agent Work Details</Title>
                <AgentGrid>
                    {descriptors.map((descriptor) => {
                        const output = result.agents[descriptor.id];
                        const status = output?.status || (running ? 'running' : 'pending');
                        return (
                            <AgentPill key={descriptor.id}>
                                {descriptor.display_name}
                                <AgentStatusBadge status={status} />
                            </AgentPill>
                        );
                    })}
                </AgentGrid>
            </Card>
        </Container>
    );
};

export default InvestigationReport;
