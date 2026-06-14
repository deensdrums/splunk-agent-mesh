import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { variables } from '@splunk/themes';
import Button from '@splunk/react-ui/Button';
import Message from '@splunk/react-ui/Message';
import SidePanel from '@splunk/react-ui/SidePanel';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import {
    AgentDescriptor,
    AgentEvent,
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
    inputSummary?: React.ReactNode;
}

// Cards reveal one at a time (even when several events arrive in one response)
// and fade/slide in as they paint.
const STAGGER_INTERVAL_MS = 330;
// Treat the view as "stuck to bottom" if within this many px of the end.
const STICK_THRESHOLD_PX = 40;
const fadeSlideIn = keyframes`
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
`;

const thinkingPulse = keyframes`
    0%, 100% { opacity: 0.55; }
    50% { opacity: 1; }
`;

const thinkingDots = keyframes`
    0% { content: '.'; }
    33% { content: '..'; }
    66%, 100% { content: '...'; }
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

const Container = styled.div`
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    width: 100%;
    overflow: hidden;
`;

const AgentSection = styled.div`
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    width: 100%;
    padding-top: ${variables.spacingSmall};
`;

const AgentHead = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
    flex-wrap: wrap;
    margin-bottom: ${variables.spacingSmall};
`;

const AgentName = styled.span`
    font-weight: ${variables.fontWeightSemiBold};
    font-size: ${variables.fontSizeLarge};
    color: ${variables.contentColorActive};
`;

const AgentHeadSummary = styled.div`
    display: flex;
    align-items: center;
    flex: 1 1 420px;
    justify-content: flex-end;
    min-width: 0;
`;

// A console surface rather than an outer card: restrained separators define the
// workspace while the colored event blocks carry the visual hierarchy.
const TranscriptShell = styled.div`
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    width: 100%;
    box-sizing: border-box;
    border-top: 1px solid ${variables.borderColor};
    border-bottom: 1px solid ${variables.borderColor};
    overflow: hidden;
    background: ${variables.backgroundColorPage};
`;

const ScrollArea = styled.div`
    flex: 1 1 auto;
    min-height: 0;
    width: 100%;
    box-sizing: border-box;
    overflow-y: auto;

    /* Extra bottom padding keeps the newest auto-scrolled card clear of the
       status footer so it stays comfortably readable. */
    padding: ${variables.spacingMedium} ${variables.spacingMedium} ${variables.spacingLarge};
`;

const ScrollContent = styled.div`
    display: flex;
    flex-direction: column;

    /* Breathing room between event cards, on top of the card's own bottom
       margin — keeps the transcript easy to scan. */
    gap: ${variables.spacingSmall};
    width: 100%;
    box-sizing: border-box;
`;

const RevealItem = styled.div`
    width: 100%;
    box-sizing: border-box;
    animation: ${fadeSlideIn} 165ms ease-out;
`;

const ThinkingIndicator = styled.div`
    padding: ${variables.spacingMedium} 0 ${variables.spacingLarge};
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightSemiBold};
    letter-spacing: 0.04em;
    text-align: center;
    animation: ${thinkingPulse} 1.5s ease-in-out infinite;

    &::after {
        display: inline-block;
        min-width: 1.5em;
        content: '.';
        text-align: left;
        animation: ${thinkingDots} 1.2s steps(1, end) infinite;
    }
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
    flex: 1 1 auto;
    align-items: center;
    justify-content: center;
    min-height: 0;
    width: 100%;
    padding: ${variables.spacingXLarge};
    color: ${variables.contentColorMuted};
`;

const EmptyStateBlock = styled.div`
    max-width: 640px;
    text-align: left;
`;

const EmptyKicker = styled.div`
    margin-bottom: ${variables.spacingSmall};
    color: ${variables.accentColorL10};
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    letter-spacing: 0.08em;
    text-transform: uppercase;
`;

const EmptyTitle = styled.div`
    margin-bottom: ${variables.spacingSmall};
    color: ${variables.contentColorActive};
    font-size: 24px;
    font-weight: ${variables.fontWeightSemiBold};
    line-height: 1.25;
`;

const EmptyStateBody = styled.div`
    color: ${variables.contentColorDefault};
    font-size: ${variables.fontSizeLarge};
    line-height: 1.55;
`;

const EmptyHint = styled.div`
    margin-top: ${variables.spacingMedium};
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
    line-height: 1.5;
`;

const StartingState = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeLarge};
`;

const DrawerInner = styled.div`
    width: 560px;
    max-width: 90vw;
    padding: ${variables.spacingLarge} ${variables.spacingXLarge};
    box-sizing: border-box;
`;

const DrawerHeader = styled.div`
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: ${variables.spacingMedium};
    padding-bottom: ${variables.spacingSmall};
    border-bottom: 1px solid ${variables.borderColor};
`;

const DrawerTitle = styled.h2`
    margin: 0;
    font-size: ${variables.fontSizeXXLarge};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorActive};
`;

const DrawerActions = styled.ol`
    margin: ${variables.spacingMedium} 0 0;
    padding-left: 1.4em;
    color: ${variables.contentColorDefault};
    line-height: 1.55;

    li {
        margin-bottom: ${variables.spacingSmall};
    }
`;

const DrawerActionsHeading = styled.h3`
    margin: ${variables.spacingLarge} 0 ${variables.spacingSmall};
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorActive};
`;

// Authoritative labels when the backend reports its phase. Preferred over the
// client-side inference below, since the harness knows exactly what it's doing —
// including the sub-agent ("delegating") window the UI can't otherwise observe.
const PHASE_LABELS: Record<string, string> = {
    delegating: 'Consulting the reporting agent',
    interpreting: 'Interpreting results',
    finalizing: 'Finalizing',
    investigating: 'Investigating',
};

function phaseLabel(phase?: string | null): string | null {
    return phase ? PHASE_LABELS[phase] ?? null : null;
}

/**
 * Context-aware label for the working indicator, derived from the last
 * *revealed* event (so it stays coherent with the visible transcript) and, for
 * searches, the artifact's status. Returns `null` to hide the indicator
 * entirely — e.g. while a search is running, since the search card already
 * shows its own progress.
 */
function thinkingLabel(visible: AgentEvent[], artifacts: Artifact[]): string | null {
    if (visible.length === 0) {
        return 'Investigating';
    }
    const last = visible[visible.length - 1];
    if (last.type === 'splunk_search') {
        // The Nth revealed search maps to the Nth artifact (one search per turn).
        const searchCount = visible.filter((event) => event.type === 'splunk_search').length;
        const artifact = artifacts[searchCount - 1];
        if (!artifact || artifact.status === 'pending' || artifact.status === 'running') {
            return null; // search in flight — its card carries the running state
        }
        return 'Interpreting results'; // rows are back; the agent is reading them
    }
    // After a handoff the sub-agent has already responded (the harness only
    // streams the handoff event once it returns), so a final answer is next.
    if (last.type === 'handoff' || (last.type === 'result_summary' && visible.some((e) => e.type === 'handoff'))) {
        return 'Finalizing';
    }
    return 'Investigating';
}

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
    inputSummary?: React.ReactNode;
    onViewSummary: (summary: string, actions: unknown[]) => void;
}> = ({ agentName, output, artifacts, investigationId, investigationStatus, running, resetKey, inputSummary, onViewSummary }) => {
    const scrollRef = useRef<HTMLDivElement>(null);
    const contentRef = useRef<HTMLDivElement>(null);
    const followBottom = useRef(true);
    const userScrollIntent = useRef(false);

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

    const scrollToBottom = () => {
        const el = scrollRef.current;
        if (!el) {
            return;
        }
        el.scrollTop = el.scrollHeight;
    };

    const handleScroll = () => {
        const el = scrollRef.current;
        if (!el) {
            return;
        }
        const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        if (userScrollIntent.current) {
            followBottom.current = distanceFromBottom < STICK_THRESHOLD_PX;
            userScrollIntent.current = false;
        } else if (followBottom.current && distanceFromBottom >= STICK_THRESHOLD_PX) {
            scrollToBottom();
        }
    };

    const markUserScrollIntent = () => {
        userScrollIntent.current = true;
    };

    // Keep the newest revealed card in view — but only if the user hasn't
    // scrolled up to read an earlier card.
    useLayoutEffect(() => {
        if (followBottom.current) {
            scrollToBottom();
        }
    }, [revealed, output?.markdown, artifacts.length]);

    useEffect(() => {
        const content = contentRef.current;
        if (!content || typeof ResizeObserver === 'undefined') {
            return undefined;
        }
        const observer = new ResizeObserver(() => {
            // Search artifacts often expand after their event card already
            // exists (preview/final rows, charts, tables). That growth is not
            // user intent, so keep following bottom unless an explicit scroll
            // interaction turned follow mode off.
            if (followBottom.current) {
                scrollToBottom();
            }
        });
        observer.observe(content);
        return () => observer.disconnect();
    }, [resetKey]);

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
                    <EventRenderer event={event} artifact={artifact} isCurrent={idx === visible.length - 1} onViewSummary={onViewSummary} />
                </RevealItem>
            );
        });
        // Artifacts not tied to a search event (defensive) only show once every
        // event is revealed, so none appears before its search card.
        const leftover = revealed >= total ? artifacts.slice(searchIndex) : [];
        const finalRevealed = visible.some((event) => event.type === 'final');
        // Prefer the backend's reported phase; fall back to client-side inference.
        const label = phaseLabel(output?.phase) ?? thinkingLabel(visible, artifacts);
        const showThinking = isActive && !finalRevealed && label !== null;
        body = (
            <>
                {rendered}
                {leftover.map((artifact) => (
                        <ArtifactRenderer key={artifact.id} artifact={artifact} />
                    ))}
                {showThinking && <ThinkingIndicator data-testid="thinking-indicator">{label}</ThinkingIndicator>}
            </>
        );
    }

    return (
        <AgentSection>
            <AgentHead>
                <AgentName>{agentName}</AgentName>
                <AgentStatusBadge status={hunterStatus} />
                {inputSummary && <AgentHeadSummary>{inputSummary}</AgentHeadSummary>}
            </AgentHead>
            <TranscriptShell data-testid="transcript-shell">
                <ScrollArea
                    data-testid="transcript-scroll"
                    ref={scrollRef}
                    onScroll={handleScroll}
                    onWheel={markUserScrollIntent}
                    onTouchMove={markUserScrollIntent}
                    onKeyDown={markUserScrollIntent}
                >
                    <ScrollContent ref={contentRef} data-testid="transcript-content">
                        {body}
                    </ScrollContent>
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

const InvestigationReport: React.FC<Props> = ({ descriptors, result, running, inputSummary }) => {
    const [summaryOpen, setSummaryOpen] = useState(false);
    const [summaryContent, setSummaryContent] = useState<{ summary: string; actions: unknown[] }>({ summary: '', actions: [] });

    const handleViewSummary = useCallback((summary: string, actions: unknown[]) => {
        setSummaryContent({ summary, actions });
        setSummaryOpen(true);
    }, []);

    const handleCloseSummary = useCallback(() => {
        setSummaryOpen(false);
    }, []);

    if (!result && !running) {
        return (
            <Placeholder>
                <EmptyStateBlock>
                    <EmptyKicker>Investigation console</EmptyKicker>
                    <EmptyTitle>Start an investigation</EmptyTitle>
                    <EmptyStateBody>
                        Describe an alert, host, user, or suspicious behavior. The Threat Hunter will stream
                        evidence, searches, findings, and a final summary here.
                    </EmptyStateBody>
                    <EmptyHint>
                        Use Run Demo Investigation to preview the console with sample data.
                    </EmptyHint>
                </EmptyStateBlock>
            </Placeholder>
        );
    }

    if (!result && running) {
        return (
            <Placeholder>
                <StartingState>
                    <WaitSpinner size="medium" /> Starting investigation…
                </StartingState>
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
        <Container>
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
                        inputSummary={inputSummary}
                        onViewSummary={handleViewSummary}
                    />
                );
            })}

            <SidePanel
                open={summaryOpen}
                dockPosition="right"
                useLayerForClickAway
                onRequestClose={handleCloseSummary}
                innerStyle={{ overflow: 'auto' }}
            >
                <DrawerInner>
                    <DrawerHeader>
                        <DrawerTitle>Executive Summary</DrawerTitle>
                        <Button appearance="secondary" label="Close" onClick={handleCloseSummary} />
                    </DrawerHeader>
                    <MarkdownView content={summaryContent.summary} />
                    {summaryContent.actions.length > 0 && (
                        <>
                            <DrawerActionsHeading>Recommended Actions</DrawerActionsHeading>
                            <DrawerActions>
                                {summaryContent.actions.map((action) => (
                                    <li key={String(action)}>{String(action)}</li>
                                ))}
                            </DrawerActions>
                        </>
                    )}
                </DrawerInner>
            </SidePanel>
        </Container>
    );
};

export default InvestigationReport;
