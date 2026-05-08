import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { NPCInfo, ToolDef, RandomEvent, TimelineEntry, NPCObservation, PlayerAction, NPCStatusType } from '../types'
import { showToast } from '../services/toast'

function deriveStatus(npcId: string, hour: number): { status: NPCStatusType; label: string } {
  if (hour >= 22 || hour < 6) return { status: 'sleeping', label: '😴 睡眠中' }
  if (hour >= 18 && hour < 22) return { status: 'socializing', label: '🍺 酒馆社交' }
  if (hour >= 12 && hour < 13) return { status: 'resting', label: '☕ 休息中' }
  const labels: Record<string, string> = {
    farmer: '🌾 耕作中',
    bartender: '🧹 整理中',
    sheriff: '🛡 巡逻中',
    fortune_teller: '🔮 占卜中',
    beggar: '🚶 流浪中',
    shopkeeper: '📦 看店中',
  }
  return { status: 'working', label: labels[npcId] || '工作中' }
}

export const useMockStore = defineStore('mock', () => {
  const currentHour = ref(14)

  // ── NPC 列表 ──
  const npcs = ref<NPCInfo[]>([
    {
      id: 'farmer', name: '农夫·托德', role: '村庄农夫', avatar: '🧑‍🌾',
      unlocked: true, state: { health: 80, hunger: 60, fatigue: 30, mood: 70 },
      status: 'working', statusLabel: '🌾 耕作中', relationship: 35,
    },
    {
      id: 'bartender', name: '酒保·盖斯', role: '酒馆老板', avatar: '🍺',
      unlocked: true, state: { health: 90, hunger: 50, fatigue: 20, mood: 60 },
      status: 'working', statusLabel: '🧹 整理中', relationship: 20,
    },
    {
      id: 'sheriff', name: '警长·巴顿', role: '治安官', avatar: '⭐',
      unlocked: false, state: { health: 100, hunger: 70, fatigue: 10, mood: 80 },
      status: 'working', statusLabel: '🔒 解锁条件未知', relationship: 0,
    },
    {
      id: 'fortune_teller', name: '占卜师·丽娜', role: '神秘占卜师', avatar: '🔮',
      unlocked: false, state: { health: 70, hunger: 40, fatigue: 50, mood: 90 },
      status: 'working', statusLabel: '🔒 解锁条件未知', relationship: 0,
    },
    {
      id: 'beggar', name: '流浪者·威利', role: '流浪乞丐', avatar: '🪙',
      unlocked: false, state: { health: 40, hunger: 10, fatigue: 60, mood: 30 },
      status: 'away', statusLabel: '🔒 解锁条件未知', relationship: 0,
    },
    {
      id: 'shopkeeper', name: '杂货商·洛克', role: '杂货店老板', avatar: '📦',
      unlocked: false, state: { health: 85, hunger: 60, fatigue: 15, mood: 75 },
      status: 'working', statusLabel: '🔒 解锁条件未知', relationship: 0,
    },
  ])

  const unlockedNPCs = computed(() => npcs.value.filter(n => n.unlocked))
  const lockedNPCs = computed(() => npcs.value.filter(n => !n.unlocked))

  function updateNPCStatus(hour: number) {
    currentHour.value = hour
    npcs.value.forEach(npc => {
      if (!npc.unlocked) return
      const s = deriveStatus(npc.id, hour)
      npc.status = s.status
      npc.statusLabel = s.label
    })
  }

  // ── 工具列表 ──
  const tools = ref<ToolDef[]>([
    { id: 'farming', name: '耕作', icon: '🌾', unlocked: true, trustRequired: 0, npcId: 'farmer' },
    { id: 'trading', name: '交易', icon: '🗡', unlocked: false, trustRequired: 30, npcId: 'bartender' },
    { id: 'patrol', name: '巡逻', icon: '🛡', unlocked: false, trustRequired: 60, npcId: 'sheriff' },
    { id: 'divination', name: '占卜', icon: '🔮', unlocked: false, trustRequired: 90, npcId: 'fortune_teller' },
    { id: 'brewing', name: '酿酒', icon: '🍺', unlocked: false, trustRequired: 40, npcId: 'bartender' },
    { id: 'painting', name: '作画', icon: '🎨', unlocked: false, trustRequired: 50, npcId: 'shopkeeper' },
  ])

  // ── 事件系统 ──
  const dailyEventQuota = ref(1)
  const randomEvents: RandomEvent[] = [
    { id: 'hail', name: '冰雹', description: '突降冰雹，作物受损', icon: '🌨️' },
    { id: 'theft_tavern', name: '盗窃案（酒馆）', description: '酒馆昨夜遭窃', icon: '🦹' },
    { id: 'harvest', name: '丰收日', description: '今日耕作产出翻倍', icon: '🌾' },
    { id: 'merchant', name: '流浪商人', description: '一位神秘商人路过村庄', icon: '🧳' },
    { id: 'eclipse', name: '月食', description: '占卜之力增强', icon: '🌑' },
    { id: 'brawl', name: '酒馆斗殴', description: '酒馆爆发冲突', icon: '👊' },
  ]
  const currentEvent = ref<RandomEvent | null>(null)

  // ── 笔记簿 ──
  const timeline = ref<TimelineEntry[]>([
    { day: 1, text: '你来到了这个村庄。酒馆里，酒保·盖斯和一个陌生人做了交易。', source: 'witnessed' },
    { day: 2, text: '农夫·托德在酒馆和酒保·盖斯吵架，摔了一个杯子。（原因不明）', source: 'witnessed' },
    { day: 2, text: '听说流浪者·威利在村口捡到了一枚金币。', source: 'heard' },
  ])

  const npcObservations = ref<NPCObservation[]>([
    { npcId: 'bartender', entries: [{ day: 1, text: '和流浪商人交易了东西，神神秘秘的。' }, { day: 2, text: '和农夫吵架，心情不太好。' }] },
    { npcId: 'farmer', entries: [{ day: 2, text: '在酒馆发火，似乎对酒保涨价很不满。' }] },
  ])

  const playerActions = ref<PlayerAction[]>([
    { day: 1, text: '和酒保·盖斯闲聊，问起了村里的情况。' },
    { day: 2, text: '帮农夫·托德耕了一上午的地。' },
  ])

  const notebookTab = ref<'timeline' | 'npc' | 'actions'>('timeline')

  // ── 偷听 ──
  const eavesdropQuota = ref(1)

  // ── 对话选项 ──
  const dialogueOptionSets: Record<string, string[][]> = {
    farmer: [
      ['最近村里有什么事吗？', '庄稼长得怎么样了？', '听说你和酒保闹矛盾了？'],
      ['需要我帮忙耕作吗？', '你为什么讨厌酒保？', '聊聊天气吧。'],
      ['关于警长，你知道些什么？', '我先走了。', '下次再来帮你。'],
    ],
    bartender: [
      ['来一杯你的招牌酒。', '最近生意怎么样？', '那天和你交易的是谁？'],
      ['听说你和农夫吵架了？', '有什么特别的情报吗？', '我随便看看。'],
      ['酒馆来过什么有趣的客人吗？', '给我讲讲这个村子。', '再见。'],
    ],
  }
  const optionIndex = ref<Record<string, number>>({ farmer: 0, bartender: 0 })

  function getOptions(npcId: string): string[] {
    const sets = dialogueOptionSets[npcId]
    if (!sets) return ['聊聊吧。', '我先走了。']
    const idx = optionIndex.value[npcId] || 0
    return sets[idx] || sets[0]
  }

  function advanceOptions(npcId: string) {
    const sets = dialogueOptionSets[npcId]
    if (!sets) return
    const idx = (optionIndex.value[npcId] || 0) + 1
    optionIndex.value[npcId] = idx % sets.length
  }

  // ── Mock 方法 ──
  function drawRandomEvent(): RandomEvent {
    if (dailyEventQuota.value <= 0) {
      showToast('今日事件次数已用完')
      return null!
    }
    dailyEventQuota.value--
    const event = randomEvents[Math.floor(Math.random() * randomEvents.length)]
    currentEvent.value = event
    showToast(`🎴 抽到了「${event.name}」！${event.description}（功能开发中，敬请期待）`)
    return event
  }

  function submitCustomEvent(text: string) {
    if (dailyEventQuota.value <= 0) {
      showToast('今日事件次数已用完')
      return
    }
    if (!text.trim()) {
      showToast('请输入事件描述')
      return
    }
    dailyEventQuota.value--
    showToast(`📝 自定义事件「${text}」已提交！（功能开发中，敬请期待）`)
  }

  function rollDice(): { result: number; success: boolean } {
    const result = Math.floor(Math.random() * 20) + 1
    const success = result >= 12
    showToast(`🎲 掷出了 ${result} 点！${success ? '成功！' : '失败...'}（功能开发中，敬请期待）`)
    return { result, success }
  }

  function doEavesdrop(targetIds: string[]) {
    if (eavesdropQuota.value <= 0) {
      showToast('今日偷听次数已用完')
      return
    }
    eavesdropQuota.value--
    const names = targetIds.map(id => npcs.value.find(n => n.id === id)?.name || id).join(' 和 ')
    showToast(`👂 正在偷听 ${names} 的对话...（功能开发中，敬请期待）`)
  }

  function useLockedTool(tool: ToolDef) {
    showToast(`🛠 「${tool.name}」需要信任等级 ${tool.trustRequired}（功能开发中，敬请期待）`)
  }

  function resetDailyQuotas() {
    dailyEventQuota.value = 1
    eavesdropQuota.value = 1
  }

  return {
    npcs, unlockedNPCs, lockedNPCs,
    tools,
    dailyEventQuota, randomEvents, currentEvent,
    timeline, npcObservations, playerActions, notebookTab,
    eavesdropQuota,
    dialogueOptionSets, optionIndex,
    updateNPCStatus,
    getOptions, advanceOptions,
    drawRandomEvent, submitCustomEvent, rollDice,
    doEavesdrop, useLockedTool,
    resetDailyQuotas,
  }
})
