<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/appStore'
import type { FileInfo } from '@/types'
import { invoke } from '@tauri-apps/api/core'
import { open } from '@tauri-apps/plugin-dialog'

const store = useAppStore()

const isFolderPicker = ref(true)

// ---- 添加文件夹 ----
async function addFolder() {
  try {
    isFolderPicker.value = true
    const selected = await open({
      title: '选择要添加的文件夹',
      directory: true,
      multiple: true,
    })
    if (!selected) return

    const paths = Array.isArray(selected) ? selected : [selected]
    for (const p of paths) {
      const files = await invoke<FileInfo[]>('walk_directory', { path: p, recursive: true })
      store.addFiles(files)
      store.addLog(`已添加文件夹: ${p}`)
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    store.addLog(`添加文件夹失败: ${msg}`)
    alert('添加文件夹失败: ' + msg)
  }
}

// ---- 添加文件 ----
async function addFile() {
  try {
    isFolderPicker.value = false
    const selected = await open({
      title: '选择要添加的文件',
      multiple: true,
    })
    if (!selected) return

    const paths = Array.isArray(selected) ? selected : [selected]
    for (const p of paths) {
      // 使用 walk_directory 获取单个文件信息（后端对单文件也返回 FileInfo）
      const files = await invoke<FileInfo[]>('walk_directory', { path: p, recursive: false })
      if (files.length > 0) {
        store.addFileItem(files[0])
        store.addLog(`已添加文件: ${p}`)
      }
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    store.addLog(`添加文件失败: ${msg}`)
    alert('添加文件失败: ' + msg)
  }
}

// ---- 移除选中 ----
function removeSelected() {
  if (store.getSelectedPaths().length === 0) {
    store.addLog('没有选中任何文件')
    return
  }
  const count = store.getSelectedPaths().length
  store.removeSelected()
  store.addLog(`已移除 ${count} 项`)
}

// ---- 清空 ----
function clearAll() {
  if (store.fileItems.length === 0) {
    store.addLog('文件列表已为空')
    return
  }
  const count = store.fileItems.length
  store.clearAll()
  store.addLog(`已清空文件列表（共移除 ${count} 项）`)
}

// ---- 全选 / 取消全选 ----
function toggleSelectAll() {
  if (store.getSelectedPaths().length === store.fileItems.length && store.fileItems.length > 0) {
    store.clearSelection()
  } else {
    store.selectAll()
  }
}

// ---- 格式化大小 ----
function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

// ---- 格式化时间 ----
function formatTime(timestamp: number | null): string {
  if (timestamp === null || timestamp === undefined) return '-'
  const d = new Date(timestamp * 1000)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

const totalCount = computed(() => store.fileItems.length)
const selectedCount = computed(() => store.getSelectedPaths().length)
const isAllSelected = computed(() => {
  return store.fileItems.length > 0 && store.getSelectedPaths().length === store.fileItems.length
})
</script>

<template>
  <div class="file-list-container">
    <!-- 工具栏 -->
    <div class="toolbar">
      <button class="btn btn-primary" @click="addFolder" title="添加文件夹">
        📁 添加文件夹
      </button>
      <button class="btn btn-primary" @click="addFile" title="添加文件">
        📄 添加文件
      </button>
      <button class="btn btn-danger" @click="removeSelected" :disabled="selectedCount === 0" title="移除选中">
        ✕ 移除选中 ({{ selectedCount }})
      </button>
      <button class="btn btn-danger" @click="clearAll" :disabled="totalCount === 0" title="清空全部">
        🗑 清空
      </button>
      <button class="btn" @click="toggleSelectAll">
        {{ isAllSelected ? '☐ 取消全选' : '☑ 全选' }}
      </button>
      <span class="ml-auto text-muted text-sm">共 {{ totalCount }} 项</span>
    </div>

    <!-- 文件表格 -->
    <div class="file-table-wrapper" ref="tableWrapper">
      <table class="file-table">
        <thead>
          <tr>
            <th class="col-check"><input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll"></th>
            <th class="col-name">文件名</th>
            <th class="col-size">大小</th>
            <th class="col-mtime">修改时间</th>
            <th class="col-owner">所有者</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="file in store.fileItems"
            :key="file.path"
            :class="{ selected: store.isPathSelected(file.path) }"
            @click="store.toggleSelect(file.path)"
          >
            <td class="col-check">
              <input
                type="checkbox"
                :checked="store.isPathSelected(file.path)"
                @click.stop="store.toggleSelect(file.path)"
              >
            </td>
            <td class="col-name">
              <span class="file-icon">{{ file.is_dir ? '📁' : '📄' }}</span>
              <span class="file-name" :title="file.path">{{ file.name }}</span>
            </td>
            <td class="col-size text-muted">{{ formatSize(file.size) }}</td>
            <td class="col-mtime text-sm text-muted">
              {{ formatTime(file.last_write_time) }}
            </td>
            <td class="col-owner text-sm text-muted">{{ file.owner || '-' }}</td>
          </tr>
          <tr v-if="store.fileItems.length === 0">
            <td colspan="5" class="empty-hint">
              暂无文件，请添加文件夹或文件
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.file-list-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 500px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: var(--bg-header);
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}

.ml-auto {
  margin-left: auto;
}

.file-table-wrapper {
  flex: 1;
  overflow-x: auto;
  overflow-y: auto;
}

.file-table {
  width: 100%;
  min-width: 420px;
}

.file-table .col-check {
  width: 36px;
  text-align: center;
}

.file-table .col-name {
  min-width: 180px;
}

.file-table .col-size {
  width: 80px;
  text-align: right;
}

.file-table .col-mtime {
  min-width: 160px;
}

.file-table .col-owner {
  min-width: 100px;
}

.file-icon {
  margin-right: 4px;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-hint {
  text-align: center;
  color: var(--text-muted);
  padding: 40px;
  font-style: italic;
}

tbody tr {
  cursor: pointer;
}

tbody tr:hover {
  background: var(--highlight);
}

tbody tr.selected {
  background: var(--selected-bg);
}
</style>
