import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { WorldState, PlayerState, ChatResponse } from '../types'
import api from '../services/api'
import { streamChat } from '../services/api'

export const useGameStore = defineStore('game', () => {
  const world = ref<WorldState | null>(null)
  const player = ref<PlayerState | null>(null)
  const currentNPC = ref<string>('farmer')
  const messages = ref<Array<{ speaker: string; content: string }>>([])
  const streaming = ref(false)
  let _streamCtrl: AbortController | null = null

  async function fetchWorld() {
    const { data } = await api.get('/world')
    world.value = data
  }

  async function fetchPlayer() {
    const { data } = await api.get('/api/player')
    player.value = data
  }

  async function advanceTime(minutes: number = 60) {
    await api.post('/time/advance', null, { params: { minutes } })
    await fetchWorld()
    await fetchPlayer()
  }

  async function togglePause() {
    await api.post('/time/toggle')
    await fetchWorld()
  }

  async function sendMessage(npcId: string, text: string): Promise<ChatResponse> {
    messages.value.push({ speaker: 'player', content: text })
    const { data } = await api.post(`/api/chat/${npcId}`, null, {
      params: { message: text },
    })
    messages.value.push({ speaker: npcId, content: data.reply })
    await fetchPlayer()
    return data
  }

  async function sendMessageStream(npcId: string, text: string): Promise<void> {
    messages.value.push({ speaker: 'player', content: text })
    streaming.value = true

    // 创建占位消息，流式填充
    const msgIndex = messages.value.length
    messages.value.push({ speaker: npcId, content: '' })

    _streamCtrl = await streamChat(
      npcId,
      text,
      // onDelta
      (delta: string) => {
        messages.value[msgIndex].content += delta
      },
      // onDone
      (options: string[]) => {
        const finalContent = messages.value[msgIndex].content
        // 移除 [OPTIONS] 标记
        if (finalContent.includes('[OPTIONS]')) {
          messages.value[msgIndex].content = finalContent.split('[OPTIONS]')[0].trim()
        }
        streaming.value = false
        // 如果需要，可以将 options 传递给 mock store
        fetchPlayer()
      },
      // onError
      (err: string) => {
        messages.value[msgIndex].content = `（出错了: ${err}）`
        streaming.value = false
      },
    )
  }

  function cancelStream() {
    if (_streamCtrl) {
      _streamCtrl.abort()
      _streamCtrl = null
      streaming.value = false
    }
  }

  function selectNPC(npcId: string) {
    currentNPC.value = npcId
    messages.value = []
    cancelStream()
  }

  async function useFarmingTool() {
    const { data } = await api.post('/api/tools/farming')
    return data
  }

  return { world, player, currentNPC, messages, streaming, fetchWorld, fetchPlayer, advanceTime, togglePause, sendMessage, sendMessageStream, cancelStream, selectNPC, useFarmingTool }
})
