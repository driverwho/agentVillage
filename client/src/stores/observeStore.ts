import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import api from '../services/api'

export interface NPCHistoryEntry {
  timestamp: string
  tool: string
  message: string
  tokens: number
}

export interface NPCObserveData {
  id: string
  name: string
  avatar: string
  location: string
  activity: {
    status: 'idle' | 'active'
    currentTool: string | null
    endDay: number | null
    endHour: number | null
    idleReason: string | null
  }
  state: { health: number; hunger: number; fatigue: number; mood: number }
  llmStatus: 'idle' | 'requesting' | 'done'
  history: NPCHistoryEntry[]
}

export interface GameTimeData {
  day: number
  hour: number
  minute: number
}

const AVATAR_MAP: Record<string, string> = {
  farmer: '/img/128/farmer.png',
  bartender: '/img/128/bartender.png',
  sheriff: '/img/128/sheriff.png',
  beggar: '/img/128/beggar.png',
  painter: '/img/128/shopkeeper.png',
  fortune_teller: '/img/128/witch.png',
}

export const useObserveStore = defineStore('observe', () => {
  const npcs = reactive<Record<string, NPCObserveData>>({})
  const gameTime = ref<GameTimeData>({ day: 1, hour: 6, minute: 0 })
  const wsConnected = ref(false)
  let ws: WebSocket | null = null

  async function fetchInitialStatus() {
    const { data } = await api.get('/api/npcs/status')
    gameTime.value = data.game_time
    for (const [npcId, npcData] of Object.entries(data.npcs as Record<string, any>)) {
      npcs[npcId] = {
        id: npcId,
        name: npcData.name,
        avatar: AVATAR_MAP[npcId] || '/img/128/farmer.png',
        location: npcData.location,
        activity: {
          status: npcData.activity.status,
          currentTool: npcData.activity.current_tool,
          endDay: npcData.activity.end_day,
          endHour: npcData.activity.end_hour,
          idleReason: npcData.activity.idle_reason,
        },
        state: npcData.state,
        llmStatus: 'idle',
        history: [],
      }
    }
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws/observe`
    ws = new WebSocket(wsUrl)

    ws.onopen = () => { wsConnected.value = true }
    ws.onclose = () => {
      wsConnected.value = false
      setTimeout(connectWebSocket, 3000)
    }
    ws.onerror = () => { wsConnected.value = false }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      handleMessage(msg)
    }
  }

  function handleMessage(msg: any) {
    if (msg.type === 'game_time_update') {
      if (msg.day !== undefined) {
        gameTime.value = { day: msg.day, hour: msg.hour, minute: msg.minute || 0 }
      }
      return
    }

    const npcId = msg.npc_id
    if (!npcId || !npcs[npcId]) return

    switch (msg.type) {
      case 'npc_state_update':
        npcs[npcId].state = {
          health: msg.health,
          hunger: msg.hunger,
          fatigue: msg.fatigue,
          mood: msg.mood,
        }
        break

      case 'npc_activity_change':
        npcs[npcId].activity = {
          status: msg.status,
          currentTool: msg.current_tool,
          endDay: msg.end_day,
          endHour: msg.end_hour,
          idleReason: msg.idle_reason,
        }
        npcs[npcId].location = msg.location || npcs[npcId].location
        if (msg.status === 'idle') {
          npcs[npcId].llmStatus = 'idle'
        }
        break

      case 'npc_llm_start':
        npcs[npcId].llmStatus = 'requesting'
        break

      case 'npc_llm_done':
        npcs[npcId].llmStatus = 'done'
        npcs[npcId].history.unshift({
          timestamp: msg.timestamp,
          tool: msg.tool_used || '(无工具)',
          message: msg.message || '',
          tokens: msg.tokens || 0,
        })
        if (npcs[npcId].history.length > 5) {
          npcs[npcId].history.pop()
        }
        break
    }
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  return { npcs, gameTime, wsConnected, fetchInitialStatus, connectWebSocket, disconnect }
})
