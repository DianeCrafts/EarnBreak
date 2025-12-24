
<script lang="ts">
import { ref, onMounted } from "vue";
import { type LiveState } from "./services/ws";
export default {
  setup() {
    const state = ref<LiveState | null>(null);
    const labelRequest = ref<any>(null);
    const ws = ref<WebSocket | null>(null);

    function adaptBackendLiveState(raw: any): LiveState {
      return {
        ts: raw.ts,

        // legacy / unused (kept for ws.ts compatibility)
        focus_score: 0,
        time_speed: 1,
        work_credits: 0,
        credits_target: 0,
        reasons: [],

        active_app: raw.active_app,
        active_title: raw.active_title,
        active_is_browser: raw.active_is_browser,

        browser_domain: raw.browser_domain,
        browser_category: raw.browser_category,
        doomscroll_prob: raw.doomscroll_prob,

        primary_context: "",
        current_context: "",
        seconds_since_primary: 0,
        support_trips_5m: 0,
        successful_returns_5m: 0,
        drift_events_5m: 0,

        face_present: raw.face_present,
        gaze_on_screen: raw.gaze_on_screen,
        head_motion: raw.head_motion,
        blink_rate_60s: 0,
        yawn_prob: 0,
      };
    }

    function sendLabel(label: string) {
      if (!ws.value) return;
      ws.value.send(JSON.stringify({ label }));
      labelRequest.value = null;
    }

    onMounted(() => {
      ws.value = new WebSocket("ws://localhost:8000/ws");

      ws.value.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);

          if (msg.type === "live_state") {
            state.value = adaptBackendLiveState(msg.data);
          }

          if (msg.type === "label_request") {
            labelRequest.value = msg;
          }
        } catch (e) {
          console.error("Bad WS message", e);
        }
      };

      ws.value.onopen = () => console.log("WS connected");
      ws.value.onclose = () => console.log("WS disconnected");
    });

    return {
      state,
      labelRequest,
      sendLabel,
    };
  },
};
</script>

<template>
  <div style="font-family: system-ui; padding: 24px; max-width: 900px; margin: 0 auto;">
    <h1>Earn Break — Data Collection Mode</h1>

    <div v-if="!state">Connecting…</div>

    <div v-else>
      <h2>Live state</h2>

      <p>
        <strong>App:</strong> {{ state.active_app }}<br />
        <strong>Title:</strong> {{ state.active_title || "(no title)" }}<br />
        <strong>Is browser:</strong>
        <span :style="{ color: state.active_is_browser ? '#dc2626' : '#16a34a' }">
          {{ state.active_is_browser }}
        </span>
      </p>

      <div v-if="state.active_is_browser">
        <p>
          <strong>Category:</strong> {{ state.browser_category }}<br />
          <strong>Domain:</strong> {{ state.browser_domain }}<br />
          <strong>Doomscroll:</strong> {{ state.doomscroll_prob }}
        </p>
      </div>

      <p>
        <strong>Face present:</strong> {{ state.face_present }}<br />
        <strong>Gaze on screen:</strong> {{ state.gaze_on_screen }}<br />
        <strong>Head motion:</strong> {{ state.head_motion }}
      </p>

      <small style="opacity:0.6;">
        Last update (UTC): {{ state.ts }}
      </small>
    </div>

    <!-- Label modal -->
    <div
      v-if="labelRequest"
      style="position:fixed; inset:0; background:rgba(0,0,0,.4); display:flex; align-items:center; justify-content:center;"
    >
      <div style="background:white; padding:24px; border-radius:12px; width:420px;">
        <h2>How was the last window?</h2>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:16px;">
          <button @click="sendLabel('Focused')">Focused</button>
          <button @click="sendLabel('Distracted')">Distracted</button>
          <button @click="sendLabel('Idle')">Idle</button>
          <button @click="sendLabel('Neutral')">Neutral</button>
        </div>
      </div>
    </div>
  </div>
</template>
