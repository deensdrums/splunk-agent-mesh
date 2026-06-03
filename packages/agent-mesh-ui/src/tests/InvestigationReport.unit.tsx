import React from 'react';
import { act, fireEvent, render, screen, within } from '@testing-library/react';

import InvestigationReport from '../components/InvestigationReport';
import { AgentEvent, Artifact, InvestigationResult } from '../types';

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

const FINAL_EVENT: AgentEvent = {
    type: 'final',
    title: 'Investigation complete',
    text: 'The investigation is complete.',
    payload: {},
};

const HANDOFF_EVENT: AgentEvent = {
    type: 'handoff',
    title: 'Reporting agent requested',
    text: 'Delegating to the reporting agent.',
    payload: { sub_agent: 'executive_brief', task: 'summarize_findings' },
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

const SEARCH_EVENT: AgentEvent = {
    type: 'splunk_search',
    title: 'Encoded PowerShell search',
    text: 'Checking endpoint activity.',
    payload: {
        query: 'index=endpoint process_name=powershell.exe | timechart count',
        purpose: 'Confirm suspicious execution.',
        type: 'timechart',
    },
};

const SEARCH_ARTIFACT: Artifact = {
    id: 'artifact-test',
    type: 'splunk_search',
    agent_id: 'spl_hunter',
    title: 'Encoded PowerShell search',
    spl: 'index=endpoint process_name=powershell.exe | timechart count',
    earliest: '-4h',
    latest: 'now',
    sid: 'test-sid',
    status: 'done',
    fields: ['_time', 'count'],
    rows: [{ _time: '2026-05-21T14:02:00+00:00', count: '3' }],
    visualization: { kind: 'timechart', reason: 'SPL uses timechart.' },
};

describe('InvestigationReport console', () => {
    let resizeObservers: Array<{ callback: ResizeObserverCallback; disconnect: jest.Mock }> = [];

    beforeEach(() => {
        jest.useFakeTimers();
        resizeObservers = [];
        (globalThis as any).ResizeObserver = jest.fn().mockImplementation((callback: ResizeObserverCallback) => {
            const observer = {
                callback,
                observe: jest.fn(),
                disconnect: jest.fn(),
            };
            resizeObservers.push(observer);
            return observer;
        });
    });

    afterEach(() => {
        jest.useRealTimers();
        delete (globalThis as any).ResizeObserver;
    });

    test('renders focused first-use empty-state guidance before a run starts', () => {
        render(<InvestigationReport descriptors={[]} result={null} running={false} />);

        expect(screen.getByText('Start an investigation')).toBeInTheDocument();
        expect(screen.getByText(/The Threat Hunter will stream evidence/i)).toBeInTheDocument();
        expect(screen.queryByText(/Run an investigation to populate the report/i)).not.toBeInTheDocument();
    });

    test('renders a pending Threat Hunter console before agent order arrives', () => {
        const result: InvestigationResult = {
            id: 'inv-pending',
            status: 'running',
            agent_order: [],
            agents: {},
        };

        render(<InvestigationReport descriptors={[]} result={result} running />);

        expect(screen.getAllByText('Threat Hunter')).toHaveLength(2);
        expect(screen.getByText('Starting investigation…')).toBeInTheDocument();
        expect(screen.getByTestId('transcript-status')).toHaveTextContent('Investigationrunning');
    });

    test('renders optional input summary in the Threat Hunter header', () => {
        render(
            <InvestigationReport
                descriptors={[]}
                result={resultWithEvents([EVENT_ONE])}
                running={false}
                inputSummary={<span>Edit Inputs</span>}
            />
        );

        expect(screen.getByText('Edit Inputs')).toBeInTheDocument();
    });

    test('shows progressive event count', () => {
        render(<InvestigationReport descriptors={[]} result={resultWithEvents([EVENT_ONE])} running />);

        act(() => {
            jest.advanceTimersByTime(330);
        });

        expect(screen.getByTestId('transcript-status')).toHaveTextContent('Events1/1');
    });

    test('keeps the transcript shell and event cards full width from first reveal', () => {
        render(<InvestigationReport descriptors={[]} result={resultWithEvents([EVENT_ONE])} running />);

        act(() => {
            jest.advanceTimersByTime(330);
        });

        expect(screen.getByTestId('transcript-shell')).toBeInTheDocument();
        expect(screen.getByTestId('event-card')).toBeInTheDocument();
    });

    test('auto-follows new events until the analyst scrolls upward', () => {
        const { rerender } = render(
            <InvestigationReport descriptors={[]} result={resultWithEvents([EVENT_ONE])} running />
        );
        const scrollArea = screen.getByTestId('transcript-scroll');
        Object.defineProperties(scrollArea, {
            clientHeight: { configurable: true, value: 100 },
            scrollHeight: { configurable: true, value: 1000 },
            scrollTop: { configurable: true, value: 0, writable: true },
        });

        act(() => {
            jest.advanceTimersByTime(330);
        });
        expect(scrollArea.scrollTop).toBe(1000);

        scrollArea.scrollTop = 100;
        fireEvent.wheel(scrollArea);
        fireEvent.scroll(scrollArea);
        rerender(
            <InvestigationReport
                descriptors={[]}
                result={resultWithEvents([EVENT_ONE, EVENT_TWO])}
                running
            />
        );
        act(() => {
            jest.advanceTimersByTime(330);
        });

        expect(scrollArea.scrollTop).toBe(100);
        expect(within(scrollArea).getByText('Suspicious activity found.')).toBeInTheDocument();
    });

    test('keeps following bottom when rendered search content expands without user scroll intent', () => {
        const result = resultWithEvents([SEARCH_EVENT]);
        result.artifacts = [{ ...SEARCH_ARTIFACT, status: 'running', _revision: 2 }];

        render(<InvestigationReport descriptors={[]} result={result} running />);
        const scrollArea = screen.getByTestId('transcript-scroll');
        Object.defineProperties(scrollArea, {
            clientHeight: { configurable: true, value: 100 },
            scrollHeight: { configurable: true, value: 1000 },
            scrollTop: { configurable: true, value: 0, writable: true },
        });

        act(() => {
            jest.advanceTimersByTime(330);
        });
        expect(scrollArea.scrollTop).toBe(1000);

        Object.defineProperty(scrollArea, 'scrollHeight', { configurable: true, value: 1400 });
        scrollArea.scrollTop = 1000;
        act(() => {
            resizeObservers[0].callback([], resizeObservers[0] as unknown as ResizeObserver);
        });

        expect(scrollArea.scrollTop).toBe(1400);
    });

    test('renders search results inside one blue event card without duplicating SPL or title', () => {
        const result = resultWithEvents([SEARCH_EVENT]);
        result.artifacts = [SEARCH_ARTIFACT];

        render(<InvestigationReport descriptors={[]} result={result} running />);
        act(() => {
            jest.advanceTimersByTime(330);
        });

        const scrollArea = screen.getByTestId('transcript-scroll');
        expect(within(scrollArea).getAllByText('Encoded PowerShell search')).toHaveLength(1);
        expect(within(scrollArea).getAllByText('index=endpoint process_name=powershell.exe | timechart count')).toHaveLength(1);
        expect(within(scrollArea).getByText('Column')).toBeInTheDocument();
        expect(within(scrollArea).getByText('timechart · done · SID test-sid')).toBeInTheDocument();
    });

    test('renders preview chart with a running indicator before search completion', () => {
        const result = resultWithEvents([SEARCH_EVENT]);
        result.artifacts = [{ ...SEARCH_ARTIFACT, status: 'running', _revision: 2 }];

        render(<InvestigationReport descriptors={[]} result={result} running />);
        act(() => {
            jest.advanceTimersByTime(330);
        });

        const scrollArea = screen.getByTestId('transcript-scroll');
        expect(within(scrollArea).getByText('Search running. Preview results update automatically.')).toBeInTheDocument();
        expect(within(scrollArea).getByText('Column')).toBeInTheDocument();
        expect(within(scrollArea).queryByText('Search complete. Showing final results.')).not.toBeInTheDocument();
    });

    test('hides the thinking indicator while a search is running', () => {
        const result = resultWithEvents([SEARCH_EVENT]);
        result.artifacts = [{ ...SEARCH_ARTIFACT, status: 'running', _revision: 2 }];

        render(<InvestigationReport descriptors={[]} result={result} running />);
        act(() => {
            jest.advanceTimersByTime(330);
        });

        expect(screen.queryByTestId('thinking-indicator')).not.toBeInTheDocument();
    });

    test('reports interpreting results once a search completes', () => {
        const result = resultWithEvents([SEARCH_EVENT]);
        result.artifacts = [SEARCH_ARTIFACT]; // status: 'done'

        render(<InvestigationReport descriptors={[]} result={result} running />);
        act(() => {
            jest.advanceTimersByTime(330);
        });

        expect(screen.getByTestId('thinking-indicator')).toHaveTextContent('Interpreting results');
    });

    test('reports finalizing after a handoff event is revealed', () => {
        render(
            <InvestigationReport
                descriptors={[]}
                result={resultWithEvents([EVENT_ONE, HANDOFF_EVENT])}
                running
            />
        );
        // Each reveal step needs its own act() so the next timer is scheduled.
        act(() => {
            jest.advanceTimersByTime(330);
        });
        act(() => {
            jest.advanceTimersByTime(330);
        });

        expect(screen.getByTestId('thinking-indicator')).toHaveTextContent('Finalizing');
    });

    test('prefers the backend phase label over inference', () => {
        const result = resultWithEvents([EVENT_ONE, HANDOFF_EVENT]);
        result.agents.spl_hunter.phase = 'delegating';

        render(<InvestigationReport descriptors={[]} result={result} running />);
        act(() => {
            jest.advanceTimersByTime(330);
        });

        expect(screen.getByTestId('thinking-indicator')).toHaveTextContent('Consulting the reporting agent');
    });

    test('shows a working label while active and hides it after the final event is revealed', () => {
        const { rerender } = render(
            <InvestigationReport descriptors={[]} result={resultWithEvents([EVENT_ONE])} running />
        );
        act(() => {
            jest.advanceTimersByTime(330);
        });
        expect(screen.getByTestId('thinking-indicator')).toHaveTextContent('Investigating');

        rerender(
            <InvestigationReport
                descriptors={[]}
                result={resultWithEvents([EVENT_ONE, FINAL_EVENT])}
                running
            />
        );
        act(() => {
            jest.advanceTimersByTime(330);
        });
        expect(screen.queryByTestId('thinking-indicator')).not.toBeInTheDocument();
    });
});
