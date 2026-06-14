import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import Button from '@splunk/react-ui/Button';
import Text from '@splunk/react-ui/Text';
import Message from '@splunk/react-ui/Message';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import { LLMSettings } from '../types';
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

const ReadOnlyModelPanel = styled.div`
    padding: ${variables.spacingSmall} ${variables.spacingMedium};
    border-radius: 3px;
    background: ${variables.backgroundColorSection};
    border-left: 3px solid ${variables.accentColorL10};
`;

const ModelValue = styled.div`
    color: ${variables.contentColorActive};
    font-family: ${variables.monoFontFamily};
    font-size: ${variables.fontSizeLarge};
    overflow-wrap: anywhere;
`;

const ModelMeta = styled.div`
    margin-top: 3px;
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
    line-height: 1.5;
`;

const MessageWrapper = styled.div`
    margin-top: ${variables.spacingMedium};
`;

const MessageWrapperSmall = styled.div`
    margin-top: ${variables.spacingSmall};
`;

const SettingsPage: React.FC = () => {
    const [effectiveModel, setEffectiveModel] = useState<LLMSettings['effective_model']>();
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
                setEffectiveModel(s.effective_model);
                setKeyConfigured(s.api_key_configured);
                setLoading(false);
            })
            .catch(() => {
                setLoading(false);
            });
    }, []);

    const handleSave = async () => {
        setSaving(true);
        setSaveMessage(null);
        try {
            const res = await apiClient.saveSettings({
                provider: 'anthropic',
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

    if (loading) {return <WaitSpinner size="medium" />;}

    return (
        <Card>
            <SectionTitle>Anthropic API Key</SectionTitle>

            <FieldGroup>
                <FieldLabel>API Key</FieldLabel>
                <Text
                    value={apiKey}
                    onChange={(_e: unknown, { value }: { value: string }) => setApiKey(value)}
                    placeholder={
                        keyConfigured
                            ? '••••••••••••  (key is configured — enter new key to replace)'
                            : 'sk-ant-...'
                    }
                    type="password"
                    canClear
                />
                <FieldHint>
                    Enter your Anthropic API key. You can create one at{' '}
                    <code>console.anthropic.com</code>.
                    {' '}Current status:{' '}
                    <KeyStatusBadge configured={keyConfigured}>
                        {keyConfigured ? 'Configured' : 'Not configured'}
                    </KeyStatusBadge>
                </FieldHint>
            </FieldGroup>

            <FieldGroup>
                <FieldLabel>Active Model</FieldLabel>
                <ReadOnlyModelPanel>
                    <ModelValue>
                        {effectiveModel?.model || 'No active model configured'}
                    </ModelValue>
                    <ModelMeta>
                        Source: <code>agents.conf</code>
                        {effectiveModel?.conf_source && <> ({effectiveModel.conf_source})</>}
                    </ModelMeta>
                </ReadOnlyModelPanel>
            </FieldGroup>

            <ButtonRow>
                <Button label="Save" appearance="primary" disabled={saving || !apiKey} onClick={handleSave} />
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
        </Card>
    );
};

export default SettingsPage;
