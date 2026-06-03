import styled from 'styled-components';
import { variables } from '@splunk/themes';

export const StyledAppContainer = styled.div<{ $height?: number }>`
    display: flex;
    flex-direction: column;
    height: ${({ $height }) => ($height ? `${$height}px` : '100vh')};
    min-height: 0;
    overflow: hidden;
    background: ${variables.backgroundColorPage};
`;

export const StyledNavigationShell = styled.div`
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;

    > * {
        display: flex;
        flex: 1 1 auto;
        flex-direction: column;
        min-height: 0;
        width: 100%;
        overflow: hidden;
    }

    [role='tabpanel'] {
        display: flex;
        flex: 1 1 auto;
        min-height: 0;
        width: 100%;
        overflow: auto;
    }
`;

export const StyledPanelFill = styled.div`
    display: flex;
    flex: 1 1 auto;
    min-height: 0;
    width: 100%;
    overflow: hidden;
`;

// Legacy exports retained for any existing references
export const StyledContainer = StyledAppContainer;
export const StyledGreeting = StyledAppContainer;
