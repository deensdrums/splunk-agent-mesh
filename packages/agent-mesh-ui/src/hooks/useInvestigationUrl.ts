import { useCallback, useEffect, useRef, useState } from 'react';

const PARAM = 'id';

function getIdFromUrl(): string | null {
    const params = new URLSearchParams(window.location.search);
    return params.get(PARAM) || null;
}

function buildUrl(id: string | null): string {
    const params = new URLSearchParams(window.location.search);
    if (id) {
        params.set(PARAM, id);
    } else {
        params.delete(PARAM);
    }
    const qs = params.toString();
    return `${window.location.pathname}${qs ? `?${qs}` : ''}`;
}

export interface UseInvestigationUrlResult {
    initialId: string | null;
    currentId: string | null;
    setId: (id: string | null, replace?: boolean) => void;
}

export function useInvestigationUrl(): UseInvestigationUrlResult {
    const initialRef = useRef(getIdFromUrl());
    const [currentId, setCurrentId] = useState<string | null>(initialRef.current);

    const setId = useCallback((id: string | null, replace = false) => {
        const url = buildUrl(id);
        if (replace) {
            window.history.replaceState({}, '', url);
        } else {
            window.history.pushState({}, '', url);
        }
        setCurrentId(id);
    }, []);

    useEffect(() => {
        const onPopState = () => {
            setCurrentId(getIdFromUrl());
        };
        window.addEventListener('popstate', onPopState);
        return () => window.removeEventListener('popstate', onPopState);
    }, []);

    return { initialId: initialRef.current, currentId, setId };
}
