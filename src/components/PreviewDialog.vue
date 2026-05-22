<script setup lang="ts">
import { useAppStore } from '@/stores/appStore'
import { computed } from 'vue'

const store = useAppStore()

const changes = computed(() => store.previewChanges)
const totalChanges = computed(() => store.previewChanges.length)

function handleClose() {
  store.closePreview()
}
</script>

<template>
  <div class="modal-overlay" v-if="store.showPreview">
    <div class="modal-content" style="min-width: 500px">
      <div class="modal-header">
        <h3>预览修改</h3>
        <button class="modal-close" @click="handleClose">×</button>
      </div>

      <div v-if="totalChanges === 0" class="empty-message">
        没有发现需要修改的属性
      </div>

      <div v-else>
        <div class="changes-summary">
          共发现 <strong>{{ totalChanges }}</strong> 个待修改属性
        </div>

        <div class="changes-scroll">
          <table class="preview-table">
            <thead>
              <tr>
                <th class="col-path">文件路径</th>
                <th class="col-attr">属性</th>
                <th class="col-old">修改前</th>
                <th class="col-new">修改后</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(change, idx) in changes" :key="idx">
                <td class="col-path" :title="change.path">{{ change.path.split(/[\\/]/).pop() }}</td>
                <td class="col-attr">{{ change.attribute }}</td>
                <td class="col-old old-value">{{ change.old_value }}</td>
                <td class="col-new new-value">{{ change.new_value }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn" @click="handleClose">取消</button>
        <button class="btn btn-success" @click="executeChanges(true); handleClose()">确认执行</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-message {
  text-align: center;
  color: var(--text-muted);
  padding: 24px;
  font-style: italic;
}

.changes-summary {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.changes-scroll {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
}

.preview-table {
  width: 100%;
  font-size: 12px;
}

.preview-table .col-path {
  min-width: 150px;
  font-family: var(--font-mono);
  font-size: 11px;
}

.preview-table .col-attr {
  width: 80px;
}

.preview-table .col-old {
  width: 160px;
  color: var(--accent-red);
}

.preview-table .col-new {
  width: 160px;
  color: var(--accent-green);
  font-weight: 600;
}

.old-value {
  text-decoration: line-through;
}

.new-value {
  font-weight: 600;
}
</style>
