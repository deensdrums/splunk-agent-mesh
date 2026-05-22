import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import { AgentStep, AgentStatus } from '../../types';

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
    margin-bottom: ${variables.spacingSmall};
`;

const StepRow = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
    padding: 6px 0;
    border-bottom: 1px solid ${variables.borderColor};
    &:last-child {
        border-bottom: none;
    }
`;

const StatusIcon = styled.span<{ status: AgentStatus }>`
    font-size: 14px;
    width: 18px;
    text-align: center;
    color: ${({ status }) => {
        if (status === 'complete') return '#5cc05c';
        if (status === 'error') return '#e84c4c';
        if (status === 'running') return variables.accentColorL10;
        return variables.contentColorMuted;
    }};
`;

const StepLabel = styled.span<{ status: AgentStatus }>`
    font-size: ${variables.fontSizeSmall};
    color: ${({ status }) =>
        status === 'pending' ? variables.contentColorMuted : variables.contentColorDefault};
    min-width: 160px;
`;

const StepMessage = styled.span`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    flex: 1;
`;

function statusIcon(status: AgentStatus): React.ReactNode {
    if (status === 'complete') return '✓';
    if (status === 'error') return '✗';
    if (status === 'running') return <WaitSpinner size="small" />;
    return '○';
}

interface AgentRunPanelProps {
    steps: AgentStep[];
}

const AgentRunPanel: React.FC<AgentRunPanelProps> = ({ steps }) => (
    <Panel>
        <PanelTitle>Agent Progress</PanelTitle>
        {steps.map((step) => (
            <StepRow key={step.name}>
                <StatusIcon status={step.status}>{statusIcon(step.status)}</StatusIcon>
                <StepLabel status={step.status}>{step.label}</StepLabel>
                {step.message && <StepMessage>{step.message}</StepMessage>}
            </StepRow>
        ))}
    </Panel>
);

export default AgentRunPanel;
