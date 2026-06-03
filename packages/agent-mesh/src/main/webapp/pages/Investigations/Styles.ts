import styled from 'styled-components';
import { variables, mixins } from '@splunk/themes';

export const StyledContainer = styled.div`
    ${mixins.reset('inline')};
    display: flex;
    min-height: 0;
    overflow: hidden;
    font-size: ${variables.fontSizeLarge};
    line-height: normal;
    margin: 0;
`;
