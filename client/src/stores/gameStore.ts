import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { WorldState, PlayerState, ChatResponse } from '../types'
import api from '../services/api'

export const useGameStore = defineStore('game', () => {
  const world = ref<WorldState | null>(null)
  const player = ref<PlayerState | null>(null)
  const currentNPC = ref<string>('farmer')
  const messages = ref<Array<{ speaker: string; content: string }>>([])

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

  function selectNPC(npcId: string) {
    currentNPC.value = npcId
    messages.value = []
  }

  async function useFarmingTool() {
    const { data } = await api.post('/api/tools/farming')
    return data
  }

  return { world, player, currentNPC, messages, fetchWorld, fetchPlayer, advanceTime, togglePause, sendMessage, selectNPC, useFarmingTool }
})
