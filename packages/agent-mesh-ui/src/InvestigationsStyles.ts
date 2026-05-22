import styled from 'styled-components';
import { variables } from '@splunk/themes';

export const StyledAppContainer = styled.div`
    display: block;
    padding: ${variables.spacingLarge};
`;

export const StyledHeader = styled.h1`
    font-size: 24px;
    font-weight: ${variables.fontWeightBold};
    color: ${variables.contentColorDefault};
    margin: 0 0 4px 0;
`;

export const StyledTagline = styled.p`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    margin: 0 0 ${variables.spacingMedium} 0;
`;

// Legacy exports retained for any existing references
export const StyledContainer = StyledAppContainer;
export const StyledGreeting = StyledHeader;
