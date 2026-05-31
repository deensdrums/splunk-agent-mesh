import React from 'react';
import { act, fireEvent, render, screen, within } from '@testing-library/react';

import InvestigationReport from '../components/InvestigationReport';
import { AgentEvent, InvestigationResult } from '../types';

jest.mock('@splunk/themes', () => ({
    variables: new Proxy({}, { get: () => '0px' }),
}));
jest.mock('@splunk/react-ui/Button', () => ({ label, onClick }: any) => (
    <button type="button" onClick={onClick}>
        {label}
    </button>
));
jest.mock('@splunk/react-ui/Message', () => ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
));
jest.mock('@splunk/react-ui/WaitSpinner', () => () => <span>Loading</span>);
jest.mock('react-markdown', () => ({ children }: { children: React.ReactNode }) => <div>{children}</div>);
jest.mock('remark-gfm', () => () => null);
jest.mock('rehype-sanitize', () => () => null);
jest.mock('@splunk/visualizations/Column', () => () => <div>Column</div>);
jest.mock('@splunk/visualizations/Line', () => () => <div>Line</div>);
jest.mock('@splunk/visualizations/Pie', () => () => <div>Pie</div>);

const EVENT_ONE: AgentEvent = {
    type: 'narration',
    title: 'Starting',
    text: 'Beginning the investigation.',
    payload: {},
};

const EVENT_TWO: AgentEvent = {
    type: 'finding',
    title: 'Finding',
    text: 'Suspicious activity found.',
    payload: { confidence: 'high' },
};

function resultWithEvents(events: AgentEvent[]): InvestigationResult {
    return {
        id: 'inv-test',
        status: 'running',
        agent_order: ['spl_hunter'],
        agents: {
            spl_hunter: {
                agent_id: 'spl_hunter',
                display_name: 'Threat Hunter',
                status: 'iterating',
                events,
                markdown: '',
            },
        },
        artifacts: [],
    };
}

describe('InvestigationReport console', () => {
    beforeEach(() => {
        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    test('renders a pending Threat Hunter console before agent order arrives', () => {
        const result: InvestigationResult = {
            id: 'inv-pending',
            status: 'running',
            agent_order: [],
            agents: {},
        };

        render(<InvestigationReport descriptors={[]} result={result} running onClear={jest.fn()} />);

        expect(screen.getByText('Investigation Console')).toBeInTheDocument();
        expect(screen.getAllByText('Threat Hunter')).toHaveLength(2);
        expect(screen.getByText('Starting investigation…')).toBeInTheDocument();
        expect(screen.getByTestId('transcript-status')).toHaveTextContent('Investigationrunning');
    });

    test('shows progressive event count and invokes clear from the toolbar', () => {
        const onClear = jest.fn();
        render(<InvestigationReport descriptors={[]} result={resultWithEvents([EVENT_ONE])} running onClear={onClear} />);

        act(() => {
            jest.advanceTimersByTime(300);
        });

        expect(screen.getByTestId('transcript-status')).toHaveTextContent('Events1/1');
        fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
        expect(onClear).toHaveBeenCalledTimes(1);
    });

    test('auto-follows new events until the analyst scrolls upward', () => {
        const { rerender } = render(
            <InvestigationReport descriptors={[]} result={resultWithEvents([EVENT_ONE])} running onClear={jest.fn()} />
        );
        const scrollArea = screen.getByTestId('transcript-scroll');
        Object.defineProperties(scrollArea, {
            clientHeight: { configurable: true, value: 100 },
            scrollHeight: { configurable: true, value: 1000 },
            scrollTop: { configurable: true, value: 0, writable: true },
        });

        act(() => {
            jest.advanceTimersByTime(300);
        });
        expect(scrollArea.scrollTop).toBe(1000);

        scrollArea.scrollTop = 100;
        fireEvent.scroll(scrollArea);
        rerender(
            <InvestigationReport
                descriptors={[]}
                result={resultWithEvents([EVENT_ONE, EVENT_TWO])}
                running
                onClear={jest.fn()}
            />
        );
        act(() => {
            jest.advanceTimersByTime(300);
        });

        expect(scrollArea.scrollTop).toBe(100);
        expect(within(scrollArea).getByText('Suspicious activity found.')).toBeInTheDocument();
    });
});
