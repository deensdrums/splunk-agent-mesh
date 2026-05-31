import React, { useEffect, useRef } from 'react';
import styled, { keyframes } from 'styled-components';
import { variables } from '@splunk/themes';
import Message from '@splunk/react-ui/Message';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import { AgentDescriptor, AgentEvent, Artifact, InvestigationResult } from '../types';
import { useStaggeredReveal } from '../hooks/useStaggeredReveal';
import ArtifactRenderer from './ArtifactRenderer';
import EventRenderer from './EventRenderer';
import MarkdownView from './MarkdownView';
import AgentStatusBadge from './AgentStatusBadge';

// Cards reveal one at a time (even when several events arrive in one response)
// and fade/slide in as they paint.
const STAGGER_INTERVAL_MS = 300;
// Treat the view as "stuck to bottom" if within this many px of the end.
const STICK_THRESHOLD_PX = 40;

const fadeSlideIn = keyframes`
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
`;

const ScrollArea = styled.div`
    max-height: 70vh;
    overflow-y: auto;
    padding-right: ${variables.spacingSmall};
`;

const RevealItem = styled.div`
    animation: ${fadeSlideIn} 150ms ease-out;
`;

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
const AgentBody: React.FC<{
    events?: AgentEvent[];
    markdown: string;
    artifacts: Artifact[];
    resetKey: unknown;
}> = ({ events, markdown, artifacts, resetKey }) => {
    const scrollRef = useRef<HTMLDivElement>(null);
    const stickToBottom = useRef(true);
    const hasEvents = !!events && events.length > 0;
    const revealed = useStaggeredReveal(hasEvents ? events!.length : 0, STAGGER_INTERVAL_MS, resetKey);

    const handleScroll = () => {
        const el = scrollRef.current;
        if (!el) {
            return;
        }
        const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        stickToBottom.current = distanceFromBottom < STICK_THRESHOLD_PX;
    };

    // Keep the newest revealed card in view — but only if the user hasn't
    // scrolled up to read an earlier card.
    useEffect(() => {
        const el = scrollRef.current;
        if (el && stickToBottom.current) {
            el.scrollTop = el.scrollHeight;
        }
    }, [revealed, markdown, artifacts.length]);

    let body: React.ReactNode;
    if (!hasEvents) {
        body = (
            <>
                <MarkdownView content={markdown} />
                {artifacts.map((artifact) => (
                    <ArtifactRenderer key={artifact.id} artifact={artifact} />
                ))}
            </>
        );
    } else {
        let searchIndex = 0;
        const visible = events!.slice(0, revealed);
        const rendered = visible.map((event, idx) => {
            let artifact: Artifact | undefined;
            if (event.type === 'splunk_search') {
                artifact = artifacts[searchIndex];
                searchIndex += 1;
            }
            return (
                // eslint-disable-next-line react/no-array-index-key
                <RevealItem key={`event-${idx}`}>
                    <EventRenderer event={event} />
                    {artifact && <ArtifactRenderer artifact={artifact} />}
                </RevealItem>
            );
        });
        // Artifacts not tied to a search event (defensive) are only shown once
        // every event is revealed, so none ever appears before its search card.
        const leftover = revealed >= events!.length ? artifacts.slice(searchIndex) : [];
        body = (
            <>
                {rendered}
                {leftover.map((artifact) => (
                    <ArtifactRenderer key={artifact.id} artifact={artifact} />
                ))}
            </>
        );
    }

    return (
        <ScrollArea ref={scrollRef} onScroll={handleScroll}>
            {body}
        </ScrollArea>
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
                            resetKey={result.id}
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
