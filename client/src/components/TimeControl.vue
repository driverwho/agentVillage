<template>
  <div class="time-control">
    <span class="time-display">
      Day {{ world?.game_time.day }} {{ world?.game_time.hour }}:00
      {{ world?.is_paused ? '(已暂停)' : '' }}
    </span>
    <div class="time-buttons">
      <button class="time-btn" @click="advanceTime(60)">+1h</button>
      <button class="time-btn" @click="advanceTime(360)">+6h</button>
      <button class="time-btn" @click="advanceTime(1440)">+1天</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { storeToRefs } from 'pinia'

const store = useGameStore()
const { world } = storeToRefs(store)
const { advanceTime } = store
</script>

<style scoped>
.time-control {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.time-display {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
}

.time-buttons {
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
</style>
