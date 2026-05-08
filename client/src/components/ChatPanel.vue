<template>
  <div class="chat-panel">
    <h3>对话 - {{ currentNPC }}</h3>
    <div class="messages" ref="msgContainer">
      <div v-for="(msg, i) in messages" :key="i" :class="msg.speaker">
        <strong>{{ msg.speaker === 'player' ? '你' : msg.speaker }}:</strong> {{ msg.content }}
      </div>
    </div>
    <div class="options" v-if="lastOptions.length">
      <button v-for="(opt, i) in lastOptions" :key="i" @click="selectOption(opt)">
        {{ opt }}
      </button>
    </div>
    <div class="input-area">
      <input v-model="inputText" @keyup.enter="send" placeholder="输入消息..." />
      <button @click="send">发送</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useGameStore } from '../stores/gameStore'
import { storeToRefs } from 'pinia'

const store = useGameStore()
const { messages, currentNPC } = storeToRefs(store)
const inputText = ref('')
const lastOptions = ref<string[]>([])

async function send() {
  if (!inputText.value.trim()) return
  const data = await store.sendMessage(currentNPC.value, inputText.value)
  lastOptions.value = data.options || []
  inputText.value = ''
}

async function selectOption(opt: string) {
  const data = await store.sendMessage(currentNPC.value, opt)
  lastOptions.value = data.options || []
}
</script>

<style scoped>
.messages { height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 8px; }
.player { color: blue; }
.farmer, .bartender { color: green; }
.options { margin-bottom: 8px; display: flex; gap: 4px; flex-wrap: wrap; }
.options button { padding: 4px 12px; cursor: pointer; }
.input-area { display: flex; gap: 8px; }
.input-area input { flex: 1; padding: 6px; }
</style>
