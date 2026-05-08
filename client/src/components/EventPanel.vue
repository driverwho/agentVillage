<template>
  <div class="event-panel">
    <h3>⚡ 每日事件</h3>
    <div class="quota-label">
      今日剩余 <span class="quota-num">{{ mock.dailyEventQuota }}</span> 次
    </div>

    <!-- 随机事件卡 -->
    <div class="event-cards">
      <div
        v-for="event in mock.randomEvents.slice(0, 3)"
        :key="event.id"
        class="event-card"
        @click="drawEvent(event)"
      >
        <span class="event-icon">{{ event.icon }}</span>
        <span class="event-name">{{ event.name }}</span>
      </div>
    </div>
    <button class="draw-btn" @click="drawRandom()">
      🎴 随机抽一张
    </button>

    <!-- 分隔 -->
    <div class="divider">或</div>

    <!-- 自定义事件 -->
    <div class="custom-event">
      <input
        v-model="customText"
        placeholder="自定义事件..."
        @keyup.enter="submitCustom"
      />
      <button @click="submitCustom">提交</button>
    </div>

    <!-- 骰子 -->
    <div class="divider">D20 判定</div>
    <DiceRoller @result="onDiceResult" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMockStore } from '../stores/mockStore'
import DiceRoller from './DiceRoller.vue'
import type { RandomEvent } from '../types'

const mock = useMockStore()
const customText = ref('')

function drawRandom() {
  mock.drawRandomEvent()
}

function drawEvent(event: RandomEvent) {
  mock.currentEvent = event
  mock.drawRandomEvent()
}

function submitCustom() {
  mock.submitCustomEvent(customText.value)
  customText.value = ''
}

function onDiceResult(_value: number, _success: boolean) {
  // handled inside DiceRoller via mock.rollDice()
}
</script>

<style scoped>
.event-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}

.event-panel h3 {
  margin-bottom: 2px;
  font-size: var(--font-size-sm);
}

.quota-label {
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-text-dim);
  margin-bottom: var(--gap-sm);
}

.quota-num {
  color: var(--color-accent);
}

.event-cards {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: var(--gap-sm);
}

.event-card {
  flex: 1;
  min-width: 70px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  padding: 6px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s;
}

.event-card:hover {
  border-color: var(--color-accent);
}

.event-icon {
  font-size: 18px;
  display: block;
}

.event-name {
  font-family: var(--font-pixel);
  font-size: 7px;
  color: var(--color-text-dim);
  margin-top: 2px;
  display: block;
}

.draw-btn {
  width: 100%;
  margin-bottom: var(--gap-sm);
}

.divider {
  text-align: center;
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-text-dim);
  margin: var(--gap-sm) 0;
  position: relative;
}

.divider::before,
.divider::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 30%;
  height: 1px;
  background: var(--color-border);
}

.divider::before { left: 0; }
.divider::after { right: 0; }

.custom-event {
  display: flex;
  gap: var(--gap-xs);
}

.custom-event input {
  flex: 1;
  font-size: 10px;
  padding: 5px;
}
</style>
