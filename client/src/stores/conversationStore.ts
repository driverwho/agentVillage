import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ConversationMessage {
  speakerId: string
  speakerName: string
  content: string
}

export interface ConversationBlock {
  id: string
  day: number
  hour: number
  location: string
  participants: string[]
  messages: ConversationMessage[]
  finished: boolean
  summary?: string
}

const MAX_CONVERSATIONS = 20

const LOCATION_NAMES: Record<string, string> = {
  home: '家',
  field: '田地',
  tavern: '酒馆',
  market: '市场',
  church: '教堂',
  forest: '森林',
}

export function getLocationName(loc: string): string {
  return LOCATION_NAMES[loc] || loc
}

const AVATAR_MAP: Record<string, string> = {
  farmer: '/img/48/farmer.png',
  bartender: '/img/48/bartender.png',
  sheriff: '/img/48/sheriff.png',
  beggar: '/img/48/beggar.png',
  painter: '/img/48/shopkeeper.png',
  fortune_teller: '/img/48/witch.png',
}

export function getAvatar(npcId: string): string {
  return AVATAR_MAP[npcId] || '/img/48/farmer.png'
}

export const useConversationStore = defineStore('conversation', () => {
  const conversations = ref<ConversationBlock[]>([])

  function handleMessage(msg: any): boolean {
    switch (msg.type) {
      case 'npc_conversation_start':
        _onStart(msg)
        return true
      case 'npc_conversation_message':
        _onMessage(msg)
        return true
      case 'npc_conversation_end':
        _onEnd(msg)
        return true
      default:
        return false
    }
  }

  function _onStart(msg: any) {
    const block: ConversationBlock = {
      id: msg.conversation_id,
      day: msg.day,
      hour: msg.hour,
      location: msg.location,
      participants: msg.participants,
      messages: [],
      finished: false,
    }
    conversations.value.unshift(block)
    if (conversations.value.length > MAX_CONVERSATIONS) {
      conversations.value.pop()
    }
  }

  function _onMessage(msg: any) {
    const block = conversations.value.find(c => c.id === msg.conversation_id)
    if (!block) return
    block.messages.push({
      speakerId: msg.speaker_id,
      speakerName: msg.speaker_name,
      content: msg.content,
    })
  }

  function _onEnd(msg: any) {
    const block = conversations.value.find(c => c.id === msg.conversation_id)
    if (!block) return
    block.finished = true
    block.summary = msg.summary
  }

  return { conversations, handleMessage }
})
