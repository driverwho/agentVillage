<template>
  <div class="eavesdrop-panel">
    <h3>👂 偷听</h3>
    <div class="quota-label">
      今日剩余 <span class="quota-num">{{ mock.eavesdropQuota }}</span> 次
    </div>

    <div class="eavesdrop-targets">
      <div
        v-for="npc in mock.unlockedNPCs"
        :key="npc.id"
        class="target-chip"
        :class="{ 'target-selected': selected.includes(npc.id) }"
        @click="toggleTarget(npc.id)"
      >
        <img :src="avatarSmall(npc.avatar)" :alt="npc.name" class="chip-avatar" /> {{ npc.name }}
      </div>
    </div>

    <button
      class="eavesdrop-btn"
      :disabled="selected.length < 2 || mock.eavesdropQuota <= 0"
      @click="doEavesdrop"
    >
      偷听 ({{ selected.length }}/2)
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMockStore } from '../stores/mockStore'

const mock = useMockStore()
const selected = ref<string[]>([])

function avatarSmall(path: string): string {
  return path.replace('/avatars/', '/avatars/32/')
}

function toggleTarget(id: string) {
  const idx = selected.value.indexOf(id)
  if (idx >= 0) {
    selected.value.splice(idx, 1)
  } else if (selected.value.length < 2) {
    selected.value.push(id)
  }
}

function doEavesdrop() {
  if (selected.value.length < 2) return
  mock.doEavesdrop([...selected.value])
  selected.value = []
}
</script>

<style scoped>
.eavesdrop-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}

.eavesdrop-panel h3 {
  margin-bottom: 2px;
  font-size: var(--font-size-sm);
}

.quota-label {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-text-dim);
  margin-bottom: var(--gap-sm);
}

.quota-num { color: var(--color-accent); }

.eavesdrop-targets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--gap-sm);
}

.target-chip {
  font-family: var(--font-pixel);
  font-size: 10px;
  padding: 4px 8px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.15s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.chip-avatar {
  width: 20px;
  height: 20px;
  object-fit: contain;
  image-rendering: pixelated;
}

.target-chip:hover { border-color: var(--color-border-light); }

.target-selected {
  border-color: var(--color-info);
  color: var(--color-info);
}

.eavesdrop-btn { width: 100%; }
</style>
