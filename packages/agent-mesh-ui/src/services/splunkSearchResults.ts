import { getData } from '@splunk/splunk-utils/search';
import { SearchArtifact } from '../types';
import { isSplunkWebRuntime } from './splunkWeb';

const POLL_INTERVAL_MS = 750;
export const canPollSplunkWebResults = isSplunkWebRuntime();

interface SearchResultPayload {
    fields?: Array<{ name?: string }>;
    results?: Record<string, unknown>[];
    messages?: Array<{ type?: string; text?: string }>;
}

function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

function normalizeResult(sourceArtifact: SearchArtifact, payload: SearchResultPayload, status: 'running' | 'done'): SearchArtifact {
    const rows = payload.results || [];
    const fields = (payload.fields || []).map((field) => field.name).filter((field): field is string => Boolean(field));
    return {
        ...sourceArtifact,
        status,
        fields: fields.length > 0 ? fields : sourceArtifact.fields,
        rows,
        messages: (payload.messages || []).map((message) => `${message.type || 'INFO'}: ${message.text || ''}`.trim()),
        browser_results_error: null,
    };
}

function isDone(statusPayload: any): boolean {
    const content = statusPayload?.entry?.[0]?.content || {};
    return Boolean(content.isDone) || content.dispatchState === 'DONE';
}

function terminalError(statusPayload: any): string | null {
    const dispatchState = statusPayload?.entry?.[0]?.content?.dispatchState;
    if (['FAILED', 'INTERNAL_CANCEL', 'USER_CANCEL', 'BAD_INPUT_CANCEL', 'QUIT'].includes(dispatchState)) {
        return `Splunk search ended: ${dispatchState}`;
    }
    return null;
}

export function pollSplunkSearchResults(
    artifact: SearchArtifact,
    onUpdate: (update: SearchArtifact) => void,
    onError: (message: string) => void,
): { close: () => void } {
    let closed = false;
    let consecutiveErrors = 0;
    let errorReported = false;

    const run = async () => {
        while (!closed) {
            try {
                // eslint-disable-next-line no-await-in-loop
                const status = await getData(artifact.sid as string);
                const jobError = terminalError(status);
                if (jobError) {
                    onError(jobError);
                    return;
                }
                if (isDone(status)) {
                    // eslint-disable-next-line no-await-in-loop
                    const results = await getData(artifact.sid as string, 'results', { count: 100 });
                    if (!closed) {onUpdate(normalizeResult(artifact, results || {}, 'done'));}
                    return;
                }
                // eslint-disable-next-line no-await-in-loop
                const preview = await getData(artifact.sid as string, 'results_preview', { count: 100 });
                if (!closed) {onUpdate(normalizeResult(artifact, preview || {}, 'running'));}
                consecutiveErrors = 0;
                errorReported = false;
            } catch (error) {
                consecutiveErrors += 1;
                if (!closed && consecutiveErrors >= 3 && !errorReported) {
                    onError(error instanceof Error ? error.message : 'Unable to retrieve Splunk search results.');
                    errorReported = true;
                }
            }
            // eslint-disable-next-line no-await-in-loop
            await sleep(POLL_INTERVAL_MS);
        }
    };

    run();
    return { close: () => {closed = true;} };
}
