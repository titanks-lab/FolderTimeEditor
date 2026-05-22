<script setup lang="ts">
import { useAppStore } from '@/stores/appStore'
import { computed, nextTick, watch, ref } from 'vue'

const store = useAppStore()

const logContainer = ref<HTMLDivElement | null>(null)

const totalCount = computed(() => store.progressBar.total)
const progressPercent = computed(() => totalCount.value > 0 ? Math.round((store.progressBar.current / totalCount.value) * 100) : 0)

// 自动滚动到底部
watch(() => store.logMessages.length, async () => {
  await nextTick()
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
})
</script>

<template>
  <div class="operation-log">
    <div class="log-header">
      <span class="log-title">📋 操作日志</span>
      <div class="log-stats">
        <span v-if="totalCount > 0" class="log-progress">
          <progress :value="store.progressBar.current" :max="totalCount"></progress>
          <span class="progress-text">{{ progressPercent }}% ({{ store.progressBar.current }}/{{ totalCount }})</span>
        </span>
        <span class="stat success">成功: {{ store.successCount }}</span>
        <span class="stat fail">失败: {{ store.failCount }}</span>
        <button class="btn btn-sm" @click="store.clearLog()">清理</button>
      </div>
    </div>
    <div class="log-body" ref="logContainer">
      <textarea class="log-textarea" readonly :value="store.logMessages.join('\n')"></textarea>
    </div>
  </div>
</template>

<style scoped>
.operation-log {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 80px;
  border-top: 2px solid var(--border-color);
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 12px;
  background: var(--bg-header);
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
  gap: 4px;
}

.log-title {
  font-weight: 600;
  font-size: 12px;
}

.log-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
}

.log-progress {
  display: flex;
  align-items: center;
  gap: 4px;
}

.progress-text {
  color: var(--text-secondary);
  white-space: nowrap;
}

.stat {
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 600;
}

.stat.success {
  color: var(--accent-green);
  background: rgba(40, 167, 69, 0.1);
}

.stat.fail {
  color: var(--accent-red);
  background: rgba(220, 53, 69, 0.1);
}

.log-body {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.log-textarea {
  width: 100%;
  height: 100%;
  resize: none;
  border: none;
  background: transparent;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  padding: 4px 8px;
  line-height: 1.5;
  overflow-y: auto;
}
</style>
