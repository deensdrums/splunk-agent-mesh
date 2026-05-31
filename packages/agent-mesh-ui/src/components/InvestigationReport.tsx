import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import Message from '@splunk/react-ui/Message';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import { AgentDescriptor, AgentEvent, Artifact, InvestigationResult } from '../types';
import ArtifactRenderer from './ArtifactRenderer';
import EventRenderer from './EventRenderer';
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

/**
 * Renders a primary agent's body. The threat hunter now emits an ordered
 * `events` array; we render those, and immediately after each `splunk_search`
 * event we render its matching artifact (matched by order — the Nth search
 * event corresponds to the Nth search artifact, since the harness runs at most
 * one search per turn). Falls back to markdown for legacy single-shot agents.
 */
const AgentBody: React.FC<{ events?: AgentEvent[]; markdown: string; artifacts: Artifact[] }> = ({
    events,
    markdown,
    artifacts,
}) => {
    if (!events || events.length === 0) {
        return (
            <>
                <MarkdownView content={markdown} />
                {artifacts.map((artifact) => (
                    <ArtifactRenderer key={artifact.id} artifact={artifact} />
                ))}
            </>
        );
    }

    let searchIndex = 0;
    const rendered = events.map((event, idx) => {
        let artifact: Artifact | undefined;
        if (event.type === 'splunk_search') {
            artifact = artifacts[searchIndex];
            searchIndex += 1;
        }
        return (
            // eslint-disable-next-line react/no-array-index-key
            <React.Fragment key={`event-${idx}`}>
                <EventRenderer event={event} />
                {artifact && <ArtifactRenderer artifact={artifact} />}
            </React.Fragment>
        );
    });

    // Any artifacts beyond those matched to a search event (defensive).
    const leftover = artifacts.slice(searchIndex);
    return (
        <>
            {rendered}
            {leftover.map((artifact) => (
                <ArtifactRenderer key={artifact.id} artifact={artifact} />
            ))}
        </>
    );
};

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
                        <AgentBody
                            events={output.events}
                            markdown={output.markdown}
                            artifacts={artifactsByAgent.get(agentId) || []}
                        />
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
