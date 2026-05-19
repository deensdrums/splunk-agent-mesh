import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import { EvidenceRecord } from '../types';

const Panel = styled.div`
    background: ${variables.backgroundColorNavigation};
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    padding: ${variables.spacingMedium};
    overflow-x: auto;
`;

const PanelTitle = styled.div`
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorDefault};
    margin-bottom: ${variables.spacingMedium};
`;

const Table = styled.table`
    width: 100%;
    border-collapse: collapse;
    font-size: ${variables.fontSizeSmall};
`;

const Th = styled.th`
    text-align: left;
    padding: 6px 10px;
    border-bottom: 2px solid ${variables.borderColor};
    color: ${variables.contentColorMuted};
    font-weight: ${variables.fontWeightSemiBold};
    white-space: nowrap;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
`;

const Td = styled.td`
    padding: 6px 10px;
    border-bottom: 1px solid ${variables.borderColor};
    color: ${variables.contentColorDefault};
    vertical-align: top;
`;

const MonoTd = styled(Td)`
    font-family: ${variables.monoFontFamily};
    font-size: 11px;
    word-break: break-all;
    max-width: 240px;
`;

const InterpretationTd = styled(Td)`
    color: ${variables.contentColorMuted};
    max-width: 280px;
`;

const SourceBadge = styled.span`
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    background: ${variables.backgroundColorSection};
    color: ${variables.contentColorMuted};
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

interface EvidenceTableProps {
    evidence: EvidenceRecord[];
}

const EvidenceTable: React.FC<EvidenceTableProps> = ({ evidence }) => (
    <Panel>
        <PanelTitle>Evidence ({evidence.length})</PanelTitle>
        <Table>
            <thead>
                <tr>
                    <Th>Source</Th>
                    <Th>Time</Th>
                    <Th>Host</Th>
                    <Th>User</Th>
                    <Th>Field</Th>
                    <Th>Value</Th>
                    <Th>Interpretation</Th>
                </tr>
            </thead>
            <tbody>
                {evidence.map((row, idx) => (
                    <tr key={idx}>
                        <Td>
                            <SourceBadge>{row.source}</SourceBadge>
                        </Td>
                        <MonoTd>{formatTime(row.time)}</MonoTd>
                        <MonoTd>{row.host}</MonoTd>
                        <MonoTd>{row.user}</MonoTd>
                        <MonoTd>{row.field}</MonoTd>
                        <MonoTd>{row.value}</MonoTd>
                        <InterpretationTd>{row.interpretation}</InterpretationTd>
                    </tr>
                ))}
            </tbody>
        </Table>
    </Panel>
);

export default EvidenceTable;
