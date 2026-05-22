<script setup lang="ts">
import { useAppStore } from '@/stores/appStore'

const store = useAppStore()

function removeProfile(index: number) {
  const name = store.profiles[index]?.name
  store.removeProfile(index)
  store.addLog(`已删除方案: ${name}`)
}

function saveCurrentProfile() {
  const name = prompt('请输入方案名称：')
  if (!name) return
  store.addProfile(name, store.settings)
  store.addLog(`已保存方案: ${name}`)
}
</script>

<template>
  <div class="modal-overlay" v-if="store.profiles.length > 0">
    <div class="modal-content" style="min-width: 350px">
      <div class="modal-header">
        <h3>方案管理</h3>
        <button class="modal-close" @click="store.clearProfiles()">×</button>
      </div>

      <div class="profile-list">
        <div v-for="(profile, index) in store.profiles" :key="index" class="profile-item">
          <span class="profile-name">{{ profile.name }}</span>
          <div class="profile-actions">
            <button class="btn btn-sm btn-primary" @click="store.loadProfile(index)">加载</button>
            <button class="btn btn-sm btn-danger" @click="removeProfile(index)">删除</button>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-primary" @click="saveCurrentProfile">💾 保存当前方案</button>
        <button class="btn" @click="store.clearProfiles()">清空所有方案</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-list {
  max-height: 250px;
  overflow-y: auto;
}

.profile-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-light);
}

.profile-item:last-child {
  border-bottom: none;
}

.profile-name {
  font-weight: 500;
  font-size: 13px;
}

.profile-actions {
  display: flex;
  gap: 4px;
}
</style>
