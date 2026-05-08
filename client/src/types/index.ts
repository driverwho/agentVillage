export interface GameTime {
  day: number
  hour: number
  minute: number
}

export interface NPCState {
  health: number
  hunger: number
  fatigue: number
  mood: number
}

export type NPCStatusType = 'working' | 'resting' | 'socializing' | 'sleeping' | 'abnormal' | 'away'

export interface NPCInfo {
  id: string
  name: string
  role: string
  avatar: string
  unlocked: boolean
  state: NPCState
  status: NPCStatusType
  statusLabel: string
  relationship: number
}

export interface WorldState {
  game_time: GameTime
  is_paused: boolean
  npcs: Record<string, { state: NPCState }>
}

export interface PlayerState {
  name: string
  health: number
  hunger: number
  fatigue: number
  location: string
  gold: number
  relationships: Record<string, number>
  reputation: number
  farm_count: number
}

export interface ChatResponse {
  reply: string
  options: string[]
}

export interface ToolDef {
  id: string
  name: string
  icon: string
  unlocked: boolean
  trustRequired: number
  npcId: string
}

export interface TimelineEntry {
  day: number
  text: string
  source: 'witnessed' | 'heard' | 'inferred'
}

export interface NPCObservation {
  npcId: string
  entries: { day: number; text: string }[]
}

export interface PlayerAction {
  day: number
  text: string
}

export interface RandomEvent {
  id: string
  name: string
  description: string
  icon: string
}
