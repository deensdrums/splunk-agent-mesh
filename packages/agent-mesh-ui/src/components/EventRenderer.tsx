import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
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
}

const EventCard = styled.div<{ accent: string }>`
    border-left: 3px solid ${({ accent }) => accent};
    background: ${variables.backgroundColorNavigation};
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

const EventRenderer: React.FC<Props> = ({ event, artifact }) => {
    const accent = TYPE_ACCENTS[event.type];
    const payload = event.payload || {};

    return (
        <EventCard accent={accent}>
            <EventHead>
                <TypeTag accent={accent}>{TYPE_LABELS[event.type] || event.type}</TypeTag>
                <EventTitle>{event.title}</EventTitle>
            </EventHead>
            <EventText>{event.text}</EventText>

            {event.type === 'splunk_search' && typeof payload.query === 'string' && (
                <>
                    <SplBlock>
                        <code>{String(payload.query)}</code>
                    </SplBlock>
                    <PayloadFields payload={payload} skip={['query']} />
                </>
            )}
            {event.type === 'splunk_search' && artifact && (
                <ArtifactRenderer artifact={artifact} embedded />
            )}

            {event.type === 'finding' && <PayloadFields payload={payload} />}

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
