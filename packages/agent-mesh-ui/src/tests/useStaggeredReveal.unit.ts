import { act, renderHook } from '@testing-library/react';

import { useStaggeredReveal } from '../hooks/useStaggeredReveal';

jest.useFakeTimers();

test('reveals items one at a time up to total', () => {
    const { result } = renderHook(({ total, key }) => useStaggeredReveal(total, 300, key), {
        initialProps: { total: 3, key: 'run-1' },
    });

    expect(result.current).toBe(0);
    act(() => {
        jest.advanceTimersByTime(300);
    });
    expect(result.current).toBe(1);
    act(() => {
        jest.advanceTimersByTime(300);
    });
    expect(result.current).toBe(2);
    act(() => {
        jest.advanceTimersByTime(300);
    });
    expect(result.current).toBe(3);
});

// Each reveal step needs its own act() so the effect that schedules the next
// timer flushes before the timer is advanced again.
function step() {
    act(() => {
        jest.advanceTimersByTime(300);
    });
}

test('never exceeds total', () => {
    const { result } = renderHook(({ total, key }) => useStaggeredReveal(total, 300, key), {
        initialProps: { total: 2, key: 'run-1' },
    });

    step(); // 1
    step(); // 2
    step(); // would be 3, but capped at total
    expect(result.current).toBe(2);
});

test('restarts from zero when the reset key changes', () => {
    const { result, rerender } = renderHook(({ total, key }) => useStaggeredReveal(total, 300, key), {
        initialProps: { total: 2, key: 'run-1' },
    });

    step(); // 1
    step(); // 2
    expect(result.current).toBe(2);

    act(() => {
        rerender({ total: 2, key: 'run-2' });
    });
    expect(result.current).toBe(0);

    step();
    expect(result.current).toBe(1);
});
