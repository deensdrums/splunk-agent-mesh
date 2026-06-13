import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import HistorySidebar from '../components/HistorySidebar';

jest.mock('@splunk/themes', () => ({
    variables: new Proxy({}, { get: () => '0px' }),
}));
jest.mock('@splunk/react-ui/WaitSpinner', () => () => <span>Loading</span>);

const mockListInvestigations = jest.fn();
jest.mock('../services/apiClient', () => ({
    apiClient: {
        listInvestigations: (...args: any[]) => mockListInvestigations(...args),
    },
}));

const MOCK_ITEMS = [
    {
        investigation_id: 'inv-001',
        title: 'Log4Shell Exploitation Attempt',
        status: 'complete' as const,
        owner: 'alice',
        created_at: '2026-06-10T10:00:00+00:00',
        updated_at: '2026-06-10T10:30:00+00:00',
        completed_at: '2026-06-10T10:30:00+00:00',
        event_count: 8,
        artifact_count: 3,
    },
    {
        investigation_id: 'inv-002',
        title: 'Suspicious PowerShell',
        status: 'running' as const,
        owner: 'alice',
        created_at: '2026-06-10T11:00:00+00:00',
        updated_at: '2026-06-10T11:05:00+00:00',
        completed_at: null,
        event_count: 2,
        artifact_count: 1,
    },
];

beforeEach(() => {
    mockListInvestigations.mockResolvedValue({ investigations: MOCK_ITEMS });
});

test('renders collapsed by default with a toggle button', () => {
    render(<HistorySidebar activeInvestigationId={null} onSelect={jest.fn()} />);

    expect(screen.getByRole('button', { name: 'Show investigation history' })).toBeInTheDocument();
    expect(screen.queryByTestId('history-sidebar')).not.toBeInTheDocument();
});

test('expands on toggle click and shows history items', async () => {
    render(<HistorySidebar activeInvestigationId={null} onSelect={jest.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Show investigation history' }));

    expect(await screen.findByTestId('history-sidebar')).toBeInTheDocument();
    expect(screen.getByText('History')).toBeInTheDocument();
    expect(screen.getByText('Log4Shell Exploitation Attempt')).toBeInTheDocument();
    expect(screen.getByText('Suspicious PowerShell')).toBeInTheDocument();
});

test('collapses when close button is clicked', async () => {
    render(<HistorySidebar activeInvestigationId={null} onSelect={jest.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Show investigation history' }));
    await screen.findByTestId('history-sidebar');

    fireEvent.click(screen.getByRole('button', { name: 'Close history' }));
    expect(screen.queryByTestId('history-sidebar')).not.toBeInTheDocument();
});

test('calls onSelect when an item is clicked', async () => {
    const onSelect = jest.fn();
    render(<HistorySidebar activeInvestigationId={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByRole('button', { name: 'Show investigation history' }));
    await screen.findByText('Log4Shell Exploitation Attempt');

    fireEvent.click(screen.getByText('Log4Shell Exploitation Attempt'));
    expect(onSelect).toHaveBeenCalledWith('inv-001');
});

test('highlights the active investigation', async () => {
    render(<HistorySidebar activeInvestigationId="inv-001" onSelect={jest.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Show investigation history' }));
    await screen.findByText('Log4Shell Exploitation Attempt');

    const activeButton = screen.getByTitle('Log4Shell Exploitation Attempt');
    expect(activeButton).toBeInTheDocument();
});

test('shows empty message when no investigations exist', async () => {
    mockListInvestigations.mockResolvedValueOnce({ investigations: [] });

    render(<HistorySidebar activeInvestigationId={null} onSelect={jest.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Show investigation history' }));
    expect(await screen.findByText('No investigations yet.')).toBeInTheDocument();
});
