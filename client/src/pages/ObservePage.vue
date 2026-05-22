<template>
  <div class="observe-page">
    <header class="observe-header">
      <h1 class="observe-title">Agent Village — NPC 观察面板</h1>
      <router-link to="/" class="back-btn">返回游戏</router-link>
    </header>
    <div class="observe-grid">
      <p style="color: var(--color-text-dim);">加载中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.observe-page {
  min-height: 100vh;
  padding: var(--gap-md);
  max-width: 1400px;
  margin: 0 auto;
}

.observe-header {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--gap-md);
}

.observe-title {
  font-size: var(--font-size-lg);
  margin: 0;
}

.back-btn {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
  text-decoration: none;
  border: 2px solid var(--color-border);
  padding: 6px 12px;
}

.back-btn:hover {
  border-color: var(--color-accent);
}

.observe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--gap-md);
}
</style>
