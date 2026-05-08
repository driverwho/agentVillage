<template>
  <div class="status-panel" v-if="player">
    <h3>玩家状态</h3>
    <div class="status-grid">
      <div>健康: {{ player.health }}</div>
      <div>饥饿: {{ player.hunger }}</div>
      <div>疲惫: {{ player.fatigue }}</div>
      <div>金币: {{ player.gold }}</div>
      <div>耕作次数: {{ player.farm_count }}</div>
      <div v-if="player.relationships && Object.keys(player.relationships).length">
        好感度:
        <ul>
          <li v-for="(val, key) in player.relationships" :key="key">
            {{ key }}: {{ val }}
          </li>
        </ul>
      </div>
    </div>
  </div>
  <div v-else>加载中...</div>
</template>

<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { storeToRefs } from 'pinia'

const store = useGameStore()
const { player } = storeToRefs(store)
</script>
