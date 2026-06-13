import { renderHook, act } from '@testing-library/react';
import { useInvestigationUrl } from '../hooks/useInvestigationUrl';

beforeEach(() => {
    window.history.replaceState({}, '', '/app/splunk-agent-mesh/Investigations');
});

test('reads initial id from URL query parameter', () => {
    window.history.replaceState({}, '', '/app/splunk-agent-mesh/Investigations?id=inv-abc123');
    const { result } = renderHook(() => useInvestigationUrl());

    expect(result.current.initialId).toBe('inv-abc123');
    expect(result.current.currentId).toBe('inv-abc123');
});

test('returns null when no id parameter is present', () => {
    const { result } = renderHook(() => useInvestigationUrl());

    expect(result.current.initialId).toBeNull();
    expect(result.current.currentId).toBeNull();
});

test('setId updates the URL with pushState', () => {
    const { result } = renderHook(() => useInvestigationUrl());

    act(() => {
        result.current.setId('inv-new');
    });

    expect(result.current.currentId).toBe('inv-new');
    expect(window.location.search).toContain('id=inv-new');
});

test('setId with null removes the id parameter', () => {
    window.history.replaceState({}, '', '/app/splunk-agent-mesh/Investigations?id=inv-old');
    const { result } = renderHook(() => useInvestigationUrl());

    act(() => {
        result.current.setId(null);
    });

    expect(result.current.currentId).toBeNull();
    expect(window.location.search).not.toContain('id=');
});

test('setId preserves other query parameters', () => {
    window.history.replaceState({}, '', '/app/splunk-agent-mesh/Investigations?ns=search&prov=default');
    const { result } = renderHook(() => useInvestigationUrl());

    act(() => {
        result.current.setId('inv-test');
    });

    expect(window.location.search).toContain('ns=search');
    expect(window.location.search).toContain('prov=default');
    expect(window.location.search).toContain('id=inv-test');
});

test('responds to popstate events (back/forward)', () => {
    const { result } = renderHook(() => useInvestigationUrl());

    act(() => {
        result.current.setId('inv-first');
    });
    expect(result.current.currentId).toBe('inv-first');

    // Simulate browser back: manually restore the previous URL and fire popstate
    act(() => {
        window.history.replaceState({}, '', '/app/splunk-agent-mesh/Investigations');
        window.dispatchEvent(new PopStateEvent('popstate'));
    });

    expect(result.current.currentId).toBeNull();
});

test('setId with replace=true uses replaceState', () => {
    const pushSpy = jest.spyOn(window.history, 'pushState');
    const replaceSpy = jest.spyOn(window.history, 'replaceState');
    const { result } = renderHook(() => useInvestigationUrl());

    act(() => {
        result.current.setId('inv-replace', true);
    });

    expect(replaceSpy).toHaveBeenCalled();
    expect(pushSpy).not.toHaveBeenCalled();

    pushSpy.mockRestore();
    replaceSpy.mockRestore();
});
