import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import { TimelineEvent, Severity } from '../types';

const Panel = styled.div`
    background: ${variables.backgroundColorNavigation};
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    padding: ${variables.spacingMedium};
`;

const PanelTitle = styled.div`
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorDefault};
    margin-bottom: ${variables.spacingMedium};
`;

const Timeline = styled.div`
    position: relative;
    padding-left: 24px;
    &::before {
        content: '';
        position: absolute;
        left: 8px;
        top: 0;
        bottom: 0;
        width: 2px;
        background: ${variables.borderColor};
    }
`;

const TimelineItem = styled.div`
    position: relative;
    margin-bottom: ${variables.spacingMedium};
    &:last-child {
        margin-bottom: 0;
    }
`;

const Dot = styled.div<{ severity: Severity }>`
    position: absolute;
    left: -20px;
    top: 4px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: ${({ severity }) => {
        if (severity === 'critical') return '#b22222';
        if (severity === 'high') return '#e84c4c';
        if (severity === 'medium') return '#e8a14c';
        return '#5cc05c';
    }};
    border: 2px solid ${variables.backgroundColorPage};
`;

const TimeLabel = styled.div`
    font-size: 11px;
    font-family: ${variables.monoFontFamily};
    color: ${variables.contentColorMuted};
    margin-bottom: 2px;
`;

const EventTitle = styled.div`
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorDefault};
    margin-bottom: 2px;
`;

const EventDescription = styled.div`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
`;

const SourceBadge = styled.span`
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    background: ${variables.backgroundColorSection};
    color: ${variables.contentColorMuted};
    margin-right: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
`;

function formatTime(iso: string): string {
    try {
        return new Date(iso).toLocaleTimeString(undefined, {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
        });
    } catch {
        return iso;
    }
}

interface IncidentTimelineProps {
    events: TimelineEvent[];
}

const IncidentTimeline: React.FC<IncidentTimelineProps> = ({ events }) => (
    <Panel>
        <PanelTitle>Incident Timeline</PanelTitle>
        <Timeline>
            {events.map((event, idx) => (
                <TimelineItem key={idx}>
                    <Dot severity={event.severity} />
                    <TimeLabel>
                        <SourceBadge>{event.source}</SourceBadge>
                        {formatTime(event.time)}
                    </TimeLabel>
                    <EventTitle>{event.title}</EventTitle>
                    <EventDescription>{event.description}</EventDescription>
                </TimelineItem>
            ))}
        </Timeline>
    </Panel>
);

export default IncidentTimeline;
