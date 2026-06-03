import { useEffect, useRef, useCallback } from 'react';

type EventHandler = (...args: unknown[]) => void;

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 10;
const listeners = new Map<string, Set<EventHandler>>();
const globalListeners = new Set<(event: string, data: unknown) => void>();

function getWsUrl(): string {
  const host = window.location.hostname;
  const port = import.meta.env.VITE_WS_PORT || '8000';
  return import.meta.env.VITE_WS_URL || `ws://${host}:${port}/ws`;
}

function notify(event: string, data: unknown) {
  const handlers = listeners.get(event);
  if (handlers) {
    handlers.forEach((h) => h(data));
  }
  globalListeners.forEach((h) => h(event, data));
}

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  try {
    ws = new WebSocket(getWsUrl());

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
      reconnectAttempts = 0;
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        const evt = parsed.event || parsed.type || 'message';
        const data = parsed.data || parsed;
        notify(evt, data);
      } catch {
        // Not JSON, forward as raw message
        notify('raw', event.data);
      }
    };

    ws.onclose = (reason) => {
      console.log('[WebSocket] Disconnected:', reason);
      ws = null;
      scheduleReconnect();
    };

    ws.onerror = (err) => {
      console.error('[WebSocket] Connection error:', err);
    };
  } catch (err) {
    console.error('[WebSocket] Failed to create connection:', err);
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  if (reconnectAttempts >= maxReconnectAttempts) {
    console.log('[WebSocket] Max reconnect attempts reached');
    return;
  }
  reconnectAttempts++;
  const delay = Math.min(3000 * Math.pow(1.5, reconnectAttempts - 1), 30000);
  console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${maxReconnectAttempts})`);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

/** Subscribe to a WebSocket event */
export function subscribe(event: string, handler: EventHandler): () => void {
  const handlers = listeners.get(event) || new Set();
  handlers.add(handler);
  listeners.set(event, handlers);
  return () => {
    handlers.delete(handler);
    if (handlers.size === 0) listeners.delete(event);
  };
}

/** Subscribe to all events */
export function subscribeAll(handler: (event: string, data: unknown) => void): () => void {
  globalListeners.add(handler);
  return () => { globalListeners.delete(handler); };
}

/** Send a message */
export function emit(event: string, data?: unknown): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ event, data }));
  }
}

/** Check connection status */
export function isConnected(): boolean {
  return ws?.readyState === WebSocket.OPEN;
}

/** Disconnect */
export function disconnect(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }
  listeners.clear();
  globalListeners.clear();
  reconnectAttempts = 0;
}

/** Reconnect */
export function reconnect(): void {
  disconnect();
  connect();
}

/**
 * React hook for WebSocket events with auto cleanup.
 */
export function useWebSocket() {
  const connectedRef = useRef(false);

  useEffect(() => {
    connect();
    const interval = setInterval(() => {
      connectedRef.current = ws?.readyState === WebSocket.OPEN;
    }, 1000);
    return () => {
      clearInterval(interval);
    };
  }, []);

  return { subscribe, subscribeAll, emit, isConnected, reconnect };
}

export default { subscribe, subscribeAll, emit, isConnected, disconnect, reconnect };
