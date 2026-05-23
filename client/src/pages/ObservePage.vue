<template>
  <div class="observe-page">
    <header class="observe-header">
      <h1 class="observe-title">Agent Village — NPC 观察面板</h1>
      <div class="observe-header-right">
        <div class="time-controls">
          <button class="time-btn" @click="togglePause">
            {{ gameStore.world?.is_paused ? '▶ 启动' : '⏸ 暂停' }}
          </button>
          <button class="time-btn" @click="advanceTime(60)">+1h</button>
          <button class="time-btn" @click="advanceTime(360)">+6h</button>
          <button class="time-btn" @click="advanceTime(1440)">+1天</button>
        </div>
        <span class="ws-status" :class="wsConnected ? 'ws-on' : 'ws-off'">
          {{ wsConnected ? '● 已连接' : '○ 断开' }}
        </span>
        <span class="game-time-display">
          Day {{ gameTime.day }} {{ gameTime.hour }}:00
        </span>
        <router-link to="/" class="back-btn">返回游戏</router-link>
      </div>
    </header>

    <div class="event-banner">
      <span class="event-banner-title">当前事件</span>
      <div class="event-tags">
        <span v-if="worldEvents.length === 0" class="event-tag event-tag--empty">今日无事</span>
        <span v-for="evt in worldEvents" :key="evt.id" class="event-tag">
          {{ evt.name }}（{{ evt.started_hour }}:00 起）
        </span>
      </div>
    </div>

    <div class="observe-grid">
      <NPCObserveCard
        v-for="npc in npcList"
        :key="npc.id"
        :npc="npc"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useObserveStore } from '../stores/observeStore'
import { useGameStore } from '../stores/gameStore'
import NPCObserveCard from '../components/NPCObserveCard.vue'

const store = useObserveStore()
const gameStore = useGameStore()
const { npcs, gameTime, wsConnected, worldEvents } = storeToRefs(store)

const npcList = computed(() => Object.values(npcs.value))

async function advanceTime(minutes: number) {
  await gameStore.advanceTime(minutes)
  await store.fetchInitialStatus()
}

async function togglePause() {
  await gameStore.togglePause()
}

onMounted(async () => {
  await gameStore.fetchWorld()
  await store.fetchInitialStatus()
  store.connectWebSocket()
})

onUnmounted(() => {
  store.disconnect()
})
</script>

<style scoped>
.observe-page {
  min-height: 100vh;
  padding: var(--gap-md);
  max-width: 1400px;
  margin: 0 auto;
}

.observe-header {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--gap-md);
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.observe-title {
  font-size: var(--font-size-lg);
  margin: 0;
}

.observe-header-right {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.ws-status {
  font-family: var(--font-pixel);
  font-size: 10px;
}

.ws-on { color: var(--color-health); }
.ws-off { color: var(--color-fatigue); }

.game-time-display {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
}

.back-btn {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
  text-decoration: none;
  border: 2px solid var(--color-border);
  padding: 6px 12px;
}

.back-btn:hover {
  border-color: var(--color-accent);
}

.time-controls {
  display: flex;
  gap: 4px;
}

.time-btn {
  font-family: var(--font-pixel);
  font-size: 10px;
  padding: 4px 8px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  color: var(--color-text);
  cursor: pointer;
}

.time-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.observe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--gap-md);
}

.event-banner {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-sm) var(--gap-md);
  margin-bottom: var(--gap-md);
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.event-banner-title {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-text);
  white-space: nowrap;
}

.event-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.event-tag {
  font-family: var(--font-pixel);
  font-size: 10px;
  padding: 2px 8px;
  border: 1px solid var(--color-accent);
  color: var(--color-accent);
}

.event-tag--empty {
  border-color: var(--color-border);
  color: var(--color-border);
}
</style>
