import React, { useEffect, useRef, useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { variables } from '@splunk/themes';
import Button from '@splunk/react-ui/Button';
import Message from '@splunk/react-ui/Message';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import {
    AgentDescriptor,
    AgentOutput,
    AgentRunStatus,
    Artifact,
    InvestigationResult,
} from '../types';
import { useStaggeredReveal } from '../hooks/useStaggeredReveal';
import ArtifactRenderer from './ArtifactRenderer';
import EventRenderer from './EventRenderer';
import MarkdownView from './MarkdownView';
import AgentStatusBadge from './AgentStatusBadge';

interface Props {
    descriptors: AgentDescriptor[];
    result: InvestigationResult | null;
    running: boolean;
    onClear: () => void;
}

// Cards reveal one at a time (even when several events arrive in one response)
// and fade/slide in as they paint.
const STAGGER_INTERVAL_MS = 300;
// Treat the view as "stuck to bottom" if within this many px of the end.
const STICK_THRESHOLD_PX = 40;
// Leave a small gutter below the workbench so it does not sit flush against the
// viewport edge. On short screens, keep enough height for a usable transcript
// and allow the document to scroll naturally.
const VIEWPORT_GUTTER_PX = 16;
const MIN_WORKBENCH_HEIGHT_PX = 360;

const fadeSlideIn = keyframes`
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
`;

// ---- Status tones ----
// Statuses map to a small semantic tone; the tone resolves to a theme color
// inside the styled template (the same pattern AgentStatusBadge uses), which
// avoids passing theme-variable interpolations through a string-typed prop.

type Tone = 'muted' | 'info' | 'success' | 'error' | 'default';

const TONE_COLOR = {
    muted: variables.contentColorMuted,
    info: variables.statusColorInfo,
    success: variables.statusColorLow,
    error: variables.statusColorHigh,
    default: variables.contentColorDefault,
};

const INVESTIGATION_TONE: Record<InvestigationResult['status'], Tone> = {
    pending: 'muted',
    running: 'info',
    complete: 'success',
    error: 'error',
    cancelled: 'muted',
};

const HUNTER_TONE: Record<AgentRunStatus, Tone> = {
    pending: 'muted',
    running: 'info',
    iterating: 'info',
    completed: 'success',
    error: 'error',
    cancelled: 'muted',
};

// ---- Layout primitives ----

const Container = styled.div<{ $height: number }>`
    display: flex;
    flex-direction: column;
    height: ${({ $height }) => `${$height}px`};
    min-height: ${MIN_WORKBENCH_HEIGHT_PX}px;
`;

const Toolbar = styled.div`
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: ${variables.spacingMedium};
    padding: 0 0 ${variables.spacingSmall};
    border-bottom: 1px solid ${variables.borderColor};
`;

const ToolbarTitle = styled.div`
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorActive};
`;

const ToolbarGroup = styled.div`
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: ${variables.spacingSmall};
`;

const ToolbarMeta = styled.div`
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
`;

const AgentSection = styled.div`
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    padding-top: ${variables.spacingSmall};
`;

const AgentHead = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
    margin-bottom: ${variables.spacingSmall};
`;

const AgentName = styled.span`
    font-weight: ${variables.fontWeightSemiBold};
    font-size: ${variables.fontSizeLarge};
    color: ${variables.contentColorActive};
`;

// A console surface rather than an outer card: restrained separators define the
// workspace while the colored event blocks carry the visual hierarchy.
const TranscriptShell = styled.div`
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    border-top: 1px solid ${variables.borderColor};
    border-bottom: 1px solid ${variables.borderColor};
    overflow: hidden;
    background: ${variables.backgroundColorPage};
`;

const ScrollArea = styled.div`
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;

    /* Extra bottom padding keeps the newest auto-scrolled card clear of the
       status footer so it stays comfortably readable. */
    padding: ${variables.spacingMedium} ${variables.spacingMedium} ${variables.spacingLarge};
`;

const RevealItem = styled.div`
    animation: ${fadeSlideIn} 150ms ease-out;
`;

const EmptyBody = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
    color: ${variables.contentColorMuted};
    font-style: italic;
    padding: ${variables.spacingLarge} 0;
`;

// Persistent footer within the transcript region (not viewport-fixed): keeps
// live state continuously visible and reinforces the scrollable area.
const StatusBar = styled.div`
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: ${variables.spacingSmall} ${variables.spacingMedium};
    padding: ${variables.spacingSmall} ${variables.spacingMedium};
    border-top: 1px solid ${variables.borderColor};
    background: ${variables.backgroundColorNavigation};
    font-size: ${variables.fontSizeSmall};
`;

const StatusGroup = styled.div`
    display: flex;
    align-items: center;
    gap: 6px;
`;

const StatusLabel = styled.span`
    color: ${variables.contentColorMuted};
`;

const StatusValue = styled.span<{ tone: Tone }>`
    font-weight: ${variables.fontWeightSemiBold};
    color: ${({ tone }) => TONE_COLOR[tone]};
    text-transform: capitalize;
`;

const Spacer = styled.div`
    flex: 1 1 auto;
`;

const MonoId = styled.span`
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    color: ${variables.contentColorMuted};
    white-space: nowrap;
`;

const Placeholder = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
    border: 1px solid ${variables.borderColor};
    border-radius: 6px;
    padding: ${variables.spacingLarge};
    color: ${variables.contentColorMuted};
`;

/**
 * The threat hunter's transcript: an open, scrollable region of structured
 * event blocks (with inline search artifacts) plus a persistent status footer.
 *
 * Events emit in ordered bursts, so `useStaggeredReveal` paints them one at a
 * time. Each `splunk_search` event's artifact is matched by order (the harness
 * runs at most one search per turn) and rendered inline. The view auto-follows
 * new events while the user is near the bottom, and pauses when they scroll up.
 */
const AgentTranscript: React.FC<{
    agentName: string;
    output?: AgentOutput;
    artifacts: Artifact[];
    investigationId: string;
    investigationStatus: InvestigationResult['status'];
    running: boolean;
    resetKey: unknown;
}> = ({ agentName, output, artifacts, investigationId, investigationStatus, running, resetKey }) => {
    const scrollRef = useRef<HTMLDivElement>(null);
    const stickToBottom = useRef(true);

    const events = output?.events;
    const hasEvents = !!events && events.length > 0;
    const total = hasEvents ? events!.length : 0;
    const revealed = useStaggeredReveal(total, STAGGER_INTERVAL_MS, resetKey);

    const hunterStatus: AgentRunStatus = output?.status ?? (running ? 'running' : 'pending');
    const isActive =
        running ||
        investigationStatus === 'running' ||
        investigationStatus === 'pending' ||
        hunterStatus === 'running' ||
        hunterStatus === 'iterating';

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
    }, [revealed, output?.markdown, artifacts.length]);

    let body: React.ReactNode;
    if (output?.status === 'error') {
        body = <Message type="error">{output.error || output.markdown}</Message>;
    } else if (!hasEvents && !output?.markdown) {
        body = (
            <EmptyBody>
                {isActive && <WaitSpinner size="small" />}
                {isActive ? 'Starting investigation…' : 'No events yet.'}
            </EmptyBody>
        );
    } else if (!hasEvents) {
        // Legacy markdown fallback for single-shot agents.
        body = (
            <>
                <MarkdownView content={output!.markdown} />
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
                    <EventRenderer event={event} artifact={artifact} />
                </RevealItem>
            );
        });
        // Artifacts not tied to a search event (defensive) only show once every
        // event is revealed, so none appears before its search card.
        const leftover = revealed >= total ? artifacts.slice(searchIndex) : [];
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
        <AgentSection>
            <AgentHead>
                <AgentName>{agentName}</AgentName>
                <AgentStatusBadge status={hunterStatus} />
            </AgentHead>
            <TranscriptShell>
                <ScrollArea data-testid="transcript-scroll" ref={scrollRef} onScroll={handleScroll}>
                    {body}
                </ScrollArea>
                <StatusBar data-testid="transcript-status">
                    {isActive && <WaitSpinner size="small" />}
                    <StatusGroup>
                        <StatusLabel>Investigation</StatusLabel>
                        <StatusValue tone={INVESTIGATION_TONE[investigationStatus]}>
                            {investigationStatus}
                        </StatusValue>
                    </StatusGroup>
                    <StatusGroup>
                        <StatusLabel>Threat Hunter</StatusLabel>
                        <StatusValue tone={HUNTER_TONE[hunterStatus]}>{hunterStatus}</StatusValue>
                    </StatusGroup>
                    {total > 0 && (
                        <StatusGroup>
                            <StatusLabel>Events</StatusLabel>
                            <StatusValue tone="default">
                                {revealed}/{total}
                            </StatusValue>
                        </StatusGroup>
                    )}
                    <Spacer />
                    {investigationId && <MonoId title={investigationId}>{investigationId}</MonoId>}
                </StatusBar>
            </TranscriptShell>
        </AgentSection>
    );
};

const InvestigationReport: React.FC<Props> = ({ descriptors, result, running, onClear }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [workbenchHeight, setWorkbenchHeight] = useState(MIN_WORKBENCH_HEIGHT_PX);

    useEffect(() => {
        const updateWorkbenchHeight = () => {
            const top = containerRef.current?.getBoundingClientRect().top;
            if (top === undefined) {
                return;
            }
            setWorkbenchHeight(Math.max(MIN_WORKBENCH_HEIGHT_PX, window.innerHeight - top - VIEWPORT_GUTTER_PX));
        };

        updateWorkbenchHeight();
        window.addEventListener('resize', updateWorkbenchHeight);
        return () => window.removeEventListener('resize', updateWorkbenchHeight);
    });

    if (!result && !running) {
        return (
            <Placeholder>
                <Message type="info">Run an investigation to populate the report.</Message>
            </Placeholder>
        );
    }

    if (!result && running) {
        return (
            <Placeholder>
                <WaitSpinner size="medium" /> Starting investigation…
            </Placeholder>
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

    const configuredAgentId = descriptors[0]?.id;
    let agentIds = result.agent_order;
    if (agentIds.length === 0) {
        const outputAgentIds = Object.keys(result.agents);
        agentIds = outputAgentIds.length > 0 ? outputAgentIds : [configuredAgentId || 'spl_hunter'];
    }

    return (
        <Container ref={containerRef} $height={workbenchHeight}>
            <Toolbar>
                <ToolbarGroup>
                    <ToolbarTitle>Investigation Console</ToolbarTitle>
                    <ToolbarMeta>
                        {result.status}
                        {result.owner ? ` · ${result.owner}` : ''}
                        {result.id ? ` · ${result.id}` : ''}
                    </ToolbarMeta>
                </ToolbarGroup>
                <Button label="Clear" appearance="subtle" onClick={onClear} />
            </Toolbar>

            {result.error && (
                <Message type="error" appearance="fill">
                    {result.error}
                </Message>
            )}

            {agentIds.map((agentId) => {
                const output = result.agents[agentId];
                const descriptor = descriptors.find((d) => d.id === agentId);
                const displayName = output?.display_name
                    || descriptor?.display_name
                    || (agentId === 'spl_hunter' ? 'Threat Hunter' : agentId);

                return (
                    <AgentTranscript
                        key={`section-${agentId}`}
                        agentName={displayName}
                        output={output}
                        artifacts={artifactsByAgent.get(agentId) || []}
                        investigationId={result.id}
                        investigationStatus={result.status}
                        running={running}
                        resetKey={result.id}
                    />
                );
            })}
        </Container>
    );
};

export default InvestigationReport;
