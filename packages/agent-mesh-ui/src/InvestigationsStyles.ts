import styled from 'styled-components';
import { variables } from '@splunk/themes';

export const StyledAppContainer = styled.div<{ $height?: number }>`
    display: flex;
    position: relative;
    flex-direction: column;
    height: ${({ $height }) => ($height ? `${$height}px` : '100vh')};
    min-height: 0;
    width: 100%;
    box-sizing: border-box;
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
    display: flex;
    flex: 0 0 auto;
    justify-content: flex-end;
    gap: ${variables.spacingSmall};
    align-items: center;
    width: 100%;
    box-sizing: border-box;
    padding: ${variables.spacingSmall} ${variables.spacingMedium} 0;
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
