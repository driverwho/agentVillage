<template>
  <div class="time-control">
    <div class="time-display">
      Day {{ world?.game_time.day }} {{ world?.game_time.hour }}:00
      {{ world?.is_paused ? '(已暂停)' : '' }}
    </div>
    <div class="controls">
      <button @click="advanceTime(60)">推进1小时</button>
      <button @click="advanceTime(360)">推进6小时</button>
      <button @click="advanceTime(1440)">推进1天</button>
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
