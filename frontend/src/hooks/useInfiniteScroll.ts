
// --- Advanced Infinite Scroll Hook ---
import { useEffect, useRef, useState, useCallback } from 'react';

interface UseInfiniteScrollOptions {
    threshold?: number;
    rootMargin?: string;
    enabled?: boolean;
}

export function useInfiniteScroll(
    onLoadMore: () => Promise<void>,
    options: UseInfiniteScrollOptions = {}
) {
    const { threshold = 0.1, rootMargin = '100px', enabled = true } = options;
    const [isLoading, setIsLoading] = useState(false);
    const observerTarget = useRef<HTMLDivElement | null>(null);

    const handleObserver = useCallback(
        async (entries: IntersectionObserverEntry[]) => {
            const [target] = entries;
            if (target.isIntersecting && enabled && !isLoading) {
                setIsLoading(true);
                try {
                    await onLoadMore();
                } catch (error) {
                    console.error('Infinite scroll fetch failed:', error);
                } finally {
                    setIsLoading(false);
                }
            }
        },
        [enabled, isLoading, onLoadMore]
    );

    useEffect(() => {
        const element = observerTarget.current;
        if (!element) return;

        const observer = new IntersectionObserver(handleObserver, {
            root: null,
            rootMargin,
            threshold,
        });

        observer.observe(element);

        return () => {
            if (element) observer.unobserve(element);
        };
    }, [handleObserver, rootMargin, threshold]);

    return { observerTarget, isLoading };
}
