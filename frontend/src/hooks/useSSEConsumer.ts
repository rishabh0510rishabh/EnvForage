import { useState, useEffect, useCallback, useRef } from 'react';

interface SSEOptions {
    url: string;
    method?: 'GET' | 'POST';
    body?: any;
    headers?: Record<string, string>;
    maxRetries?: number;
    retryIntervalMs?: number;
}

interface SSEState {
    status: 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'error' | 'done';
    data: string;
    error: Error | null;
}

export function useSSEConsumer() {
    const [state, setState] = useState<SSEState>({ status: 'idle', data: '', error: null });
    const abortControllerRef = useRef<AbortController | null>(null);
    const retryCountRef = useRef(0);

    const disconnect = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        setState(s => ({ ...s, status: 'idle' }));
    }, []);

    const connect = useCallback(async (options: SSEOptions) => {
        disconnect();
        
        const { url, method = 'GET', body, headers, maxRetries = 5, retryIntervalMs = 2000 } = options;
        setState({ status: 'connecting', data: '', error: null });
        retryCountRef.current = 0;

        const attemptConnection = async () => {
            const controller = new AbortController();
            abortControllerRef.current = controller;

            try {
                const response = await fetch(url, {
                    method,
                    headers: {
                        'Accept': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                        ...(body ? { 'Content-Type': 'application/json' } : {}),
                        ...headers
                    },
                    body: body ? JSON.stringify(body) : undefined,
                    signal: controller.signal
                });

                if (!response.ok) {
                    throw new Error(`HTTP Error: ${response.status}`);
                }

                if (!response.body) {
                    throw new Error("ReadableStream not supported");
                }

                setState(s => ({ ...s, status: 'connected', error: null }));
                retryCountRef.current = 0; // Reset retries on successful connection

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let buffer = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || ''; // Keep incomplete lines in buffer

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const chunk = line.slice(6);
                            if (chunk === '[DONE]') {
                                setState(s => ({ ...s, status: 'done' }));
                                return;
                            }
                            try {
                                // Assume chunk could be JSON or raw text
                                const parsed = JSON.parse(chunk);
                                setState(s => ({ ...s, data: s.data + (parsed.text || parsed) }));
                            } catch {
                                // Raw text fallback
                                setState(s => ({ ...s, data: s.data + chunk }));
                            }
                        }
                    }
                }
                
                setState(s => ({ ...s, status: 'done' }));
                
            } catch (error: any) {
                if (error.name === 'AbortError') {
                    console.log('SSE connection aborted manually.');
                    return;
                }

                console.error('SSE Error:', error);
                
                if (retryCountRef.current < maxRetries) {
                    retryCountRef.current += 1;
                    setState(s => ({ ...s, status: 'reconnecting', error }));
                    console.log(`Reconnecting in ${retryIntervalMs}ms... (Attempt ${retryCountRef.current}/${maxRetries})`);
                    setTimeout(attemptConnection, retryIntervalMs);
                } else {
                    setState(s => ({ ...s, status: 'error', error }));
                }
            }
        };

        attemptConnection();
    }, [disconnect]);

    useEffect(() => {
        return () => disconnect();
    }, [disconnect]);

    return { ...state, connect, disconnect };
}
