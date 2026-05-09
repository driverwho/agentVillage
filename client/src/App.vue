<template>
  <div class="game-container">
    <header class="game-header">
      <h1 class="game-title">Agent Village / 麦穗小镇</h1>
      <TimeControl />
    </header>

    <aside class="col-left" :class="{ 'col-left--folded': leftCollapsed }">
      <div class="left-top-row">
        <div class="sidebar-toggle" @click="leftCollapsed = !leftCollapsed" :title="leftCollapsed ? '展开' : '折叠'">
          <span class="toggle-arrow">{{ leftCollapsed ? '▶' : '◀' }}</span>
        </div>
        <StatusPanel :collapsed="leftCollapsed" />
      </div>
      <NPCPanel :collapsed="leftCollapsed" @select="store.selectNPC" />
    </aside>

    <main class="col-center">
      <div class="switch-panel">
        <div class="switch-tabs">
          <button
            class="switch-tab"
            :class="{ 'switch-tab--active': centerTab === 'chat' }"
            @click="centerTab = 'chat'"
          >💬 对话</button>
          <button
            class="switch-tab"
            :class="{ 'switch-tab--active': centerTab === 'tavern' }"
            @click="centerTab = 'tavern'"
          >🍺 酒馆</button>
        </div>
        <ChatPanel v-show="centerTab === 'chat'" />
        <TavernPanel v-show="centerTab === 'tavern'" />
      </div>
      <ToolPanelV2 />
    </main>

    <aside class="col-right">
      <div class="switch-panel">
        <div class="switch-tabs">
          <button
            class="switch-tab"
            :class="{ 'switch-tab--active': rightTab === 'event' }"
            @click="rightTab = 'event'"
          >⚡ 事件</button>
          <button
            class="switch-tab"
            :class="{ 'switch-tab--active': rightTab === 'notebook' }"
            @click="rightTab = 'notebook'"
          >📜 笔记</button>
        </div>
        <EventPanel v-show="rightTab === 'event'" />
        <NotebookPanel v-show="rightTab === 'notebook'" />
      </div>
      <EavesdropPanel />
    </aside>

    <div class="toast-container" v-if="toasts.length">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast-item"
        :class="{ 'toast-leaving': !t.visible }"
      >
        {{ t.message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import TimeControl from './components/TimeControl.vue'
import StatusPanel from './components/StatusPanel.vue'
import NPCPanel from './components/NPCPanel.vue'
import ChatPanel from './components/ChatPanel.vue'
import ToolPanelV2 from './components/ToolPanelV2.vue'
import EventPanel from './components/EventPanel.vue'
import EavesdropPanel from './components/EavesdropPanel.vue'
import NotebookPanel from './components/NotebookPanel.vue'
import TavernPanel from './components/TavernPanel.vue'
import { useGameStore } from './stores/gameStore'
import { toasts } from './services/toast'

const store = useGameStore()
const leftCollapsed = ref(false)
const centerTab = ref<'chat' | 'tavern'>('chat')
const rightTab = ref<'event' | 'notebook'>('event')

onMounted(async () => {
  await Promise.all([store.fetchWorld(), store.fetchPlayer()])
})
</script>

<style>
.game-container {
  max-width: 1400px;
  min-height: 100vh;
  margin: 0 auto;
  padding: var(--gap-md);
  display: grid;
  grid-template-areas:
    "header header header"
    "left   center right";
  grid-template-columns: auto 1fr 280px;
  grid-template-rows: auto 1fr;
  gap: var(--gap-md);
}

.game-header {
  grid-area: header;
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.game-title {
  font-size: var(--font-size-lg);
  margin: 0;
  white-space: nowrap;
}

/* ── Left column ── */
.col-left {
  grid-area: left;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}

.col-left--folded { overflow-y: visible; }

.left-top-row {
  display: flex;
  border: 2px solid var(--color-border);
  background: var(--color-panel);
}

.sidebar-toggle {
  width: 10%;
  min-width: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  border-right: 2px solid var(--color-border);
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}

.sidebar-toggle:hover { color: var(--color-accent); }
.col-left--folded .sidebar-toggle { width: 28px; }

.toggle-arrow {
  font-size: 10px;
  color: var(--color-text-dim);
}

/* ── Center column ── */
.col-center {
  grid-area: center;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  min-width: 400px;
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}

/* ── Right column ── */
.col-right {
  grid-area: right;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}

/* ── Switch panels ── */
.switch-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  border: 2px solid var(--color-border);
  background: var(--color-panel);
}

.switch-tabs {
  display: flex;
  gap: 4px;
  padding: var(--gap-sm);
  background: var(--color-bg);
  border-bottom: 2px solid var(--color-border);
}

.switch-tab {
  flex: 1;
  font-size: var(--font-size-xs);
  padding: 4px 8px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  text-align: center;
}

.switch-tab--active {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

/* ── Toast ── */
.toast-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast-item {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-bg);
  background: var(--color-accent);
  border: 2px solid var(--color-accent-light);
  padding: 8px 16px;
  text-align: center;
  animation: toast-in 0.3s ease-out;
  pointer-events: auto;
}

.toast-leaving {
  opacity: 0;
  transition: opacity 0.3s ease-out;
}

@keyframes toast-in {
  from { transform: translateY(-20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* ── Responsive ── */
@media (max-width: 1000px) {
  .game-container {
    grid-template-areas:
      "header header"
      "left   center"
      "right  right";
    grid-template-columns: auto 1fr;
  }
  .col-right {
    flex-direction: row;
    max-height: none;
  }
}

@media (max-width: 700px) {
  .game-container {
    grid-template-areas:
      "header"
      "left"
      "center"
      "right";
    grid-template-columns: 1fr;
  }
  .col-left, .col-center, .col-right { max-height: none; }
}
</style>
