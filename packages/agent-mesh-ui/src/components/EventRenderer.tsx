import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import CollapsiblePanel from '@splunk/react-ui/CollapsiblePanel';
import { AgentEvent, Artifact } from '../types';
import ArtifactRenderer from './ArtifactRenderer';
import MarkdownView from './MarkdownView';

/**
 * Renders one structured threat-hunter event. The harness guarantees every
 * event is already valid (type/title/text/payload), so this component only
 * decides presentation per type — it never validates or repairs model output.
 *
 * splunk_search events render their query and intent here, along with the
 * matching SearchArtifact results supplied by the parent.
 */

interface Props {
    event: AgentEvent;
    artifact?: Artifact;
    isCurrent?: boolean;
}

const EventCard = styled.div<{ accent: string; $isCurrent: boolean }>`
    width: 100%;
    box-sizing: border-box;
    border-left: 3px solid ${({ accent }) => accent};
    background: ${({ $isCurrent }) =>
        $isCurrent ? variables.backgroundColorSidebar : variables.backgroundColorNavigation};
    box-shadow: 3px 4px 8px rgba(0, 0, 0, 0.18);
    padding: ${variables.spacingSmall} ${variables.spacingMedium};
    margin-bottom: ${variables.spacingMedium};
`;

const EventHead = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
    margin-bottom: 4px;
`;

const TypeTag = styled.span<{ accent: string }>`
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: ${({ accent }) => accent};
`;

const EventTitle = styled.span`
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorActive};
`;

const EventText = styled.div`
    color: ${variables.contentColorDefault};
    line-height: 1.5;
`;

const SplBlock = styled.pre`
    box-sizing: border-box;
    width: 100%;
    background: ${variables.backgroundColorSidebar};
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    overflow-x: auto;
    padding: ${variables.spacingSmall};
    margin: ${variables.spacingSmall} 0 0;
`;

const PayloadList = styled.dl`
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 2px ${variables.spacingMedium};
    margin: ${variables.spacingSmall} 0 0;
    font-size: ${variables.fontSizeSmall};

    dt {
        color: ${variables.contentColorMuted};
        font-weight: ${variables.fontWeightSemiBold};
    }
    dd {
        margin: 0;
        color: ${variables.contentColorDefault};
    }
`;

const LabelPanel = styled.div<{ tone: string }>`
    margin-top: ${variables.spacingSmall};
    padding: ${variables.spacingSmall};
    background: ${variables.backgroundColorSidebar};
    border-left: 3px solid ${({ tone }) => tone};
`;

const LabelHeader = styled.div`
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: ${variables.spacingSmall};
    margin-bottom: ${variables.spacingXSmall};
`;

const LabelBadge = styled.span<{ tone: string }>`
    display: inline-flex;
    align-items: center;
    color: ${({ tone }) => tone};
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    letter-spacing: 0.04em;
    text-transform: uppercase;
`;

const LabelMeta = styled.span`
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
`;

const LabelSection = styled.div`
    margin-top: ${variables.spacingSmall};
`;

const LabelSectionTitle = styled.div`
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    letter-spacing: 0.03em;
    text-transform: uppercase;
`;

const CompactList = styled.ul`
    margin: ${variables.spacingXSmall} 0 0;
    padding-left: 1.4em;
`;

const ActionsList = styled.ol`
    margin: ${variables.spacingSmall} 0 0;
    padding-left: 1.4em;
`;

// Literal accent colors (not theme tokens) so each event type stays visually
// distinct regardless of which Splunk theme is active.
const TYPE_ACCENTS: Record<AgentEvent['type'], string> = {
    narration: '#888a8d',
    splunk_search: '#3863a0',
    result_summary: '#5c6b77',
    finding: '#d6563c',
    handoff: '#8a6fb0',
    final: '#1a8a4a',
};

const TYPE_LABELS: Record<AgentEvent['type'], string> = {
    narration: 'Narration',
    splunk_search: 'Splunk Search',
    result_summary: 'Result Summary',
    finding: 'Finding',
    handoff: 'Handoff',
    final: 'Final',
};

function isScalar(value: unknown): value is string | number | boolean {
    return ['string', 'number', 'boolean'].includes(typeof value);
}

function isLabelerFinding(event: AgentEvent, payload: Record<string, unknown>): boolean {
    return event.type === 'finding' && payload.source === 'subagent' && payload.kind === 'labeler';
}

function titleCase(value: unknown): string {
    return String(value || '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatConfidence(value: unknown): string | null {
    if (typeof value !== 'number') {
        return isScalar(value) ? String(value) : null;
    }
    const percent = value <= 1 ? value * 100 : value;
    return `${Math.round(percent)}% confidence`;
}

function labelTone(label: unknown, severity: unknown): string {
    const normalizedLabel = String(label || '').toLowerCase();
    const normalizedSeverity = String(severity || '').toLowerCase();
    if (normalizedLabel === 'true_positive' || ['high', 'critical'].includes(normalizedSeverity)) {
        return '#d6563c';
    }
    if (normalizedLabel === 'false_positive' || normalizedLabel === 'benign_true_positive') {
        return '#1a8a4a';
    }
    if (normalizedLabel === 'needs_review' || normalizedSeverity === 'medium') {
        return '#c77919';
    }
    return '#5c6b77';
}

const PayloadFields: React.FC<{ payload: Record<string, unknown>; skip?: string[] }> = ({ payload, skip = [] }) => {
    const entries = Object.entries(payload).filter(([key, value]) => !skip.includes(key) && isScalar(value));
    if (entries.length === 0) {
        return null;
    }
    return (
        <PayloadList>
            {entries.map(([key, value]) => (
                <React.Fragment key={key}>
                    <dt>{key}</dt>
                    <dd>{String(value)}</dd>
                </React.Fragment>
            ))}
        </PayloadList>
    );
};

const LabelFinding: React.FC<{ payload: Record<string, unknown> }> = ({ payload }) => {
    const tone = labelTone(payload.label, payload.severity);
    const confidence = formatConfidence(payload.confidence);
    const counterEvidence = Array.isArray(payload.counter_evidence) ? payload.counter_evidence : [];
    const rubricScores = payload.rubric_scores && typeof payload.rubric_scores === 'object'
        ? Object.entries(payload.rubric_scores as Record<string, unknown>).filter(([, value]) => isScalar(value))
        : [];

    return (
        <LabelPanel tone={tone} data-testid="label-finding">
            <LabelHeader>
                <LabelBadge tone={tone}>{titleCase(payload.label) || 'Unlabeled'}</LabelBadge>
                {typeof payload.severity === 'string' && <LabelMeta>Severity: {titleCase(payload.severity)}</LabelMeta>}
                {confidence && <LabelMeta>{confidence}</LabelMeta>}
            </LabelHeader>

            {typeof payload.rationale === 'string' && <EventText>{payload.rationale}</EventText>}

            {(typeof payload.recommended_disposition === 'string' || counterEvidence.length > 0 || rubricScores.length > 0) && (
                <CollapsiblePanel title="See details" defaultOpen={false} appearance="subtle">
                    {typeof payload.recommended_disposition === 'string' && (
                        <LabelSection>
                            <LabelSectionTitle>Recommended disposition</LabelSectionTitle>
                            <EventText>{payload.recommended_disposition}</EventText>
                        </LabelSection>
                    )}

                    {counterEvidence.length > 0 && (
                        <LabelSection>
                            <LabelSectionTitle>Counter-evidence</LabelSectionTitle>
                            <CompactList>
                                {counterEvidence.map((item) => (
                                    <li key={String(item)}>{String(item)}</li>
                                ))}
                            </CompactList>
                        </LabelSection>
                    )}

                    {rubricScores.length > 0 && (
                        <LabelSection>
                            <LabelSectionTitle>Rubric scores</LabelSectionTitle>
                            <PayloadList>
                                {rubricScores.map(([key, value]) => (
                                    <React.Fragment key={key}>
                                        <dt>{key}</dt>
                                        <dd>{String(value)}</dd>
                                    </React.Fragment>
                                ))}
                            </PayloadList>
                        </LabelSection>
                    )}
                </CollapsiblePanel>
            )}
        </LabelPanel>
    );
};

const EventRenderer: React.FC<Props> = ({ event, artifact, isCurrent = false }) => {
    const accent = TYPE_ACCENTS[event.type];
    const payload = event.payload || {};
    const labelerFinding = isLabelerFinding(event, payload);

    return (
        <EventCard accent={accent} $isCurrent={isCurrent} data-testid="event-card">
            <EventHead>
                <TypeTag accent={accent}>{TYPE_LABELS[event.type] || event.type}</TypeTag>
                <EventTitle>{event.title}</EventTitle>
            </EventHead>
            <EventText>{event.text}</EventText>

            {event.type === 'splunk_search' && artifact && (
                <ArtifactRenderer artifact={artifact} embedded />
            )}
            {event.type === 'splunk_search' && typeof payload.query === 'string' && (
                <CollapsiblePanel title="See details" defaultOpen={false} appearance="subtle">
                    <SplBlock>
                        <code>{String(payload.query)}</code>
                    </SplBlock>
                    <PayloadFields payload={payload} skip={['query']} />
                </CollapsiblePanel>
            )}

            {labelerFinding && <LabelFinding payload={payload} />}
            {event.type === 'finding' && !labelerFinding && (
                <CollapsiblePanel title="See details" defaultOpen={false} appearance="subtle">
                    <PayloadFields payload={payload} />
                </CollapsiblePanel>
            )}

            {event.type === 'final' && (
                <>
                    {typeof payload.summary === 'string' && <MarkdownView content={String(payload.summary)} />}
                    {Array.isArray(payload.recommended_actions) && (
                        <ActionsList>
                            {(payload.recommended_actions as unknown[]).map((action) => (
                                <li key={String(action)}>{String(action)}</li>
                            ))}
                        </ActionsList>
                    )}
                </>
            )}
        </EventCard>
    );
};

export default EventRenderer;
