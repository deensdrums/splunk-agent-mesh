import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import { InvestigationResult } from '../types';

const Panel = styled.div`
    background: ${variables.backgroundColorNavigation};
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    padding: ${variables.spacingMedium};
    height: 100%;
`;

const PanelTitle = styled.div`
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorDefault};
    margin-bottom: ${variables.spacingSmall};
`;

const BadgeRow = styled.div`
    display: flex;
    gap: ${variables.spacingSmall};
    margin-bottom: ${variables.spacingMedium};
    align-items: center;
    flex-wrap: wrap;
`;

const SeverityBadge = styled.span<{ severity: string }>`
    padding: 3px 10px;
    border-radius: 12px;
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    background: ${({ severity }) => {
        if (severity === 'Critical') return '#b22222';
        if (severity === 'High') return '#e84c4c';
        if (severity === 'Medium') return '#e8a14c';
        return '#5cc05c';
    }};
    color: #fff;
`;

const ConfidenceBadge = styled.span`
    padding: 3px 10px;
    border-radius: 12px;
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    background: ${variables.accentColorL10};
    color: #fff;
`;

const Summary = styled.p`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorDefault};
    line-height: 1.5;
    margin: 0 0 ${variables.spacingMedium} 0;
`;

const EntitySection = styled.div`
    margin-top: ${variables.spacingSmall};
`;

const EntityLabel = styled.span`
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorMuted};
    display: inline-block;
    min-width: 70px;
`;

const EntityValue = styled.span`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorDefault};
    font-family: ${variables.monoFontFamily};
`;

const EntityRow = styled.div`
    margin-bottom: 4px;
`;

interface InvestigationSummaryProps {
    result: InvestigationResult;
}

const InvestigationSummary: React.FC<InvestigationSummaryProps> = ({ result }) => (
    <Panel>
        <PanelTitle>{result.title}</PanelTitle>
        <BadgeRow>
            <SeverityBadge severity={result.severity}>{result.severity}</SeverityBadge>
            <ConfidenceBadge>Confidence: {Math.round(result.confidence * 100)}%</ConfidenceBadge>
        </BadgeRow>
        <Summary>{result.summary}</Summary>
        <EntitySection>
            {result.affected_entities.users.length > 0 && (
                <EntityRow>
                    <EntityLabel>Users: </EntityLabel>
                    <EntityValue>{result.affected_entities.users.join(', ')}</EntityValue>
                </EntityRow>
            )}
            {result.affected_entities.hosts.length > 0 && (
                <EntityRow>
                    <EntityLabel>Hosts: </EntityLabel>
                    <EntityValue>{result.affected_entities.hosts.join(', ')}</EntityValue>
                </EntityRow>
            )}
            {result.affected_entities.domains.length > 0 && (
                <EntityRow>
                    <EntityLabel>Domains: </EntityLabel>
                    <EntityValue>{result.affected_entities.domains.join(', ')}</EntityValue>
                </EntityRow>
            )}
            {result.affected_entities.ips.length > 0 && (
                <EntityRow>
                    <EntityLabel>IPs: </EntityLabel>
                    <EntityValue>{result.affected_entities.ips.join(', ')}</EntityValue>
                </EntityRow>
            )}
            {result.affected_entities.files.length > 0 && (
                <EntityRow>
                    <EntityLabel>Files: </EntityLabel>
                    <EntityValue>{result.affected_entities.files.join(', ')}</EntityValue>
                </EntityRow>
            )}
        </EntitySection>
    </Panel>
);

export default InvestigationSummary;
