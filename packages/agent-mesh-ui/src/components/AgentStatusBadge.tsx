import React from 'react';
import styled, { css } from 'styled-components';
import { variables } from '@splunk/themes';
import { AgentRunStatus } from '../types';

interface Props {
    status: AgentRunStatus;
}

const STATUS_LABEL: Record<AgentRunStatus, string> = {
    pending: 'pending',
    running: 'running',
    completed: 'done',
    error: 'error',
    cancelled: 'cancelled',
};

const variantStyles = {
    pending: css`
        background: ${variables.backgroundColorSidebar};
        color: ${variables.contentColorMuted};
    `,
    running: css`
        background: ${variables.statusColorInfo};
        color: ${variables.contentColorActive};
    `,
    completed: css`
        background: ${variables.statusColorLow};
        color: ${variables.contentColorActive};
    `,
    error: css`
        background: ${variables.statusColorHigh};
        color: ${variables.contentColorActive};
    `,
    cancelled: css`
        background: ${variables.backgroundColorSidebar};
        color: ${variables.contentColorMuted};
    `,
};

const Badge = styled.span<{ $variant: AgentRunStatus }>`
    display: inline-block;
    padding: 1px 8px;
    margin-left: 8px;
    border-radius: 10px;
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    text-transform: capitalize;
    ${(p) => variantStyles[p.$variant]}
`;

const AgentStatusBadge: React.FC<Props> = ({ status }) => (
    <Badge $variant={status}>{STATUS_LABEL[status]}</Badge>
);

export default AgentStatusBadge;
