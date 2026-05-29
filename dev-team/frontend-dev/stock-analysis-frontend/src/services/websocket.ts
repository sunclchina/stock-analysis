import { useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import type { WarningItem } from '../types/warning';
import type { StockSnapshot } from '../types/dashboard';

export type WsEventMap = {
  'market:update': (data: StockSnapshot[]) => void;
  'warning:trigger': (data: WarningItem) => void;
  'warning:resolve': (data: { id: string }) => void;
  'config:changed': (data: { type: string }) => void;
  'heartbeat': (data: { timestamp: number }) => void;
};

type EventHandler = (...args: unknown[]) => void;

let socket: Socket | null = null;
const listeners = new Map<string, Set<EventHandler>>();

function getSocket(): Socket {
  if (!socket) {
    const wsUrl = import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8080/ws`;
    socket = io(wsUrl, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 3000,
    });

    socket.on('connect', () => {
      console.log('[WebSocket] Connected');
    });

    socket.on('disconnect', (reason) => {
      console.log('[WebSocket] Disconnected:', reason);
    });

    socket.on('connect_error', (err) => {
      console.error('[WebSocket] Connection error:', err.message);
    });

    // Forward all events to local listeners
    const originalOn = socket.on.bind(socket);
    socket.on = ((event: string, handler: EventHandler) => {
      listeners.get(event)?.add(handler);
      return socket;
    }) as typeof socket.on;

    socket.onAny((event: string, ...args: unknown[]) => {
      const handlers = listeners.get(event);
      if (handlers) {
        handlers.forEach((h) => h(...args));
      }
    });
  }
  return socket;
}

/** Subscribe to a WebSocket event */
export function subscribe<K extends keyof WsEventMap>(
  event: K,
  handler: WsEventMap[K]
): () => void {
  const ws = getSocket();
  const handlers = listeners.get(event) || new Set();
  handlers.add(handler as EventHandler);
  listeners.set(event, handlers);

  return () => {
    handlers.delete(handler as EventHandler);
    if (handlers.size === 0) {
      listeners.delete(event);
    }
  };
}

/** Send a WebSocket event */
export function emit(event: string, data: unknown): void {
  const ws = getSocket();
  if (ws.connected) {
    ws.emit(event, data);
  }
}

/** Check connection status */
export function isConnected(): boolean {
  return socket?.connected ?? false;
}

/** Disconnect socket */
export function disconnect(): void {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
  listeners.clear();
}

/** Reconnect socket */
export function reconnect(): void {
  disconnect();
  getSocket();
}

/**
 * React hook for WebSocket events with auto cleanup.
 * Returns connection status.
 */
export function useWebSocket() {
  const connectedRef = useRef(false);

  useEffect(() => {
    const ws = getSocket();

    const onConnect = () => { connectedRef.current = true; };
    const onDisconnect = () => { connectedRef.current = false; };

    ws.on('connect', onConnect);
    ws.on('disconnect', onDisconnect);

    return () => {
      ws.off('connect', onConnect);
      ws.off('disconnect', onDisconnect);
    };
  }, []);

  return {
    subscribe,
    emit,
    isConnected: () => socket?.connected ?? false,
    reconnect,
  };
}

export default getSocket;
