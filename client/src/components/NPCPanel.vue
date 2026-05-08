<template>
  <div class="npc-panel">
    <h3>村庄居民</h3>

    <!-- 已解锁 NPC -->
    <div
      v-for="npc in mock.unlockedNPCs"
      :key="npc.id"
      class="npc-card"
      :class="{ 'npc-card--active': npc.id === currentNPC }"
      @click="$emit('select', npc.id)"
    >
      <div class="npc-avatar">{{ npc.avatar }}</div>
      <div class="npc-body">
        <div class="npc-header">
          <span class="npc-name">{{ npc.name }}</span>
          <span class="npc-status" :style="{ color: statusColor(npc.status) }">
            {{ npc.statusLabel }}
          </span>
        </div>
        <div class="npc-stats">
          <span class="npc-stat">♥{{ npc.state.health }}</span>
          <span class="npc-stat">🍖{{ npc.state.hunger }}</span>
          <span class="npc-stat">💤{{ npc.state.fatigue }}</span>
          <span class="npc-stat">☻{{ npc.state.mood }}</span>
        </div>
        <div class="npc-rel" v-if="npc.relationship > 0">
          <span class="rel-label">好感</span>
          <div class="rel-bar">
            <div class="rel-fill" :style="{ width: npc.relationship + '%' }"></div>
          </div>
          <span class="rel-val">{{ npc.relationship }}</span>
        </div>
      </div>
    </div>

    <!-- 分隔线 -->
    <div class="locked-divider">🔒 待解锁</div>

    <!-- 待解锁 NPC -->
    <div
      v-for="npc in mock.lockedNPCs"
      :key="npc.id"
      class="npc-card npc-card--locked"
    >
      <div class="npc-avatar npc-avatar--locked">{{ npc.avatar }}</div>
      <div class="npc-body">
        <div class="npc-header">
          <span class="npc-name locked-name">{{ npc.name }}</span>
        </div>
        <div class="npc-status locked-status">🔒 解锁条件未知</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { useMockStore } from '../stores/mockStore'
import { storeToRefs } from 'pinia'
import type { NPCStatusType } from '../types'

const store = useGameStore()
const mock = useMockStore()
const { currentNPC } = storeToRefs(store)

defineEmits<{ select: [npcId: string] }>()

function statusColor(status: NPCStatusType): string {
  const map: Record<NPCStatusType, string> = {
    working: 'var(--color-health)',
    resting: 'var(--color-hunger)',
    socializing: 'var(--color-info)',
    sleeping: 'var(--color-text-dim)',
    abnormal: 'var(--color-fatigue)',
    away: 'var(--color-info)',
  }
  return map[status]
}
</script>

<style scoped>
.npc-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}

.npc-panel h3 {
  margin-bottom: var(--gap-sm);
  font-size: var(--font-size-sm);
}

.npc-card {
  display: flex;
  gap: 10px;
  padding: var(--gap-sm) var(--gap-md);
  margin-bottom: var(--gap-sm);
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.15s;
  align-items: center;
}

.npc-card:hover {
  border-color: var(--color-border-light);
}

.npc-card--active {
  border-color: var(--color-accent);
}

.npc-card--locked {
  opacity: 0.55;
  border-style: dashed;
  cursor: default;
}

.npc-card--locked:hover {
  border-color: var(--color-border);
}

.npc-avatar {
  width: 40px;
  height: 40px;
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  image-rendering: pixelated;
}

.npc-avatar--locked {
  filter: grayscale(70%);
}

.npc-body {
  flex: 1;
  min-width: 0;
}

.npc-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.npc-name {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
  white-space: nowrap;
}

.locked-name {
  color: var(--color-text-dim);
}

.npc-status {
  font-family: var(--font-pixel);
  font-size: 7px;
  white-space: nowrap;
}

.locked-status {
  font-size: 7px;
  color: var(--color-text-dim);
}

.npc-stats {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  margin-top: 2px;
}

.npc-stat {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-text-dim);
}

.npc-rel {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

.rel-label {
  font-family: var(--font-pixel);
  font-size: 7px;
  color: var(--color-text-dim);
  flex-shrink: 0;
}

.rel-bar {
  flex: 1;
  max-width: 80px;
  height: 6px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}

.rel-fill {
  height: 100%;
  background: var(--color-health);
  transition: width 0.3s step-end;
}

.rel-val {
  font-family: var(--font-pixel);
  font-size: 7px;
  color: var(--color-text-dim);
  width: 20px;
  text-align: right;
}

.locked-divider {
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-text-dim);
  margin: var(--gap-sm) 0;
  padding-bottom: 2px;
  border-bottom: 1px solid var(--color-border);
}
</style>
