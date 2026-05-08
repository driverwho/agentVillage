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
