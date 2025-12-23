export type LiveState = {
  ts: string;
  focus_score: number;
  time_speed: number;
  work_credits: number;
  credits_target: number;
  reasons: string[];
  browser_domain: string,
  browser_category: string,
  doomscroll_prob: number

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
