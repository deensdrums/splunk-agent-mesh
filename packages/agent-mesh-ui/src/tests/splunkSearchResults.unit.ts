import { getData } from '@splunk/splunk-utils/search';
import { pollSplunkSearchResults } from '../services/splunkSearchResults';
import { SearchArtifact } from '../types';

jest.mock('@splunk/splunk-utils/config', () => ({ isAvailable: true }));
jest.mock('@splunk/splunk-utils/search', () => ({ getData: jest.fn() }));

const artifact: SearchArtifact = {
    id: 'artifact-1',
    type: 'splunk_search',
    agent_id: 'spl_hunter',
    title: 'Counts',
    spl: 'index=main | stats count',
    earliest: '-24h',
    latest: 'now',
    sid: 'sid-1',
    status: 'running',
    fields: [],
    rows: [],
    visualization: { kind: 'bar', reason: 'test' },
};

beforeEach(() => {
    jest.clearAllMocks();
});

test('fetches final Splunk Web results immediately when the search is done', async () => {
    (getData as jest.Mock)
        .mockResolvedValueOnce({ entry: [{ content: { dispatchState: 'DONE' } }] })
        .mockResolvedValueOnce({ fields: [{ name: 'count' }], results: [{ count: '2' }] });
    const updates: SearchArtifact[] = [];

    pollSplunkSearchResults(artifact, (update) => updates.push(update), jest.fn());
    await new Promise((resolve) => {setTimeout(resolve, 0);});

    expect(getData).toHaveBeenNthCalledWith(1, 'sid-1');
    expect(getData).toHaveBeenNthCalledWith(2, 'sid-1', 'results', { count: 100 });
    expect(updates[0]).toMatchObject({ status: 'done', fields: ['count'], rows: [{ count: '2' }] });
});

test('paints preview rows before fetching terminal results', async () => {
    jest.useFakeTimers();
    (getData as jest.Mock)
        .mockResolvedValueOnce({ entry: [{ content: { dispatchState: 'RUNNING' } }] })
        .mockResolvedValueOnce({ fields: [{ name: 'count' }], results: [{ count: '1' }] })
        .mockResolvedValueOnce({ entry: [{ content: { dispatchState: 'DONE' } }] })
        .mockResolvedValueOnce({ fields: [{ name: 'count' }], results: [{ count: '2' }] });
    const updates: SearchArtifact[] = [];

    pollSplunkSearchResults(artifact, (update) => updates.push(update), jest.fn());
    await Promise.resolve();
    await Promise.resolve();
    expect(updates[0]).toMatchObject({ status: 'running', rows: [{ count: '1' }] });

    await jest.advanceTimersByTimeAsync(750);
    expect(updates[1]).toMatchObject({ status: 'done', rows: [{ count: '2' }] });
    jest.useRealTimers();
});
