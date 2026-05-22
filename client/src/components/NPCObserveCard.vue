<template>
  <div class="observe-card" :class="{ 'observe-card--active': npc.activity.status === 'active' }">
    <div class="observe-avatar">
      <img :src="npc.avatar" :alt="npc.name" />
    </div>

    <div class="observe-info">
      <h3 class="observe-name">{{ npc.name }}</h3>
      <div class="observe-meta">
        <span class="meta-item">{{ locationName }}</span>
        <span class="meta-item" v-if="npc.activity.status === 'active'">
          {{ npc.activity.currentTool }}
        </span>
        <span class="meta-item" v-else>空闲</span>
        <span class="meta-item" v-if="npc.activity.endHour !== null">
          到 Day{{ npc.activity.endDay }} {{ npc.activity.endHour }}:00
        </span>
      </div>
    </div>

    <div class="observe-bars">
      <div class="bar-row">
        <span class="bar-label">HP</span>
        <div class="bar-track"><div class="bar-fill bar-fill--health" :style="{ width: npc.state.health + '%' }"></div></div>
        <span class="bar-val">{{ npc.state.health }}</span>
      </div>
      <div class="bar-row">
        <span class="bar-label">饱</span>
        <div class="bar-track"><div class="bar-fill bar-fill--hunger" :style="{ width: npc.state.hunger + '%' }"></div></div>
        <span class="bar-val">{{ npc.state.hunger }}</span>
      </div>
      <div class="bar-row">
        <span class="bar-label">疲</span>
        <div class="bar-track"><div class="bar-fill bar-fill--fatigue" :style="{ width: npc.state.fatigue + '%' }"></div></div>
        <span class="bar-val">{{ npc.state.fatigue }}</span>
      </div>
      <div class="bar-row">
        <span class="bar-label">情</span>
        <div class="bar-track"><div class="bar-fill bar-fill--mood" :style="{ width: npc.state.mood + '%' }"></div></div>
        <span class="bar-val">{{ npc.state.mood }}</span>
      </div>
    </div>

    <div class="observe-llm">
      <span v-if="npc.llmStatus === 'requesting'" class="llm-badge llm-badge--requesting">requesting...</span>
      <span v-else-if="npc.llmStatus === 'done'" class="llm-badge llm-badge--done">done</span>
      <span v-else class="llm-badge llm-badge--idle">idle</span>
    </div>

    <div class="observe-history" v-if="npc.history.length > 0">
      <div class="history-title">最近调用</div>
      <div v-for="(entry, idx) in npc.history" :key="idx" class="history-entry">
        <span class="history-time">{{ entry.timestamp }}</span>
        <span class="history-tool">{{ entry.tool }}</span>
        <span class="history-msg">{{ entry.message }}</span>
        <span class="history-tokens" v-if="entry.tokens > 0">{{ entry.tokens }}t</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NPCObserveData } from '../stores/observeStore'

const props = defineProps<{ npc: NPCObserveData }>()

const LOCATION_NAMES: Record<string, string> = {
  home: '家', field: '田地', tavern: '酒馆',
  market: '市场', church: '教堂', forest: '森林',
}

const locationName = computed(() => LOCATION_NAMES[props.npc.location] || props.npc.location)
</script>

<style scoped>
.observe-card {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.observe-card--active {
  border-color: var(--color-accent);
}

.observe-avatar {
  width: 128px;
  height: 128px;
  margin: 0 auto;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  overflow: hidden;
}

.observe-avatar img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
}

.observe-info {
  text-align: center;
}

.observe-name {
  font-family: var(--font-pixel);
  font-size: var(--font-size-sm);
  color: var(--color-accent);
  margin: 0 0 4px 0;
}

.observe-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  font-size: var(--font-size-xs);
  color: var(--color-text-dim);
}

.observe-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.bar-label {
  font-family: var(--font-pixel);
  font-size: 10px;
  width: 20px;
  color: var(--color-text-dim);
}

.bar-track {
  flex: 1;
  height: 10px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}

.bar-fill {
  height: 100%;
  transition: width 0.3s;
}

.bar-fill--health { background: var(--color-health); }
.bar-fill--hunger { background: var(--color-hunger); }
.bar-fill--fatigue { background: var(--color-fatigue); }
.bar-fill--mood { background: var(--color-info); }

.bar-val {
  font-family: var(--font-pixel);
  font-size: 10px;
  width: 24px;
  text-align: right;
  color: var(--color-text);
}

.observe-llm {
  text-align: center;
  padding: 4px 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.llm-badge {
  font-family: var(--font-pixel);
  font-size: 10px;
}

.llm-badge--requesting { color: var(--color-hunger); }
.llm-badge--done { color: var(--color-health); }
.llm-badge--idle { color: var(--color-text-dim); }

.observe-history {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-title {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-text-dim);
  margin-bottom: 2px;
}

.history-entry {
  display: flex;
  gap: 6px;
  align-items: baseline;
  font-size: 11px;
  color: var(--color-text);
  padding: 2px 4px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}

.history-time {
  font-family: var(--font-pixel);
  font-size: 9px;
  color: var(--color-text-dim);
  white-space: nowrap;
}

.history-tool {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-accent);
  white-space: nowrap;
}

.history-msg {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-dim);
}

.history-tokens {
  font-family: var(--font-pixel);
  font-size: 9px;
  color: var(--color-info);
  white-space: nowrap;
}
</style>
