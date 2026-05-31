import { useEffect, useState } from 'react';

/**
 * Reveals items one at a time on a timer, even when the underlying data grows
 * in bursts. The threat hunter streams its events in batches (a single model
 * response can carry several events), so this presentation-only hook walks a
 * "revealed count" up toward `total`, letting the UI paint cards one-by-one.
 *
 * @param total      The number of items currently available to reveal.
 * @param intervalMs Delay between revealing successive items.
 * @param resetKey   When this changes (e.g. a new investigation id), the reveal
 *                   restarts from zero.
 * @returns The number of items that should currently be rendered.
 */
export function useStaggeredReveal(total: number, intervalMs: number, resetKey: unknown): number {
    const [revealed, setRevealed] = useState(0);

    // Restart the reveal whenever a new run begins.
    useEffect(() => {
        setRevealed(0);
    }, [resetKey]);

    useEffect(() => {
        if (revealed >= total) {
            return undefined;
        }
        const timer = setTimeout(() => {
            setRevealed((current) => Math.min(current + 1, total));
        }, intervalMs);
        return () => clearTimeout(timer);
    }, [revealed, total, intervalMs]);

    return Math.min(revealed, total);
}

export default useStaggeredReveal;
