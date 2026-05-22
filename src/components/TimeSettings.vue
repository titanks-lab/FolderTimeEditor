<script setup lang="ts">
import { useAppStore } from '@/stores/appStore'
import type { FileTimes, PreviewChange } from '@/types'
import { invoke } from '@tauri-apps/api/core'

const store = useAppStore()
const { settings } = store

// 构建时间戳
function buildTimestamp(ts: { date: string; time: string }): number | null {
  if (!ts.date) return null
  const time = ts.time || '00:00'
  const [y, m, d] = ts.date.split('-').map(Number)
  const [h, min] = time.split(':').map(Number)
  return Math.floor(Date.UTC(y, m - 1, d, h, min) / 1000)
}

function formatTimestamp(ts: number | null): string {
  if (ts === null || ts === undefined) return '未设置'
  return new Date(ts * 1000).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  })
}

// 预览修改
async function previewChanges() {
  const paths = store.getSelectedPaths()
  if (paths.length === 0) {
    store.addLog('请先选中要修改的文件')
    return
  }

  const changes: PreviewChange[] = []

  for (const path of paths) {
    try {
      const _currentTimes = await invoke<FileTimes>('get_file_times', { path })

      if (settings.creation.enabled) {
        const newVal = buildTimestamp(settings.creation)
        if (newVal !== _currentTimes.creation_time) {
          changes.push({ path, attribute: '创建时间', old_value: formatTimestamp(_currentTimes.creation_time), new_value: formatTimestamp(newVal) })
        }
      }
      if (settings.modification.enabled) {
        const newVal = buildTimestamp(settings.modification)
        if (newVal !== _currentTimes.last_write_time) {
          changes.push({ path, attribute: '修改时间', old_value: formatTimestamp(_currentTimes.last_write_time), new_value: formatTimestamp(newVal) })
        }
      }
      if (settings.access.enabled) {
        const newVal = buildTimestamp(settings.access)
        if (newVal !== _currentTimes.last_access_time) {
          changes.push({ path, attribute: '访问时间', old_value: formatTimestamp(_currentTimes.last_access_time), new_value: formatTimestamp(newVal) })
        }
      }
      if (settings.owner_enabled && settings.owner) {
        const _currentOwner = store.fileItems.find(f => f.path === path)?.owner || ''
        if (_currentOwner !== settings.owner) {
          changes.push({ path, attribute: '所有者', old_value: _currentOwner || '(未知)', new_value: settings.owner })
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      changes.push({ path, attribute: '错误', old_value: '-', new_value: `读取失败: ${msg}` })
    }
  }

  store.setPreview(changes)
}

// 执行修改
async function executeChanges(selectedOnly: boolean = true) {
  const paths = selectedOnly ? store.getSelectedPaths() : store.fileItems.map(f => f.path)
  if (paths.length === 0) {
    store.addLog(selectedOnly ? '请先选中要修改的文件' : '文件列表为空')
    return
  }

  store.addLog(`开始执行修改... (${paths.length} 个文件)`)
  const total = paths.length
  store.setProgress(0, total)

  let success = 0
  let failed = 0

  for (let i = 0; i < paths.length; i++) {
    const path = paths[i]
    try {
      if (selectedOnly) {
        // 读取当前时间，只覆盖启用的
        await invoke<FileTimes>('get_file_times', { path })
        await invoke('set_file_times', {
          path,
          times: {
            creation_time: settings.creation.enabled ? buildTimestamp(settings.creation) : null,
            last_write_time: settings.modification.enabled ? buildTimestamp(settings.modification) : null,
            last_access_time: settings.access.enabled ? buildTimestamp(settings.access) : null,
          },
        })
      } else {
        // 应用到全部
        await invoke<FileTimes>('get_file_times', { path })
        await invoke('set_file_times', {
          path,
          times: {
            creation_time: settings.creation.enabled ? buildTimestamp(settings.creation) : null,
            last_write_time: settings.modification.enabled ? buildTimestamp(settings.modification) : null,
            last_access_time: settings.access.enabled ? buildTimestamp(settings.access) : null,
          },
        })
      }

      if (settings.owner_enabled && settings.owner) {
        await invoke('set_file_owner', { path, owner: settings.owner })
      }

      success++
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      failed++
      store.addLog(`✕ ${path}: ${msg}`)
    }

    store.setProgress(i + 1, total)
  }

  store.addLog(`执行完成！成功: ${success}, 失败: ${failed}`)
}

async function applyToSelected() {
  await executeChanges(true)
}

async function applyToAll() {
  store.selectAll()
  await executeChanges(false)
}

async function undo() {
  store.addLog('撤销功能：当前版本暂未实现文件时间回滚')
}

function saveProfile() {
  const name = prompt('请输入方案名称：')
  if (!name) return

  store.addProfile(name, settings)
  store.addLog(`已保存方案: ${name}`)
}

function loadProfile(index: number) {
  const profile = store.profiles[index]
  if (!profile) return

  settings.creation = { ...profile.settings.creation }
  settings.modification = { ...profile.settings.modification }
  settings.access = { ...profile.settings.access }
  settings.sync = profile.settings.sync
  settings.owner_enabled = profile.settings.owner_enabled
  settings.owner = profile.settings.owner

  store.addLog(`已加载方案: ${profile.name}`)
}
</script>

<template>
  <div class="time-settings">
    <!-- 同步选项 -->
    <div class="section mb-4">
      <label class="setting-row">
        <input type="checkbox" v-model="settings.sync">
        <span>同步所有时间</span>
      </label>
    </div>

    <!-- 创建时间 -->
    <div class="section mb-4">
      <label class="setting-row">
        <input type="checkbox" v-model="settings.creation.enabled">
        <span>创建时间</span>
      </label>
      <div class="time-inputs" :class="{ disabled: !settings.creation.enabled }">
        <input type="date" v-model="settings.creation.date" :disabled="!settings.creation.enabled">
        <input type="time" v-model="settings.creation.time" :disabled="!settings.creation.enabled">
      </div>
    </div>

    <!-- 修改时间 -->
    <div class="section mb-4">
      <label class="setting-row">
        <input type="checkbox" v-model="settings.modification.enabled">
        <span>修改时间</span>
      </label>
      <div class="time-inputs" :class="{ disabled: !settings.modification.enabled }">
        <input type="date" v-model="settings.modification.date" :disabled="!settings.modification.enabled">
        <input type="time" v-model="settings.modification.time" :disabled="!settings.modification.enabled">
      </div>
    </div>

    <!-- 访问时间 -->
    <div class="section mb-4">
      <label class="setting-row">
        <input type="checkbox" v-model="settings.access.enabled">
        <span>访问时间</span>
      </label>
      <div class="time-inputs" :class="{ disabled: !settings.access.enabled }">
        <input type="date" v-model="settings.access.date" :disabled="!settings.access.enabled">
        <input type="time" v-model="settings.access.time" :disabled="!settings.access.enabled">
      </div>
    </div>

    <!-- 所有者 -->
    <div class="section mb-4">
      <label class="setting-row">
        <input type="checkbox" v-model="settings.owner_enabled">
        <span>所有者</span>
      </label>
      <div class="owner-input" :class="{ disabled: !settings.owner_enabled }">
        <input type="text" v-model="settings.owner" placeholder="请输入 SID (如 S-1-5-...)" :disabled="!settings.owner_enabled" class="input" style="flex:1">
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-buttons">
      <button class="btn btn-primary" @click="applyToSelected" :disabled="store.getSelectedPaths().length === 0">
        应用到选中 ({{ store.getSelectedPaths().length }})
      </button>
      <button class="btn btn-success" @click="applyToAll" :disabled="store.fileItems.length === 0">
        应用到全部
      </button>
    </div>

    <div class="action-buttons mt-2">
      <button class="btn btn-warning" @click="previewChanges">
        👁 预览修改
      </button>
      <button class="btn btn-success" @click="executeChanges(true)" :disabled="store.getSelectedPaths().length === 0">
        ▶ 执行修改
      </button>
      <button class="btn" @click="undo">
        ↩ 撤销
      </button>
    </div>

    <div class="action-buttons mt-2">
      <button class="btn" @click="saveProfile">
        💾 保存方案
      </button>
      <select v-if="store.profiles.length > 0" class="input" style="flex:1; min-width:120px" @change="loadProfile(Number(($event.target as HTMLSelectElement).value))">
        <option value="">- 加载方案 -</option>
        <option v-for="(p, i) in store.profiles" :key="i" :value="i">{{ p.name }}</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.time-settings {
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  overflow-y: auto;
  height: 100%;
}

.section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
}

.setting-row {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 500;
}

.time-inputs {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.time-inputs.disabled,
.owner-input.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.owner-input {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
