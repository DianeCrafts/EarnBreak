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
  <div style="font-family: system-ui; padding: 24px; max-width: 900px; margin: 0 auto;">
    <h1>Earn Break</h1>

    <div v-if="!state">Connecting…</div>

    <div v-else>
      <!-- ========================= -->
      <!-- Core Focus & Speed -->
      <!-- ========================= -->
      <h2>
        Focus: {{ state.focus_score.toFixed(2) }}
        <span style="opacity: 0.6">·</span>
        Speed: {{ state.time_speed }}x
      </h2>

      <!-- ========================= -->
      <!-- Break Progress -->
      <!-- ========================= -->
      <div style="margin: 16px 0;">
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
          <strong>Break progress</strong>
          <span>{{ progressPct.toFixed(1) }}%</span>
        </div>
        <div style="height: 14px; background:#eee; border-radius: 999px; overflow:hidden;">
          <div
            :style="{
              height: '100%',
              width: progressPct + '%',
              background: state.time_speed >= 1 ? '#16a34a' : '#dc2626',
              transition: 'width 0.4s ease'
            }"
          />
        </div>
      </div>

      <!-- ========================= -->
      <!-- WHY (Explainability) -->
      <!-- ========================= -->
      <div style="margin-top: 16px;">
        <strong>Why this score:</strong>
        <ul>
          <li v-for="r in state.reasons" :key="r">{{ r }}</li>
        </ul>
      </div>

      <hr style="margin: 24px 0;" />

      <!-- ========================= -->
      <!-- ACTIVE WINDOW (SOURCE OF TRUTH) -->
      <!-- ========================= -->
      <h3>Active window</h3>
      <p>
        <strong>App:</strong> {{ state.active_app }}
        <br />
        <strong>Title:</strong> {{ state.active_title || "(no title)" }}
        <br />
        <strong>Is browser:</strong>
        <span :style="{ color: state.active_is_browser ? '#dc2626' : '#16a34a' }">
          {{ state.active_is_browser }}
        </span>
      </p>

      <!-- ========================= -->
      <!-- BROWSER INTENT (SECONDARY) -->
      <!-- ========================= -->
      <div v-if="state.active_is_browser">
        <h3>Browser intent</h3>
        <p>
          <strong>Category:</strong> {{ state.browser_category }}<br />
          <strong>Domain:</strong> {{ state.browser_domain }}<br />
          <strong>Doomscroll:</strong> {{ state.doomscroll_prob }}
        </p>
      </div>
      <div v-else style="opacity: 0.6;">
        Browser intent ignored (browser not active)
      </div>

      <hr style="margin: 24px 0;" />

      <!-- ========================= -->
      <!-- TASK CONTEXT -->
      <!-- ========================= -->
      <h3>Task context</h3>
      <p>
        <strong>Primary:</strong> {{ state.primary_context }}<br />
        <strong>Current:</strong> {{ state.current_context }}<br />
        <strong>Time away:</strong> {{ state.seconds_since_primary.toFixed(1) }}s
      </p>

      <p>
        <strong>Support trips (5m):</strong> {{ state.support_trips_5m }}<br />
        <strong>Successful returns:</strong> {{ state.successful_returns_5m }}<br />
        <strong>Drifts:</strong> {{ state.drift_events_5m }}
      </p>

      <hr style="margin: 24px 0;" />

      <!-- ========================= -->
      <!-- CAMERA -->
      <!-- ========================= -->
      <h3>Camera</h3>
      <p>
        <strong>Face present:</strong> {{ state.face_present }}<br />
        <strong>Gaze on screen:</strong> {{ state.gaze_on_screen }}<br />
        <strong>Head motion:</strong> {{ state.head_motion }}<br />
        <strong>Blinks (60s):</strong> {{ state.blink_rate_60s }}<br />
        <strong>Yawn prob:</strong> {{ state.yawn_prob }}
      </p>

      <small style="opacity:0.6;">
        Last update (UTC): {{ state.ts }}
      </small>
    </div>
  </div>
</template>
