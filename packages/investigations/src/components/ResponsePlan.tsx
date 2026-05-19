import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import { ResponseAction } from '../types';

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

const ActionItem = styled.div`
    display: flex;
    align-items: flex-start;
    gap: ${variables.spacingSmall};
    padding: ${variables.spacingSmall} 0;
    border-bottom: 1px solid ${variables.borderColor};
    &:last-child {
        border-bottom: none;
    }
`;

const ActionIcon = styled.div`
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: 2px solid ${variables.borderColor};
    flex-shrink: 0;
    margin-top: 2px;
`;

const ActionContent = styled.div`
    flex: 1;
`;

const ActionTitle = styled.div`
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorDefault};
`;

const ActionTarget = styled.span`
    font-family: ${variables.monoFontFamily};
    font-size: 11px;
    color: ${variables.accentColorL10};
    margin-left: 6px;
`;

const ActionRisk = styled.div`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    margin-top: 2px;
`;

const ApprovalBadge = styled.span<{ required: boolean }>`
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: ${variables.fontWeightSemiBold};
    background: ${({ required }) => (required ? '#e8a14c22' : '#5cc05c22')};
    color: ${({ required }) => (required ? '#e8a14c' : '#5cc05c')};
    border: 1px solid ${({ required }) => (required ? '#e8a14c' : '#5cc05c')};
    margin-left: 6px;
    white-space: nowrap;
`;

const HumanApprovalNote = styled.div`
    margin-top: ${variables.spacingMedium};
    padding: ${variables.spacingSmall};
    background: ${variables.backgroundColorSection};
    border-radius: 3px;
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    border-left: 3px solid ${variables.accentColorL10};
`;

interface ResponsePlanProps {
    actions: ResponseAction[];
}

const ResponsePlan: React.FC<ResponsePlanProps> = ({ actions }) => (
    <Panel>
        <PanelTitle>Response Plan</PanelTitle>
        {actions.map((action, idx) => (
            <ActionItem key={idx}>
                <ActionIcon />
                <ActionContent>
                    <ActionTitle>
                        {action.action}
                        <ActionTarget>{action.target}</ActionTarget>
                        <ApprovalBadge required={action.requires_approval}>
                            {action.requires_approval ? 'Approval Required' : 'Passive'}
                        </ApprovalBadge>
                    </ActionTitle>
                    <ActionRisk>Risk: {action.risk}</ActionRisk>
                </ActionContent>
            </ActionItem>
        ))}
        <HumanApprovalNote>
            All actions are recommendations. No automated execution. Analyst approval required before any containment
            action is taken.
        </HumanApprovalNote>
    </Panel>
);

export default ResponsePlan;
