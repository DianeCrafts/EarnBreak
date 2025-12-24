export type LiveState = {
  ts: string;

  // Core scoring
  focus_score: number;
  time_speed: number;
  work_credits: number;
  credits_target: number;
  reasons: string[];

  // Active window (AUTHORITATIVE)
  active_app: string;
  active_title: string;
  active_is_browser: boolean;

  // Browser intent (ONLY meaningful if active_is_browser === true)
  browser_domain: string;
  browser_category: string;
  doomscroll_prob: number;

  // Task context
  primary_context: string;
  current_context: string;
  seconds_since_primary: number;
  support_trips_5m: number;
  successful_returns_5m: number;
  drift_events_5m: number;

  // Camera
  face_present: number;
  gaze_on_screen: number;
  head_motion: number;
  blink_rate_60s: number;
  yawn_prob: number;
};



export function connectLiveState(onState: (s: LiveState) => void) {
  const ws = new WebSocket("ws://localhost:8000/ws");

  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data) as LiveState;
      onState(data);
    } catch (e) {
      console.error("Bad WS message", e);
    }
  };

  ws.onopen = () => console.log("WS connected");
  ws.onclose = () => console.log("WS disconnected");

  return ws;
}
