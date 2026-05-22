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

            {(result.sections || fallbackSections(result)).map((section) => (
                <Card key={section.id}>
                    <MarkdownView content={section.markdown} />
                    {(artifactsByAgent.get(section.agent_id || '') || []).map((artifact) => (
                        <ArtifactRenderer key={artifact.id} artifact={artifact} />
                    ))}
                </Card>
            ))}

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
