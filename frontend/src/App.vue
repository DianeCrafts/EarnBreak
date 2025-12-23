<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed } from "vue";
import { connectLiveState, type LiveState } from "./services/ws";

const state = ref<LiveState | null>(null);
let ws: WebSocket | null = null;

onMounted(() => {
  ws = connectLiveState((s) => (state.value = s));
});

onBeforeUnmount(() => {
  ws?.close();
});

const progressPct = computed(() => {
  if (!state.value) return 0;
  return Math.min(100, (state.value.work_credits / state.value.credits_target) * 100);
});
</script>

<template>
  <div style="font-family: system-ui; padding: 24px; max-width: 780px; margin: 0 auto;">
    <h1>Earn Break</h1>

    <div v-if="!state">Connecting…</div>

    <div v-else>
      <p><strong>Focus score:</strong> {{ state.focus_score }}</p>
      <p><strong>Time speed:</strong> {{ state.time_speed }}x</p>

      <div style="margin: 16px 0;">
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
          <span><strong>Break progress</strong></span>
          <span>{{ progressPct.toFixed(1) }}%</span>
        </div>
        <div style="height: 14px; background:#eee; border-radius: 999px; overflow:hidden;">
          <div :style="{ height: '100%', width: progressPct + '%', background: '#111' }"></div>
        </div>
      </div>

      <div style="margin-top: 16px;">
        <strong>Why:</strong>
        <ul>
          <li v-for="r in state.reasons" :key="r">{{ r }}</li>
        </ul>
      </div>
      <p><strong>Context:</strong> {{ state.browser_category }} ({{ state.browser_domain }})</p>
      <p><strong>Doomscroll:</strong> {{ state.doomscroll_prob }}</p>

      <p><strong>Primary:</strong> {{ state.primary_context }} | <strong>Now:</strong> {{ state.current_context }}</p>
      <p><strong>Time since primary:</strong> {{ state.seconds_since_primary }}s</p>
      <p><strong>Support trips (5m):</strong> {{ state.support_trips_5m }},
        <strong>successful returns:</strong> {{ state.successful_returns_5m }},
        <strong>drifts:</strong> {{ state.drift_events_5m }}
      </p>
      <h3>Camera</h3>
      <p><strong>Face present:</strong> {{ state.face_present }}</p>
      <p><strong>Gaze on screen (proxy):</strong> {{ state.gaze_on_screen }}</p>
      <p><strong>Head motion (proxy):</strong> {{ state.head_motion }}</p>
      <p><strong>Blinks (last 60s):</strong> {{ state.blink_rate_60s }}</p>
      <p><strong>Yawn probability (proxy):</strong> {{ state.yawn_prob }}</p>



      <small style="opacity:0.7;">Last update (UTC): {{ state.ts }}</small>
    </div>
  </div>
</template>
