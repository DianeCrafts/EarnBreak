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

      <small style="opacity:0.7;">Last update (UTC): {{ state.ts }}</small>
    </div>
  </div>
</template>
