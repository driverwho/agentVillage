<template>
  <div class="tavern-panel">
    <div class="tavern-stream" ref="streamRef">
      <div
        v-for="(msg, i) in mock.tavernConversations"
        :key="i"
        class="tavern-msg"
      >
        <div class="msg-avatar">
          <img :src="msg.avatar" :alt="msg.name" />
        </div>
        <div class="msg-body">
          <div class="msg-header">
            <span class="msg-name">{{ msg.name }}</span>
            <span class="msg-time">{{ msg.time }}</span>
          </div>
          <div class="msg-text">{{ msg.text }}</div>
        </div>
      </div>
    </div>

    <div class="tavern-status">
      <span class="live-dot"></span> 实时收听中
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useMockStore } from '../stores/mockStore'

const mock = useMockStore()
const streamRef = ref<HTMLElement | null>(null)

onMounted(async () => {
  await nextTick()
  if (streamRef.value) {
    streamRef.value.scrollTop = streamRef.value.scrollHeight
  }
})
</script>

<style scoped>
.tavern-panel {
  padding: var(--gap-md);
  display: flex;
  flex-direction: column;
  flex: 1;
}

.tavern-stream {
  flex: 1;
  overflow-y: auto;
  max-height: 300px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tavern-msg {
  display: flex;
  gap: 10px;
  padding: 8px;
  background: var(--color-bg);
  border-left: 3px solid var(--color-border);
  transition: border-color 0.2s;
}

.tavern-msg:hover {
  border-left-color: var(--color-accent);
}

.msg-avatar {
  width: 36px;
  height: 36px;
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  flex-shrink: 0;
  overflow: hidden;
}

.msg-avatar img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
}

.msg-body {
  flex: 1;
  min-width: 0;
}

.msg-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 3px;
}

.msg-name {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-accent);
}

.msg-time {
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-text-dim);
}

.msg-text {
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--color-text);
  line-height: 1.5;
}

.tavern-status {
  margin-top: var(--gap-sm);
  padding-top: var(--gap-xs);
  border-top: 1px solid var(--color-border);
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-text-dim);
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.live-dot {
  width: 6px;
  height: 6px;
  background: var(--color-fatigue);
  display: inline-block;
  animation: blink 1.5s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0.3; }
}
</style>
