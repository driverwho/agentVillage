<template>
  <div class="village-news-panel">
    <div class="news-stream" ref="streamRef">
      <template v-if="conversations.length === 0">
        <div class="news-empty">暂无 NPC 对话，等待村民们开始交流...</div>
      </template>
      <template v-for="conv in conversations" :key="conv.id">
        <div class="conv-separator">
          <span class="conv-separator-line"></span>
          <span class="conv-separator-text">
            Day {{ conv.day }} {{ conv.hour }}:00 · {{ getLocationName(conv.location) }}
          </span>
          <span v-if="!conv.finished" class="conv-live-dot"></span>
          <span class="conv-separator-line"></span>
        </div>
        <div
          v-for="(msg, i) in conv.messages"
          :key="`${conv.id}-${i}`"
          class="conv-msg"
        >
          <div class="msg-avatar">
            <img :src="getAvatar(msg.speakerId)" :alt="msg.speakerName" />
          </div>
          <div class="msg-body">
            <span class="msg-name">{{ msg.speakerName }}</span>
            <span class="msg-text">"{{ msg.content }}"</span>
          </div>
        </div>
        <div v-if="conv.finished && conv.summary" class="conv-summary">
          {{ conv.summary }}
        </div>
      </template>
    </div>
    <div class="news-status">
      <span class="live-dot"></span> 实时收听中
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useConversationStore, getLocationName, getAvatar } from '../stores/conversationStore'

const store = useConversationStore()
const { conversations } = storeToRefs(store)
const streamRef = ref<HTMLElement | null>(null)

watch(conversations, async () => {
  await nextTick()
  if (streamRef.value) {
    streamRef.value.scrollTop = 0
  }
}, { deep: true })
</script>

<style scoped>
.village-news-panel {
  padding: var(--gap-md);
  display: flex;
  flex-direction: column;
  flex: 1;
}

.news-stream {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.news-empty {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-text-dim);
  text-align: center;
  padding: var(--gap-lg) var(--gap-md);
}

.conv-separator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0 6px;
}

.conv-separator-line {
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.conv-separator-text {
  font-family: var(--font-pixel);
  font-size: 9px;
  color: var(--color-text-dim);
  white-space: nowrap;
}

.conv-live-dot {
  width: 6px;
  height: 6px;
  background: var(--color-health);
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

.conv-msg {
  display: flex;
  gap: 10px;
  padding: 6px 8px;
  background: var(--color-bg);
  border-left: 3px solid var(--color-border);
}

.conv-msg:hover {
  border-left-color: var(--color-accent);
}

.msg-avatar {
  width: 32px;
  height: 32px;
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
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.msg-name {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-accent);
}

.msg-text {
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--color-text);
  line-height: 1.5;
}

.conv-summary {
  font-family: var(--font-pixel);
  font-size: 9px;
  color: var(--color-text-dim);
  padding: 4px 8px;
  font-style: italic;
}

.news-status {
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
  background: var(--color-health);
  display: inline-block;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
