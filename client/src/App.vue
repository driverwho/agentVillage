<template>
  <div class="game-container">
    <header class="game-header">
      <h1 class="game-title">Agent Village</h1>
      <TimeControl />
    </header>

    <aside class="col-left">
      <StatusPanel />
      <NPCPanel @select="store.selectNPC" />
    </aside>

    <main class="col-center">
      <ChatPanel />
      <ToolPanelV2 />
    </main>

    <aside class="col-right">
      <EventPanel />
      <EavesdropPanel />
      <NotebookPanel />
    </aside>

    <!-- Toast overlay -->
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
import { onMounted } from 'vue'
import TimeControl from './components/TimeControl.vue'
import StatusPanel from './components/StatusPanel.vue'
import NPCPanel from './components/NPCPanel.vue'
import ChatPanel from './components/ChatPanel.vue'
import ToolPanelV2 from './components/ToolPanelV2.vue'
import EventPanel from './components/EventPanel.vue'
import EavesdropPanel from './components/EavesdropPanel.vue'
import NotebookPanel from './components/NotebookPanel.vue'
import { useGameStore } from './stores/gameStore'
import { toasts } from './services/toast'

const store = useGameStore()

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
  grid-template-columns: 260px 1fr 280px;
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

.col-left {
  grid-area: left;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}

.col-center {
  grid-area: center;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  min-width: 400px;
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}

.col-right {
  grid-area: right;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}

/* Toast overlay */
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

/* Responsive */
@media (max-width: 1000px) {
  .game-container {
    grid-template-areas:
      "header header"
      "left   center"
      "right  right";
    grid-template-columns: 260px 1fr;
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
  .col-left, .col-center, .col-right {
    max-height: none;
  }
}
</style>
