<script lang="ts">
import { ref, onMounted } from "vue";

export type LiveState = {
  ts: string;

  active_app: string;
  active_title: string;
  active_is_browser: boolean;

  browser_domain: string;
  browser_category: string;
  doomscroll_prob: number;

  face_present: number;
  gaze_on_screen: number;
  head_motion: number;
};

type LabelRequestMsg = {
  type: "label_request";
  features: Record<string, number>;
};

type LiveStateMsg = {
  type: "live_state";
  data: LiveState;
};

export default {
  setup() {
    const liveState = ref<LiveState | null>(null);
    const pendingLabel = ref<LabelRequestMsg | null>(null);
    const ws = ref<WebSocket | null>(null);

    const timeWindowSec = 30; // keep in sync with backend

    function submitLabel(label: string) {
      if (!ws.value) return;

      ws.value.send(
        JSON.stringify({
          label,
        })
      );

      pendingLabel.value = null;
    }

    onMounted(() => {
      ws.value = new WebSocket("ws://localhost:8000/ws");

      ws.value.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);

          if (msg.type === "live_state") {
            liveState.value = msg.data;
          }

          if (msg.type === "label_request") {
            pendingLabel.value = msg;
          }
        } catch (e) {
          console.error("Bad WS message", e);
        }
      };

      ws.value.onopen = () => console.log("WS connected");
      ws.value.onclose = () => console.log("WS disconnected");
    });

    return {
      liveState,
      pendingLabel,
      submitLabel,
      timeWindowSec,
    };
  },
};
</script>
