import { useEffect, useRef } from "react";

/**
 * Invokes `callback` on a fixed interval, pausing when the browser tab is
 * hidden (via `document.visibilityState`) to avoid unnecessary network
 * requests.
 *
 * @param callback  The function to invoke on each tick.
 * @param intervalMs  Polling interval in milliseconds.
 * @param enabled  When `false`, no interval is started. Useful for
 *                 conditional polling (e.g. only while a run is active).
 */
export function usePolling(
  callback: () => void,
  intervalMs: number,
  enabled: boolean,
): void {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    if (!enabled) return;

    function tick() {
      if (document.visibilityState === "visible") {
        callbackRef.current();
      }
    }

    // Fire immediately on mount / when enabled changes.
    tick();

    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}
