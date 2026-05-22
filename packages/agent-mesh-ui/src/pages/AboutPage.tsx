import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';

const Card = styled.div`
    background: ${variables.backgroundColorNavigation};
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    padding: ${variables.spacingLarge};
    max-width: 720px;
`;

const Title = styled.h2`
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightBold};
    color: ${variables.contentColorDefault};
    margin: 0 0 ${variables.spacingSmall} 0;
`;

const Tagline = styled.p`
    font-size: ${variables.fontSizeLarge};
    color: ${variables.accentColorL10};
    margin: 0 0 ${variables.spacingLarge} 0;
`;

const SectionTitle = styled.h3`
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorDefault};
    margin: ${variables.spacingLarge} 0 ${variables.spacingSmall} 0;
    padding-bottom: 6px;
    border-bottom: 1px solid ${variables.borderColor};
`;

const Body = styled.p`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    line-height: 1.6;
    margin: 0 0 ${variables.spacingSmall} 0;
`;

const BulletList = styled.ul`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    line-height: 1.8;
    padding-left: ${variables.spacingLarge};
    margin: 0 0 ${variables.spacingSmall} 0;
`;

const InlineCode = styled.code`
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 11px;
    background: ${variables.backgroundColorSection};
    padding: 1px 5px;
    border-radius: 3px;
    color: ${variables.contentColorDefault};
`;

const WarningBox = styled.div`
    background: ${variables.backgroundColorSection};
    border-left: 3px solid #e8a14c;
    border-radius: 3px;
    padding: ${variables.spacingSmall} ${variables.spacingMedium};
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    margin-top: ${variables.spacingMedium};
`;

const AboutPage: React.FC = () => (
    <Card>
        <Title>Splunk Agent Mesh</Title>
        <Tagline>A configurable agentic platform for Splunk Enterprise.</Tagline>

        <SectionTitle>What it is</SectionTitle>
        <Body>
            Splunk Agent Mesh runs a mesh of AI agents defined in{' '}
            <InlineCode>agents.conf</InlineCode>. Each <InlineCode>[agent:&lt;id&gt;]</InlineCode>{' '}
            stanza configures one node — display name, system prompt, model, order — and the
            runtime ships a single generic agent class. Adding an agent is a config edit, not a
            code change.
        </Body>
        <Body>
            Agents write narrative markdown and structured artifacts back to a merged
            investigation report. SPL-producing agents can attach search artifacts for inline
            table or chart rendering.
        </Body>

        <SectionTitle>The default SOC mesh</SectionTitle>
        <Body>
            The bundled <InlineCode>default/agents.conf</InlineCode> ships seven SOC-flavored
            agents as the first example mesh:
        </Body>
        <BulletList>
            <li>
                <strong>Triage</strong> — entity extraction and severity classification
            </li>
            <li>
                <strong>SPL Hunter</strong> — suggested SPL searches for evidence gathering
            </li>
            <li>
                <strong>Timeline</strong> — chronological incident reconstruction
            </li>
            <li>
                <strong>Blast Radius</strong> — exposure and pivot searches
            </li>
            <li>
                <strong>Detection Gap</strong> — Splunk detection rule recommendation
            </li>
            <li>
                <strong>Response</strong> — prioritized actions, all gated on approval
            </li>
            <li>
                <strong>Executive Brief</strong> — leadership summary with MITRE mapping
            </li>
        </BulletList>

        <SectionTitle>Adding or tuning an agent</SectionTitle>
        <Body>
            Edit{' '}
            <InlineCode>
                packages/agent-mesh/src/main/resources/splunk/default/agents.conf
            </InlineCode>
            , add a stanza, reload Splunk. The agent appears in the investigation report. No
            backend redeploy, no frontend rebuild.
        </Body>

        <SectionTitle>How agents coordinate</SectionTitle>
        <Body>
            Agents are independent by default. Add an explicit{' '}
            <InlineCode>depends_on =</InlineCode> stanza field when one agent should receive
            prior agent summaries and artifact metadata.
        </Body>

        <SectionTitle>Human approval principle</SectionTitle>
        <Body>
            Splunk Agent Mesh never takes automated actions. Response recommendations are exactly
            that — recommendations, gated on operator approval.
        </Body>

        <SectionTitle>Backend</SectionTitle>
        <Body>
            FastAPI service on port 8765. Reads <InlineCode>agents.conf</InlineCode> from Splunk
            via the REST configs API. Run locally with:
        </Body>
        <BulletList>
            <li>
                <InlineCode>cd server &amp;&amp; pip install -r requirements.txt</InlineCode>
            </li>
            <li>
                <InlineCode>uvicorn agent_mesh.app:app --reload --port 8765</InlineCode>
            </li>
        </BulletList>

        <WarningBox>
            This app is a hackathon prototype. Do not use in production without security review,
            Splunk packaging review, and Passwords-API-backed credential storage.
        </WarningBox>
    </Card>
);

export default AboutPage;
