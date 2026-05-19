import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import { AffectedEntities } from '../types';

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

const GraphArea = styled.div`
    height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px dashed ${variables.borderColor};
    border-radius: 3px;
    background: ${variables.backgroundColorSection};
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
    margin-bottom: ${variables.spacingMedium};
    flex-direction: column;
    gap: 8px;
`;

const EntityGrid = styled.div`
    display: flex;
    gap: ${variables.spacingSmall};
    flex-wrap: wrap;
`;

const EntityTag = styled.span<{ kind: string }>`
    display: inline-block;
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-family: ${variables.monoFontFamily};
    background: ${({ kind }) => {
        if (kind === 'user') return '#5cc05c22';
        if (kind === 'host') return '#4c9de822';
        if (kind === 'domain') return '#e84c4c22';
        if (kind === 'ip') return '#e8a14c22';
        return variables.backgroundColorSection;
    }};
    color: ${({ kind }) => {
        if (kind === 'user') return '#5cc05c';
        if (kind === 'host') return '#4c9de8';
        if (kind === 'domain') return '#e84c4c';
        if (kind === 'ip') return '#e8a14c';
        return variables.contentColorDefault;
    }};
    border: 1px solid currentColor;
`;

interface EntityGraphPlaceholderProps {
    entities: AffectedEntities;
}

const EntityGraphPlaceholder: React.FC<EntityGraphPlaceholderProps> = ({ entities }) => (
    <Panel>
        <PanelTitle>Entity Graph</PanelTitle>
        <GraphArea>
            <span>Interactive entity graph — coming in v2</span>
            <span style={{ fontSize: '11px' }}>D3 / Cytoscape visualization</span>
        </GraphArea>
        <EntityGrid>
            {entities.users.map((u) => (
                <EntityTag key={u} kind="user">
                    👤 {u}
                </EntityTag>
            ))}
            {entities.hosts.map((h) => (
                <EntityTag key={h} kind="host">
                    🖥 {h}
                </EntityTag>
            ))}
            {entities.domains.map((d) => (
                <EntityTag key={d} kind="domain">
                    🌐 {d}
                </EntityTag>
            ))}
            {entities.ips.map((ip) => (
                <EntityTag key={ip} kind="ip">
                    📡 {ip}
                </EntityTag>
            ))}
        </EntityGrid>
    </Panel>
);

export default EntityGraphPlaceholder;
