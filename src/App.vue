<script setup lang="ts">
import FileList from '@/components/FileList.vue'
import TimeSettings from '@/components/TimeSettings.vue'
import OperationLog from '@/components/OperationLog.vue'
import PreviewDialog from '@/components/PreviewDialog.vue'
import ProfileDialog from '@/components/ProfileDialog.vue'

import { ref, onMounted, onBeforeUnmount } from 'vue'

const leftPanel = ref<HTMLDivElement | null>(null)
const resizer = ref<HTMLDivElement | null>(null)
const isResizing = ref(false)

const MIN_LEFT_WIDTH = 300
const MAX_LEFT_WIDTH = 800

onMounted(() => {
  if (!resizer.value || !leftPanel.value) return

  resizer.value.addEventListener('mousedown', startResize)
  window.addEventListener('mousemove', doResize)
  window.addEventListener('mouseup', stopResize)
})

onBeforeUnmount(() => {
  if (resizer.value) {
    resizer.value.removeEventListener('mousedown', startResize)
  }
  window.removeEventListener('mousemove', doResize)
  window.removeEventListener('mouseup', stopResize)
})

function startResize(_e: MouseEvent) {
  isResizing.value = true
  resizer.value?.classList.add('active')
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function doResize(e: MouseEvent) {
  if (!isResizing.value || !leftPanel.value) return
  const newWidth = e.clientX
  const clamped = Math.max(MIN_LEFT_WIDTH, Math.min(MAX_LEFT_WIDTH, newWidth))
  leftPanel.value.style.flexBasis = `${clamped}px`
}

function stopResize() {
  if (!isResizing.value) return
  isResizing.value = false
  resizer.value?.classList.remove('active')
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}
</script>

<template>
  <div class="app-layout">
    <!-- 顶部工具栏 -->
    <header class="app-header">
      <h1 class="app-title">🕑 FolderTimeEditor</h1>
      <span class="app-subtitle">文件时间属性编辑器</span>
    </header>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：文件列表 -->
      <div ref="leftPanel" class="panel left-panel" style="flex-basis: 500px">
        <FileList />
      </div>

      <!-- 可拖动分割线 -->
      <div ref="resizer" class="resizer"></div>

      <!-- 右侧：时间设置 -->
      <div class="panel right-panel">
        <TimeSettings />
      </div>
    </div>

    <!-- 底部：操作日志 -->
    <OperationLog />

    <!-- 模态对话框 -->
    <PreviewDialog />
    <ProfileDialog />
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.app-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 16px;
  background: var(--bg-header);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.app-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.app-subtitle {
  font-size: 12px;
  color: var(--text-muted);
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 200px;
}

.left-panel {
  border-right: 1px solid var(--border-color);
}

.right-panel {
  flex: 1;
  min-width: 250px;
}

.resizer {
  width: 5px;
  cursor: col-resize;
  background: var(--border-light);
  transition: background 0.15s;
  flex-shrink: 0;
  position: relative;
}

.resizer:hover,
.resizer.active {
  background: var(--accent-blue);
}

.resizer::after {
  content: '⋮';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--text-muted);
  font-size: 12px;
  pointer-events: none;
}
</style>
