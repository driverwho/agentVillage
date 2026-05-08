<template>
  <div class="dice-roller">
    <div class="dice-display" :class="{ 'dice-rolling': rolling }">
      <span class="dice-number">{{ displayNumber }}</span>
    </div>
    <button
      class="dice-btn"
      :disabled="rolling"
      @click="roll"
    >
      🎲 掷骰子
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMockStore } from '../stores/mockStore'

const mock = useMockStore()
const rolling = ref(false)
const displayNumber = ref('?')

const emit = defineEmits<{
  result: [value: number, success: boolean]
}>()

async function roll() {
  if (rolling.value) return
  rolling.value = true

  const duration = 800
  const interval = 60
  const start = Date.now()
  const timer = setInterval(() => {
    displayNumber.value = String(Math.floor(Math.random() * 20) + 1)
    if (Date.now() - start >= duration) {
      clearInterval(timer)
      const result = mock.rollDice()
      displayNumber.value = String(result.result)
      rolling.value = false
      emit('result', result.result, result.success)
    }
  }, interval)
}
</script>

<style scoped>
.dice-roller {
  text-align: center;
}

.dice-display {
  width: 80px;
  height: 80px;
  margin: 0 auto 8px;
  background: var(--color-bg);
  border: 3px solid var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  image-rendering: pixelated;
}

.dice-rolling {
  animation: dice-shake 0.1s infinite alternate;
  border-color: var(--color-accent-light);
}

@keyframes dice-shake {
  from { transform: rotate(-5deg); }
  to { transform: rotate(5deg); }
}

.dice-number {
  font-family: var(--font-pixel);
  font-size: var(--font-size-lg);
  color: var(--color-accent);
}

.dice-btn {
  font-size: var(--font-size-xs);
}
</style>
