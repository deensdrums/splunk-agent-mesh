import styled from 'styled-components';
import { variables } from '@splunk/themes';

export const StyledAppContainer = styled.div<{ $height?: number }>`
    display: flex;
    position: relative;
    flex-direction: column;
    height: ${({ $height }) => ($height ? `${$height}px` : '100vh')};
    min-height: 0;
    overflow: hidden;
    background: ${variables.backgroundColorPage};
`;

export const StyledConsoleMain = styled.div`
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    width: 100%;
    overflow: hidden;
`;

export const StyledConsoleControls = styled.div`
    position: absolute;
    top: ${variables.spacingSmall};
    right: ${variables.spacingMedium};
    z-index: 10;
    display: flex;
    gap: ${variables.spacingSmall};
    align-items: center;
`;

export const StyledPanelFill = styled.div`
    display: flex;
    flex: 1 1 auto;
    min-height: 0;
    width: 100%;
    overflow: hidden;
`;

export const StyledModalContent = styled.div`
    min-width: 560px;
    max-width: calc(100vw - 64px);
`;

// Legacy exports retained for any existing references
export const StyledContainer = StyledAppContainer;
export const StyledGreeting = StyledAppContainer;
