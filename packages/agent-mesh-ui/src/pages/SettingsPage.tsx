import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import Button from '@splunk/react-ui/Button';
import Text from '@splunk/react-ui/Text';
import Select from '@splunk/react-ui/Select';
import Message from '@splunk/react-ui/Message';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import { LLMProvider, LLMSettings } from '../types';
import { apiClient } from '../services/apiClient';

const Card = styled.div`
    background: ${variables.backgroundColorNavigation};
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    padding: ${variables.spacingLarge};
    max-width: 600px;
`;

const SectionTitle = styled.div`
    font-size: ${variables.fontSizeLarge};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorDefault};
    margin-bottom: ${variables.spacingMedium};
`;

const FieldGroup = styled.div`
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: ${variables.spacingMedium};
`;

const FieldLabel = styled.label`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    font-weight: ${variables.fontWeightSemiBold};
`;

const FieldHint = styled.div`
    font-size: 11px;
    color: ${variables.contentColorMuted};
    margin-top: 2px;
`;

const ButtonRow = styled.div`
    display: flex;
    gap: ${variables.spacingSmall};
    flex-wrap: wrap;
    margin-top: ${variables.spacingLarge};
`;

const KeyStatusBadge = styled.span<{ configured: boolean }>`
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    background: ${({ configured }) => (configured ? '#5cc05c22' : '#e8a14c22')};
    color: ${({ configured }) => (configured ? '#5cc05c' : '#e8a14c')};
    border: 1px solid currentColor;
`;

const SecurityNote = styled.div`
    margin-top: ${variables.spacingMedium};
    padding: ${variables.spacingSmall} ${variables.spacingMedium};
    background: ${variables.backgroundColorSection};
    border-radius: 3px;
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    border-left: 3px solid ${variables.accentColorL10};
    line-height: 1.5;
`;

const Divider = styled.hr`
    border: none;
    border-top: 1px solid ${variables.borderColor};
    margin: ${variables.spacingLarge} 0;
`;

const MessageWrapper = styled.div`
    margin-top: ${variables.spacingMedium};
`;

const MessageWrapperSmall = styled.div`
    margin-top: ${variables.spacingSmall};
`;

const CredentialStorageInfo = styled.div`
    font-size: ${variables.fontSizeSmall};
    color: ${variables.contentColorMuted};
    line-height: 1.6;
`;

const PROVIDER_LABELS: Record<LLMProvider, string> = {
    anthropic: 'Anthropic Claude',
    openrouter: 'OpenRouter',
    openai_compatible: 'Custom OpenAI-compatible',
};

const DEFAULT_MODELS: Record<LLMProvider, string> = {
    anthropic: 'claude-sonnet-4-6',
    openrouter: 'anthropic/claude-sonnet-4-6',
    openai_compatible: 'gpt-4o',
};

const SettingsPage: React.FC = () => {
    const [provider, setProvider] = useState<LLMProvider>('anthropic');
    const [baseUrl, setBaseUrl] = useState('');
    const [model, setModel] = useState(DEFAULT_MODELS.anthropic);
    const [apiKey, setApiKey] = useState('');
    const [keyConfigured, setKeyConfigured] = useState(false);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const [testResult, setTestResult] = useState<{ success: boolean; text: string } | null>(null);

    useEffect(() => {
        apiClient
            .getSettings()
            .then((s: LLMSettings) => {
                setProvider(s.provider);
                setModel(s.model || DEFAULT_MODELS[s.provider]);
                setBaseUrl(s.base_url || '');
                setKeyConfigured(s.api_key_configured);
                setLoading(false);
            })
            .catch(() => {
                setLoading(false);
            });
    }, []);

    const handleProviderChange = (_e: unknown, { value }: { value: string | number | boolean }) => {
        const p = String(value) as LLMProvider;
        setProvider(p);
        setModel(DEFAULT_MODELS[p]);
        if (p !== 'openai_compatible') setBaseUrl('');
    };

    const handleSave = async () => {
        setSaving(true);
        setSaveMessage(null);
        try {
            const res = await apiClient.saveSettings({
                provider,
                base_url: baseUrl || undefined,
                model,
                api_key: apiKey || undefined,
            });
            setKeyConfigured(res.api_key_configured);
            setApiKey('');
            setSaveMessage({ type: 'success', text: 'Settings saved successfully.' });
        } catch (err) {
            setSaveMessage({ type: 'error', text: err instanceof Error ? err.message : 'Save failed.' });
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const res = await apiClient.testConnection();
            setTestResult({
                success: res.success,
                text: res.success
                    ? `Connected. Model: ${res.model ?? 'unknown'} · Latency: ${res.latency_ms ?? '?'}ms`
                    : `Failed: ${res.error ?? 'unknown error'}`,
            });
        } catch (err) {
            setTestResult({ success: false, text: err instanceof Error ? err.message : 'Test failed.' });
        } finally {
            setTesting(false);
        }
    };

    const handleClearCredentials = async () => {
        try {
            await apiClient.clearCredentials();
            setKeyConfigured(false);
            setSaveMessage({ type: 'success', text: 'API key cleared.' });
        } catch (err) {
            setSaveMessage({ type: 'error', text: err instanceof Error ? err.message : 'Clear failed.' });
        }
    };

    if (loading) return <WaitSpinner size="medium" />;

    return (
        <Card>
            <SectionTitle>LLM Provider Settings</SectionTitle>

            <FieldGroup>
                <FieldLabel>Provider</FieldLabel>
                <Select value={provider} onChange={handleProviderChange}>
                    <Select.Option label={PROVIDER_LABELS.anthropic} value="anthropic" />
                    <Select.Option label={PROVIDER_LABELS.openrouter} value="openrouter" />
                    <Select.Option label={PROVIDER_LABELS.openai_compatible} value="openai_compatible" />
                </Select>
            </FieldGroup>

            {provider === 'openai_compatible' && (
                <FieldGroup>
                    <FieldLabel>Base URL</FieldLabel>
                    <Text
                        value={baseUrl}
                        onChange={(_e: unknown, { value }: { value: string }) => setBaseUrl(value)}
                        placeholder="https://your-api-endpoint/v1"
                    />
                    <FieldHint>OpenAI-compatible endpoint (e.g., local LLM, Azure OpenAI, etc.)</FieldHint>
                </FieldGroup>
            )}

            <FieldGroup>
                <FieldLabel>Model</FieldLabel>
                <Text
                    value={model}
                    onChange={(_e: unknown, { value }: { value: string }) => setModel(value)}
                    placeholder="claude-sonnet-4-6"
                />
            </FieldGroup>

            <FieldGroup>
                <FieldLabel>API Key</FieldLabel>
                <Text
                    value={apiKey}
                    onChange={(_e: unknown, { value }: { value: string }) => setApiKey(value)}
                    placeholder={
                        keyConfigured ? '••••••••••••  (key is configured — enter new key to replace)' : 'Enter API key'
                    }
                    type="password"
                    canClear
                />
                <FieldHint>
                    Current status:{' '}
                    <KeyStatusBadge configured={keyConfigured}>
                        {keyConfigured ? 'Configured' : 'Not configured'}
                    </KeyStatusBadge>
                </FieldHint>
            </FieldGroup>

            <SecurityNote>
                API keys are stored in Splunk secure credential storage, not in browser storage or any config file. The
                key is never returned to the frontend after saving — only a configured/not-configured status is shown.
                Do not share or commit API keys.
            </SecurityNote>

            <ButtonRow>
                <Button label="Save" appearance="primary" disabled={saving} onClick={handleSave} />
                <Button
                    label="Test Connection"
                    appearance="secondary"
                    disabled={testing || !keyConfigured}
                    onClick={handleTest}
                />
                <Button
                    label="Clear Credentials"
                    appearance="destructive"
                    disabled={!keyConfigured}
                    onClick={handleClearCredentials}
                />
            </ButtonRow>

            {saveMessage && (
                <MessageWrapper>
                    <Message type={saveMessage.type} appearance="fill">
                        {saveMessage.text}
                    </Message>
                </MessageWrapper>
            )}

            {testResult && (
                <MessageWrapperSmall>
                    <Message type={testResult.success ? 'success' : 'error'} appearance="fill">
                        {testResult.text}
                    </Message>
                </MessageWrapperSmall>
            )}

            <Divider />

            <SectionTitle>About Credential Storage</SectionTitle>
            <CredentialStorageInfo>
                <p>
                    In production, API keys are stored using Splunk&apos;s encrypted passwords API (
                    <code>/services/storage/passwords</code>). Keys are encrypted at rest using Splunk&apos;s built-in
                    key management.
                </p>
                <p>
                    In local development mode, keys are read from the <code>AGENT_MESH_API_KEY</code> environment
                    variable. Plaintext key storage is refused unless <code>AGENT_MESH_DEV_MODE=1</code> is also set.
                </p>
                <p>
                    The API key is never logged, never included in HTTP responses, and never stored in browser
                    localStorage or sessionStorage.
                </p>
            </CredentialStorageInfo>
        </Card>
    );
};

export default SettingsPage;
