<template>
  <div class="game-container">
    <h1>Agent Village</h1>
    <TimeControl />
    <StatusPanel />
    <NPCPanel />
    <ChatPanel />
    <ToolPanel />
  </div>
</template>

<script setup lang="ts">
import TimeControl from './components/TimeControl.vue'
import StatusPanel from './components/StatusPanel.vue'
import NPCPanel from './components/NPCPanel.vue'
import ChatPanel from './components/ChatPanel.vue'
import ToolPanel from './components/ToolPanel.vue'
</script>
