<template>
  <div class="observe-page">
    <header class="observe-header">
      <h1 class="observe-title">Agent Village — NPC 观察面板</h1>
      <div class="observe-header-right">
        <span class="ws-status" :class="wsConnected ? 'ws-on' : 'ws-off'">
          {{ wsConnected ? '● 已连接' : '○ 断开' }}
        </span>
        <span class="game-time-display">
          Day {{ gameTime.day }} {{ gameTime.hour }}:00
        </span>
        <router-link to="/" class="back-btn">返回游戏</router-link>
      </div>
    </header>

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
import NPCObserveCard from '../components/NPCObserveCard.vue'

const store = useObserveStore()
const { npcs, gameTime, wsConnected } = storeToRefs(store)

const npcList = computed(() => Object.values(npcs.value))

onMounted(async () => {
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

.observe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--gap-md);
}
</style>
