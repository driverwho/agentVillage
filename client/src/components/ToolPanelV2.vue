<template>
  <div class="tool-panel">
    <h3>可用工具</h3>
    <div class="tool-grid">
      <button
        v-for="tool in mock.tools"
        :key="tool.id"
        class="tool-btn"
        :class="{ 'tool-locked': !tool.unlocked }"
        :disabled="!tool.unlocked && tool.trustRequired > 0"
        @click="handleToolClick(tool)"
      >
        <span class="tool-icon">{{ tool.icon }}</span>
        <span class="tool-name">{{ tool.name }}</span>
        <span class="tool-lock" v-if="!tool.unlocked">🔒</span>
      </button>
    </div>
    <p v-if="toolMessage" class="tool-msg" :class="{ 'tool-err': isError }">
      {{ toolMessage }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useGameStore } from '../stores/gameStore'
import { useMockStore } from '../stores/mockStore'
import type { ToolDef } from '../types'

const store = useGameStore()
const mock = useMockStore()
const toolMessage = ref('')
const isError = ref(false)

async function handleToolClick(tool: ToolDef) {
  if (!tool.unlocked) {
    mock.useLockedTool(tool)
    return
  }

  if (tool.id === 'farming') {
    toolMessage.value = ''
    isError.value = false
    try {
      const result = await store.useFarmingTool()
      toolMessage.value = result.message || '耕作完成！'
    } catch (e: any) {
      toolMessage.value = e.response?.data?.detail || '耕作失败'
      isError.value = true
    }
  }
}
</script>

<style scoped>
.tool-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}

.tool-panel h3 {
  margin-bottom: var(--gap-sm);
  font-size: var(--font-size-sm);
}

.tool-grid {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
}

.tool-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: var(--font-size-xs);
}

.tool-locked {
  opacity: 0.4;
}

.tool-icon {
  font-size: 14px;
}

.tool-name {
  font-family: var(--font-pixel);
}

.tool-lock {
  font-size: 10px;
  opacity: 0.6;
}

.tool-msg {
  margin-top: var(--gap-sm);
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-health);
}

.tool-err {
  color: var(--color-fatigue);
}
</style>
