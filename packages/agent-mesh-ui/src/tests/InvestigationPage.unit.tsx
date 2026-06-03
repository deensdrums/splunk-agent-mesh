import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';

import InvestigationPage, { ConsoleChromeState, upsertArtifacts } from '../pages/InvestigationPage';

jest.mock('@splunk/themes', () => ({
    variables: new Proxy({}, { get: () => '0px' }),
}));
jest.mock('@splunk/react-ui/Button', () => ({ label, onClick, disabled }: any) => (
    <button type="button" onClick={onClick} disabled={disabled}>
        {label}
    </button>
));
jest.mock('@splunk/react-ui/TextArea', () => ({ value, onChange }: any) => (
    <textarea value={value} onChange={(event) => onChange?.(event, { value: event.target.value })} />
));
jest.mock('@splunk/react-ui/Text', () => ({ value, onChange, placeholder }: any) => (
    <input
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange?.(event, { value: event.target.value })}
    />
));
jest.mock('@splunk/react-ui/Message', () => ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
));
jest.mock('../components/InvestigationReport', () => ({ result, inputSummary }: any) => (
    <div>
        {result && <span>Report ready</span>}
        {inputSummary}
    </div>
));
jest.mock('../services/apiClient', () => ({
    apiClient: {
        getAgents: jest.fn().mockResolvedValue({ agents: [] }),
        startInvestigation: jest.fn().mockResolvedValue({
            id: 'inv-test',
            status: 'running',
        }),
    },
    createInvestigationStream: jest.fn(() => ({ close: jest.fn() })),
}));

test('collapses inputs when a run starts and expands them when the console is cleared', async () => {
    let chrome: ConsoleChromeState | null = null;
    render(<InvestigationPage onConsoleChromeChange={(state) => { chrome = state; }} />);

    expect(screen.getByText('Describe what to investigate')).toBeInTheDocument();
    fireEvent.change(screen.getAllByRole('textbox')[0], {
        target: { value: 'Investigate suspicious PowerShell activity.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Start Investigation' }));

    expect(await screen.findByRole('button', { name: 'Edit Inputs' })).toBeInTheDocument();
    expect(screen.queryByText('Describe what to investigate')).not.toBeInTheDocument();
    expect(screen.getByText('Investigate suspicious PowerShell activity.')).toBeInTheDocument();

    await waitFor(() => expect(chrome?.canClear).toBe(true));
    act(() => {
        chrome?.onClear?.();
    });
    expect(screen.getByText('Describe what to investigate')).toBeInTheDocument();
});

test('replaces streamed artifact revisions without duplicating the search card', () => {
    const running = { id: 'artifact-1', status: 'running', _revision: 1 } as any;
    const done = { id: 'artifact-1', status: 'done', _revision: 2 } as any;

    expect(upsertArtifacts([running], [done])).toEqual([done]);
});
