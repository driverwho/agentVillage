<template>
  <div class="chat-panel">
    <div class="chat-npc-label">{{ npcName }}</div>

    <div class="messages" ref="msgContainer">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="msg-bubble"
        :class="msg.speaker === 'player' ? 'msg-player' : 'msg-npc'"
      >
        <div class="msg-speaker">{{ msg.speaker === 'player' ? '你' : npcName }}</div>
        <div class="msg-content">{{ msg.content }}</div>
      </div>
      <div v-if="messages.length === 0" class="msg-empty">
        选择左侧居民开始对话...
      </div>
    </div>

    <div class="options" v-if="currentOptions.length">
      <button
        v-for="(opt, i) in currentOptions"
        :key="i"
        class="opt-btn"
        @click="selectOption(opt)"
      >
        {{ opt }}
      </button>
    </div>

    <div class="input-area">
      <input
        v-model="inputText"
        @keyup.enter="send"
        placeholder="或自由输入..."
      />
      <button @click="send">发送</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { useGameStore } from '../stores/gameStore'
import { useMockStore } from '../stores/mockStore'
import { storeToRefs } from 'pinia'

const store = useGameStore()
const mock = useMockStore()
const { messages, currentNPC } = storeToRefs(store)
const inputText = ref('')
const msgContainer = ref<HTMLElement>()

const npcName = computed(() => {
  const npc = mock.npcs.find(n => n.id === currentNPC.value)
  return npc?.name || 'NPC'
})

const currentOptions = computed(() => mock.getOptions(currentNPC.value))

watch(messages, async () => {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}, { deep: true })

async function send() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  await store.sendMessage(currentNPC.value, text)
  mock.advanceOptions(currentNPC.value)
}

function selectOption(opt: string) {
  store.sendMessage(currentNPC.value, opt)
  mock.advanceOptions(currentNPC.value)
}
</script>

<style scoped>
.chat-panel {
  padding: var(--gap-md);
  display: flex;
  flex-direction: column;
  flex: 1;
}

.chat-npc-label {
  font-family: var(--font-pixel);
  font-size: 11px;
  color: var(--color-text-dim);
  margin-bottom: var(--gap-sm);
  text-align: center;
}

.messages {
  flex: 1;
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: var(--gap-sm);
  margin-bottom: var(--gap-sm);
}

.msg-empty {
  color: var(--color-text-dim);
  text-align: center;
  padding-top: 80px;
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
}

.msg-bubble {
  margin-bottom: var(--gap-sm);
  padding: var(--gap-xs) var(--gap-sm);
  background: var(--color-panel);
  border: 2px solid var(--color-border);
}

.msg-player {
  margin-left: 20%;
  border-left: 3px solid var(--color-accent);
}

.msg-npc {
  margin-right: 20%;
  border-left: 3px solid var(--color-info);
}

.msg-speaker {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
  margin-bottom: 2px;
}

.msg-content {
  font-size: var(--font-size-base);
  line-height: 1.6;
}

.options {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: var(--gap-sm);
}

.opt-btn {
  font-size: 11px;
  padding: 6px 12px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  color: var(--color-text);
  font-family: var(--font-pixel);
}

.opt-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent-light);
}

.input-area {
  display: flex;
  gap: var(--gap-sm);
}

.input-area input { flex: 1; }
</style>
