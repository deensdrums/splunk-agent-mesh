import React, { useState } from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import Button from '@splunk/react-ui/Button';
import { DetectionRecommendationData } from '../types';

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

const DetectionTitle = styled.div`
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorDefault};
    margin-bottom: 4px;
`;

const Description = styled.p`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    margin: 0 0 ${variables.spacingSmall} 0;
    line-height: 1.4;
`;

const MitreRow = styled.div`
    display: flex;
    gap: 6px;
    margin-bottom: ${variables.spacingSmall};
    flex-wrap: wrap;
`;

const MitreBadge = styled.span`
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 11px;
    background: ${variables.accentColorL10};
    color: #fff;
    font-family: ${variables.monoFontFamily};
`;

const CodeBlock = styled.pre`
    background: ${variables.backgroundColorSection};
    border: 1px solid ${variables.borderColor};
    border-radius: 3px;
    padding: ${variables.spacingSmall};
    font-size: 11px;
    font-family: ${variables.monoFontFamily};
    color: ${variables.contentColorDefault};
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0 0 ${variables.spacingSmall} 0;
`;

const CopyConfirm = styled.span`
    font-size: ${variables.fontSizeSmall};
    color: #5cc05c;
    margin-left: ${variables.spacingSmall};
`;

interface DetectionRecommendationProps {
    data: DetectionRecommendationData;
}

const DetectionRecommendation: React.FC<DetectionRecommendationProps> = ({ data }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard?.writeText(data.spl).catch(() => {});
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <Panel>
            <PanelTitle>Detection Recommendation</PanelTitle>
            <DetectionTitle>{data.title}</DetectionTitle>
            <Description>{data.description}</Description>
            <MitreRow>
                {data.mitre.map((t) => (
                    <MitreBadge key={t}>{t}</MitreBadge>
                ))}
            </MitreRow>
            <CodeBlock>{data.spl}</CodeBlock>
            <Button label="Copy SPL" appearance="secondary" onClick={handleCopy} />
            {copied && <CopyConfirm>Copied!</CopyConfirm>}
        </Panel>
    );
};

export default DetectionRecommendation;
