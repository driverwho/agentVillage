<template>
  <div class="tool-panel">
    <h3>可用工具</h3>
    <button @click="useFarming" :disabled="farmingInProgress">耕作</button>
    <p v-if="toolMessage">{{ toolMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useGameStore } from '../stores/gameStore'

const store = useGameStore()
const farmingInProgress = ref(false)
const toolMessage = ref('')

async function useFarming() {
  farmingInProgress.value = true
  try {
    await store.sendMessage('farmer', '使用耕作工具')
    toolMessage.value = '耕作完成！'
  } catch (e) {
    toolMessage.value = '耕作失败'
  }
  farmingInProgress.value = false
}
</script>
