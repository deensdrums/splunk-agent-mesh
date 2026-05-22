import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';

const Card = styled.div`
    background: ${variables.backgroundColorNavigation};
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    padding: ${variables.spacingLarge};
    max-width: 700px;
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
    font-family: ${variables.monoFontFamily};
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
        <Tagline>From alert to evidence-backed response in minutes.</Tagline>

        <SectionTitle>What Splunk Agent Mesh Does</SectionTitle>
        <Body>
            Splunk Agent Mesh is an agentic SOC investigation copilot embedded in Splunk. A SOC analyst describes an
            alert — a host, a user, a suspicious behavior — and Splunk Agent Mesh launches a multi-step investigation
            using a team of specialized AI agents.
        </Body>
        <Body>
            The investigation generates SPL searches, retrieves Splunk data, correlates evidence across sources,
            builds a timeline, maps behavior to MITRE ATT&CK, scores severity, identifies blast radius, and
            recommends response actions — all in a few seconds.
        </Body>

        <SectionTitle>How AI Is Used</SectionTitle>
        <Body>
            Splunk Agent Mesh uses a configurable LLM provider (Anthropic Claude, OpenRouter, or any OpenAI-compatible
            endpoint) to power its agents. Each agent has a defined purpose, input, output, and prompt contract.
        </Body>
        <BulletList>
            <li>
                <strong>Triage Agent</strong> — extracts entities and classifies initial severity
            </li>
            <li>
                <strong>SPL Hunter Agent</strong> — generates and runs targeted Splunk searches
            </li>
            <li>
                <strong>Timeline Agent</strong> — correlates events into a chronological timeline
            </li>
            <li>
                <strong>Blast Radius Agent</strong> — identifies other affected systems
            </li>
            <li>
                <strong>Detection Gap Agent</strong> — generates reusable Splunk detection logic
            </li>
            <li>
                <strong>Response Agent</strong> — recommends prioritized response actions
            </li>
            <li>
                <strong>Executive Brief Agent</strong> — synthesizes findings into a final report
            </li>
        </BulletList>

        <SectionTitle>How Splunk Data Is Used</SectionTitle>
        <Body>
            Agents query Splunk using SPL searches targeting endpoint, DNS, auth, proxy, and firewall indexes.
            Every conclusion in the investigation report is tied to evidence retrieved from Splunk — the agents
            are not permitted to fabricate findings.
        </Body>
        <Body>
            In demo mode, synthetic sample data is used so the app can be evaluated without a live Splunk security
            data source.
        </Body>

        <SectionTitle>Human Approval Principle</SectionTitle>
        <Body>
            Splunk Agent Mesh never takes automated response actions. All response recommendations require explicit
            analyst approval before execution. The app is a decision-support tool, not an autonomous responder.
        </Body>
        <BulletList>
            <li>All SPL is visible before execution</li>
            <li>All agent conclusions show their evidence source</li>
            <li>All response actions are flagged with approval requirements</li>
            <li>No action is taken without human sign-off</li>
        </BulletList>

        <SectionTitle>Demo Dataset</SectionTitle>
        <Body>
            The demo mode uses a synthetic scenario: <strong>Suspicious PowerShell on FIN-LAPTOP-22</strong>.
        </Body>
        <Body>
            Attack chain: User <InlineCode>jsmith</InlineCode> opens a suspicious Office document →{' '}
            <InlineCode>winword.exe</InlineCode> spawns <InlineCode>powershell.exe</InlineCode> with encoded
            command → host contacts rare domain <InlineCode>cdn-update-check.com</InlineCode> → jsmith accesses
            finance file server → archive <InlineCode>Q2_finance_exports.zip</InlineCode> is created → 48 MB
            exfiltrated to external IP.
        </Body>

        <SectionTitle>Backend Requirements</SectionTitle>
        <Body>
            Splunk Agent Mesh requires a Python backend service to run agents and LLM calls. In production, this is
            packaged as a Splunk Custom REST Handler. In local development, run:
        </Body>
        <BulletList>
            <li>
                <InlineCode>cd server && pip install -r requirements.txt</InlineCode>
            </li>
            <li>
                <InlineCode>uvicorn agent_mesh.app:app --reload --port 8000</InlineCode>
            </li>
        </BulletList>
        <Body>
            Configure your LLM provider on the Settings tab. Set <InlineCode>AGENT_MESH_API_KEY</InlineCode>{' '}
            as an environment variable for local development.
        </Body>

        <WarningBox>
            This app is a hackathon prototype. Do not use in production without security review, proper Splunk
            packaging, and validated credential storage.
        </WarningBox>
    </Card>
);

export default AboutPage;
