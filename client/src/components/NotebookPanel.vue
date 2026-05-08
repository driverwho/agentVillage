<template>
  <div class="notebook-panel">
    <h3>📜 笔记簿</h3>

    <!-- Tab 栏 -->
    <div class="nb-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="nb-tab"
        :class="{ 'nb-tab--active': mock.notebookTab === tab.id }"
        @click="mock.notebookTab = tab.id"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- 事件时间线 -->
    <div class="nb-content" v-if="mock.notebookTab === 'timeline'">
      <div v-for="(entry, i) in mock.timeline" :key="i" class="nb-entry">
        <span class="nb-day">Day {{ entry.day }}</span>
        <span class="nb-source" :class="'src-' + entry.source">
          {{ sourceLabel(entry.source) }}
        </span>
        <span class="nb-text">{{ entry.text }}</span>
      </div>
    </div>

    <!-- NPC 观察 -->
    <div class="nb-content" v-if="mock.notebookTab === 'npc'">
      <div v-for="obs in mock.npcObservations" :key="obs.npcId" class="nb-npc-group">
        <div class="nb-npc-name">
          {{ getNPCName(obs.npcId) }}
        </div>
        <div v-for="(entry, i) in obs.entries" :key="i" class="nb-entry">
          <span class="nb-day">Day {{ entry.day }}</span>
          <span class="nb-text">{{ entry.text }}</span>
        </div>
      </div>
    </div>

    <!-- 玩家行动 -->
    <div class="nb-content" v-if="mock.notebookTab === 'actions'">
      <div v-for="(action, i) in mock.playerActions" :key="i" class="nb-entry">
        <span class="nb-day">Day {{ action.day }}</span>
        <span class="nb-text">{{ action.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useMockStore } from '../stores/mockStore'

const mock = useMockStore()

const tabs = [
  { id: 'timeline' as const, icon: '📋', label: '时间线' },
  { id: 'npc' as const, icon: '👤', label: 'NPC' },
  { id: 'actions' as const, icon: '💬', label: '行动' },
]

function sourceLabel(source: string): string {
  const map: Record<string, string> = { witnessed: '目击', heard: '听说', inferred: '推测' }
  return map[source] || source
}

function getNPCName(npcId: string): string {
  return mock.npcs.find(n => n.id === npcId)?.name || npcId
}
</script>

<style scoped>
.notebook-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 150px;
}

.notebook-panel h3 {
  margin-bottom: var(--gap-sm);
  font-size: var(--font-size-sm);
}

.nb-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: var(--gap-sm);
}

.nb-tab {
  flex: 1;
  font-size: 8px;
  padding: 4px 6px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.15s;
}

.nb-tab--active {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.nb-content {
  flex: 1;
  overflow-y: auto;
  max-height: 250px;
  font-size: 10px;
}

.nb-entry {
  padding: 4px 0;
  border-bottom: 1px solid var(--color-border);
  line-height: 1.5;
}

.nb-day {
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-accent);
  margin-right: 6px;
}

.nb-source {
  font-family: var(--font-pixel);
  font-size: 7px;
  padding: 1px 3px;
  margin-right: 4px;
}

.src-witnessed { color: var(--color-health); }
.src-heard { color: var(--color-info); }
.src-inferred { color: var(--color-hunger); }

.nb-text {
  color: var(--color-text-dim);
}

.nb-npc-group {
  margin-bottom: var(--gap-sm);
}

.nb-npc-name {
  font-family: var(--font-pixel);
  font-size: 9px;
  color: var(--color-accent-light);
  margin-bottom: 4px;
  padding-bottom: 2px;
  border-bottom: 1px solid var(--color-accent);
}
</style>
