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
    justify-content: space-between;
    gap: ${variables.spacingMedium};
    align-items: center;
    width: 100%;
    box-sizing: border-box;
    padding: ${variables.spacingSmall} ${variables.spacingMedium};
    border-bottom: 1px solid ${variables.borderColor};
`;

export const StyledConsoleTitleGroup = styled.div`
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: ${variables.spacingSmall};
    min-width: 0;
`;

export const StyledConsoleTitle = styled.div`
    color: ${variables.contentColorActive};
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightSemiBold};
`;

export const StyledConsoleMeta = styled.div`
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
`;

export const StyledConsoleActions = styled.div`
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    gap: ${variables.spacingSmall};
`;

export const StyledPanelFill = styled.div`
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
`;

export const StyledModalContent = styled.div`
    min-width: 560px;
    max-width: calc(100vw - 64px);
`;

// Legacy exports retained for any existing references
export const StyledContainer = StyledAppContainer;
export const StyledGreeting = StyledAppContainer;
