<template>
  <div class="status-panel">
    <h3>玩家状态</h3>
    <div v-if="player" class="status-body">
      <div class="stat-row">
        <span class="stat-label">生命</span>
        <div class="stat-bar">
          <div class="stat-fill health" :style="{ width: player.health + '%' }"></div>
        </div>
        <span class="stat-val">{{ player.health }}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">饥饿</span>
        <div class="stat-bar">
          <div class="stat-fill hunger" :style="{ width: player.hunger + '%' }"></div>
        </div>
        <span class="stat-val">{{ player.hunger }}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">疲劳</span>
        <div class="stat-bar">
          <div class="stat-fill fatigue" :style="{ width: player.fatigue + '%' }"></div>
        </div>
        <span class="stat-val">{{ player.fatigue }}</span>
      </div>
      <div class="stat-row gold">
        <span class="stat-label">金币</span>
        <span class="stat-val gold-val">{{ player.gold }}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">耕作</span>
        <span class="stat-val">{{ player.farm_count }} 次</span>
      </div>
      <div v-if="player.relationships && Object.keys(player.relationships).length" class="relations">
        <div class="stat-label">好感度</div>
        <div v-for="(val, key) in player.relationships" :key="key" class="rel-row">
          <span>{{ key }}</span>
          <div class="stat-bar rel-bar">
            <div class="stat-fill health" :style="{ width: val + '%' }"></div>
          </div>
          <span class="stat-val">{{ val }}</span>
        </div>
      </div>
    </div>
    <div v-else class="loading">加载中...</div>
  </div>
</template>

<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { storeToRefs } from 'pinia'

const store = useGameStore()
const { player } = storeToRefs(store)
</script>

<style scoped>
.status-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}

.status-panel h3 {
  margin-bottom: var(--gap-sm);
  font-size: var(--font-size-sm);
}

.status-body {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.stat-row {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.stat-label {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-text-dim);
  width: 36px;
  flex-shrink: 0;
}

.stat-val {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  width: 32px;
  text-align: right;
  flex-shrink: 0;
}

.stat-bar {
  flex: 1;
  height: 10px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}

.stat-fill {
  height: 100%;
  transition: width 0.3s step-end;
}

.stat-fill.health { background: var(--color-health); }
.stat-fill.hunger { background: var(--color-hunger); }
.stat-fill.fatigue { background: var(--color-fatigue); }

.gold-val {
  color: var(--color-accent-light);
}

.relations {
  margin-top: var(--gap-xs);
}

.rel-row {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  margin-top: 2px;
  font-size: var(--font-size-sm);
}

.rel-bar {
  max-width: 80px;
}

.loading {
  color: var(--color-text-dim);
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}
</style>
