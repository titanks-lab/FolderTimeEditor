import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import type { FileInfo, AppSettings, PreviewChange } from '@/types'

// 默认时间设置
function defaultTimeSetting(): AppSettings {
  const now = new Date()
  const dateStr = now.toISOString().split('T')[0]
  const timeStr = now.toTimeString().slice(0, 5)
  return {
    creation: { enabled: false, date: dateStr, time: timeStr },
    modification: { enabled: false, date: dateStr, time: timeStr },
    access: { enabled: false, date: dateStr, time: timeStr },
    sync: false,
    owner_enabled: false,
    owner: '',
  }
}

export const useAppStore = defineStore('app', () => {
  // ---- 文件列表 ----
  const fileItems = reactive<FileInfo[]>([])
  const selectedPaths = ref<Set<string>>(new Set())

  function addFileItem(item: FileInfo) {
    fileItems.push(item)
  }

  function addFiles(items: FileInfo[]) {
    fileItems.push(...items)
  }

  function removeSelected() {
    const toRemove = getSelectedPaths()
    for (let i = fileItems.length - 1; i >= 0; i--) {
      if (toRemove.includes(fileItems[i].path)) {
        fileItems.splice(i, 1)
      }
    }
    selectedPaths.value.clear()
  }

  function clearAll() {
    fileItems.length = 0
    selectedPaths.value.clear()
  }

  function toggleSelect(path: string) {
    if (selectedPaths.value.has(path)) {
      selectedPaths.value.delete(path)
    } else {
      selectedPaths.value.add(path)
    }
  }

  function selectAll() {
    selectedPaths.value.clear()
    for (const item of fileItems) {
      selectedPaths.value.add(item.path)
    }
  }

  function clearSelection() {
    selectedPaths.value.clear()
  }

  function isPathSelected(path: string): boolean {
    return selectedPaths.value.has(path)
  }

  function getSelectedPaths(): string[] {
    return Array.from(selectedPaths.value)
  }

  function getSelectedItem(): FileInfo | undefined {
    const path = getSelectedPaths()[0]
    return fileItems.find((f) => f.path === path)
  }

  // ---- 应用设置 ----
  const settings = reactive<AppSettings>(defaultTimeSetting())

  // ---- 操作日志 ----
  const logMessages = ref<string[]>([])
  const progressBar = ref<{ current: number; total: number }>({ current: 0, total: 0 })
  const successCount = ref(0)
  const failCount = ref(0)

  function addLog(message: string) {
    const now = new Date()
    const time = now.toTimeString().slice(0, 8)
    logMessages.value.push(`[${time}] ${message}`)
  }

  function clearLog() {
    logMessages.value = []
    successCount.value = 0
    failCount.value = 0
  }

  function setProgress(current: number, total: number) {
    progressBar.value = { current, total }
  }

  function incrementSuccess() {
    successCount.value++
  }

  function incrementFail() {
    failCount.value++
  }

  // ---- 预览 ----
  const previewChanges = ref<PreviewChange[]>([])
  const showPreview = ref(false)

  function setPreview(changes: PreviewChange[]) {
    previewChanges.value = changes
    showPreview.value = true
  }

  function closePreview() {
    showPreview.value = false
  }

  // ---- 方案（profile）----
  const profiles = ref<{ name: string; settings: AppSettings }[]>([])

  function addProfile(name: string, s: AppSettings) {
    profiles.value.push({
      name,
      settings: {
        creation: { ...s.creation },
        modification: { ...s.modification },
        access: { ...s.access },
        sync: s.sync,
        owner_enabled: s.owner_enabled,
        owner: s.owner,
      },
    })
  }

  function removeProfile(index: number) {
    profiles.value.splice(index, 1)
  }

  function loadProfile(index: number) {
    const profile = profiles.value[index]
    if (!profile) return

    settings.creation = { ...profile.settings.creation }
    settings.modification = { ...profile.settings.modification }
    settings.access = { ...profile.settings.access }
    settings.sync = profile.settings.sync
    settings.owner_enabled = profile.settings.owner_enabled
    settings.owner = profile.settings.owner
  }

  function clearProfiles() {
    profiles.value = []
  }

  return {
    // 文件列表
    fileItems,
    selectedPaths,
    addFileItem,
    addFiles,
    removeSelected,
    clearAll,
    toggleSelect,
    selectAll,
    clearSelection,
    isPathSelected,
    getSelectedPaths,
    getSelectedItem,
    // 设置
    settings,
    // 日志
    logMessages,
    progressBar,
    successCount,
    failCount,
    addLog,
    clearLog,
    setProgress,
    incrementSuccess,
    incrementFail,
    // 预览
    previewChanges,
    showPreview,
    setPreview,
    closePreview,
    // 方案
    profiles,
    addProfile,
    removeProfile,
    loadProfile,
    clearProfiles,
  }
})
