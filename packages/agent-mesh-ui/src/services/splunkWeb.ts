import { isAvailable as isSplunkConfigAvailable } from '@splunk/splunk-utils/config';
import { createRESTURL } from '@splunk/splunk-utils/url';

const SPLUNK_WEB_PATH = /^(.*\/[a-z]{2}-[A-Z]{2})\/(?:app|manager)\//;

export function isSplunkWebRuntime(): boolean {
    if (isSplunkConfigAvailable) {
        return true;
    }
    return typeof window !== 'undefined' && SPLUNK_WEB_PATH.test(window.location.pathname);
}

export function createSplunkWebRESTURL(endpoint: string): string {
    if (isSplunkConfigAvailable) {
        return createRESTURL(endpoint);
    }
    const match = typeof window !== 'undefined' && window.location.pathname.match(SPLUNK_WEB_PATH);
    if (!match) {
        return createRESTURL(endpoint);
    }
    return `${match[1]}/splunkd/__raw/services/${endpoint.replace(/^\/+/, '')}`;
}
