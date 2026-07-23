import { useEffect, useRef, useState } from "react";
import type { OverheadResponse } from "../types/aircraft";

const FALLBACK_POLL_MS = 4000;
const RECONNECT_DELAY_MS = 3000;

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/overhead`;
}

/**
 * Streams the current "overhead" snapshot to the UI.
 *
 * Tries a WebSocket connection first (near-instant updates, one connection
 * instead of a request every few seconds). If the socket can't connect or
 * drops (e.g. a reverse proxy without WS support), it transparently falls
 * back to REST polling so the app degrades gracefully rather than going
 * blank.
 */
export function useAircraftData() {
  const [data, setData] = useState<OverheadResponse | null>(null);
  const [connected, setConnected] = useState(false);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;

    const startPolling = () => {
      if (pollTimer.current) return;
      const poll = async () => {
        try {
          const resp = await fetch("/api/overhead");
          if (resp.ok) {
            const json = (await resp.json()) as OverheadResponse;
            if (!cancelled) setData(json);
          }
        } catch {
          // Network hiccup - keep the last good frame on screen.
        }
      };
      poll();
      pollTimer.current = setInterval(poll, FALLBACK_POLL_MS);
    };

    const stopPolling = () => {
      if (pollTimer.current) {
        clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
    };

    const connectSocket = () => {
      if (cancelled) return;
      const socket = new WebSocket(wsUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        if (cancelled) return;
        setConnected(true);
        stopPolling();
      };

      socket.onmessage = (event) => {
        if (cancelled) return;
        try {
          setData(JSON.parse(event.data));
        } catch {
          /* ignore malformed frame */
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        setConnected(false);
        startPolling();
        setTimeout(connectSocket, RECONNECT_DELAY_MS);
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connectSocket();
    startPolling(); // ensures data on screen immediately while the socket handshakes

    return () => {
      cancelled = true;
      stopPolling();
      socketRef.current?.close();
    };
  }, []);

  return { data, connected };
}
