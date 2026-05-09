<template>
  <div class="npc-panel" v-show="!collapsed">
    <h3>村庄居民</h3>

    <div
      v-for="npc in mock.unlockedNPCs"
      :key="npc.id"
      class="npc-card"
      :class="{ 'npc-card--active': npc.id === currentNPC }"
      @click="$emit('select', npc.id)"
    >
      <div class="npc-avatar">
        <img :src="npc.avatar" :alt="npc.name" />
      </div>
      <div class="npc-body">
        <span class="npc-name">{{ npc.name }}</span>
        <div class="npc-rel" v-if="npc.relationship > 0">
          <div class="rel-bar">
            <div class="rel-fill" :style="{ width: npc.relationship + '%' }"></div>
          </div>
          <span class="rel-val">{{ npc.relationship }}</span>
        </div>
      </div>
    </div>

    <div class="locked-divider">🔒 待解锁</div>

    <div
      v-for="npc in mock.lockedNPCs"
      :key="npc.id"
      class="npc-card npc-card--locked"
    >
      <div class="npc-avatar npc-avatar--locked">
        <img :src="npc.avatar" :alt="npc.name" />
      </div>
      <div class="npc-body">
        <span class="npc-name locked-name">{{ npc.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { useMockStore } from '../stores/mockStore'
import { storeToRefs } from 'pinia'

defineProps<{ collapsed: boolean }>()
defineEmits<{ select: [npcId: string] }>()

const store = useGameStore()
const mock = useMockStore()
const { currentNPC } = storeToRefs(store)
</script>

<style scoped>
.npc-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
  flex: 1;
  overflow-y: auto;
}

.npc-panel h3 {
  margin-bottom: var(--gap-sm);
  font-size: var(--font-size-sm);
}

.npc-card {
  display: flex;
  gap: 12px;
  padding: var(--gap-sm) var(--gap-md);
  margin-bottom: var(--gap-sm);
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.15s;
  align-items: center;
}

.npc-card:hover { border-color: var(--color-border-light); }
.npc-card--active { border-color: var(--color-accent); }

.npc-card--locked {
  opacity: 0.55;
  border-style: dashed;
  cursor: default;
}
.npc-card--locked:hover { border-color: var(--color-border); }

.npc-avatar {
  width: 64px;
  height: 64px;
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.npc-avatar img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
}

.npc-avatar--locked { filter: grayscale(70%); }

.npc-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.npc-name {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
  white-space: nowrap;
}

.locked-name { color: var(--color-text-dim); }

.npc-rel {
  display: flex;
  align-items: center;
  gap: 6px;
}

.rel-bar {
  flex: 1;
  max-width: 80px;
  height: 8px;
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
  font-size: 10px;
  color: var(--color-health);
}

.locked-divider {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-text-dim);
  margin: var(--gap-sm) 0;
  padding-bottom: 2px;
  border-bottom: 1px solid var(--color-border);
}
</style>
