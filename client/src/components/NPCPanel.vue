<template>
  <div class="npc-panel">
    <h3>NPC状态</h3>
    <div v-for="(npc, id) in world?.npcs" :key="id" class="npc-card">
      <strong>{{ id }}</strong>
      <div>健康: {{ npc.state.health }} 饥饿: {{ npc.state.hunger }} 疲惫: {{ npc.state.fatigue }} 心情: {{ npc.state.mood }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { storeToRefs } from 'pinia'

const store = useGameStore()
const { world } = storeToRefs(store)
</script>
