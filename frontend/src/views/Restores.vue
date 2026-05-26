<template>
  <div class="restores">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>恢复管理</span>
          <el-button type="primary" @click="showRestoreDialog">
            <el-icon><Download /></el-icon>
            恢复备份
          </el-button>
        </div>
      </template>

      <el-table :data="restoreTasks" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="任务ID" width="80" />
        <el-table-column prop="backup_id" label="备份ID" width="100" />
        <el-table-column label="目标数据库" width="150">
          <template #default="{ row }">
            {{ getDatabaseName(row.target_database_id) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="restore_mode" label="恢复模式" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phase" label="阶段" width="100" />
        <el-table-column prop="progress" label="进度" width="100">
          <template #default="{ row }">
            {{ row.progress }}%
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
        <el-table-column prop="duration_seconds" label="耗时(秒)" width="100">
          <template #default="{ row }">
            {{ row.duration_seconds ? row.duration_seconds.toFixed(1) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEvents(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="fetchData"
        @size-change="fetchData"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <el-dialog v-model="restoreDialogVisible" title="恢复备份" width="500px">
      <el-form :model="restoreForm" :rules="restoreRules" ref="restoreFormRef" label-width="120px">
        <el-form-item label="备份ID" prop="backup_id">
          <el-input-number v-model="restoreForm.backup_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="目标数据库ID">
          <el-input-number v-model="restoreForm.target_database_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="恢复模式" prop="restore_mode">
          <el-select v-model="restoreForm.restore_mode" style="width: 100%">
            <el-option label="新建实例" value="NEW_INSTANCE" />
            <el-option label="覆盖现有" value="OVERWRITE" />
          </el-select>
        </el-form-item>
        <el-form-item label="预检">
          <el-switch v-model="restoreForm.dry_run" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px">仅检查不执行恢复</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="restoreDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRestore" :loading="restoreLoading">开始恢复</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="eventsDialogVisible" title="任务详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务ID">{{ currentTask?.id }}</el-descriptions-item>
        <el-descriptions-item label="备份ID">{{ currentTask?.backup_id }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ currentTask?.status }}</el-descriptions-item>
        <el-descriptions-item label="阶段">{{ currentTask?.phase }}</el-descriptions-item>
        <el-descriptions-item label="进度">{{ currentTask?.progress }}%</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ currentTask?.duration_seconds ? currentTask.duration_seconds.toFixed(1) + 's' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="错误信息" :span="2">{{ currentTask?.error_message || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 20px">
        <h4>执行日志</h4>
        <el-table :data="events" style="width: 100%" max-height="300">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="event_type" label="事件类型" width="120" />
          <el-table-column prop="message" label="消息" min-width="200" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="180" />
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getRestoreTasks, runRestore, getRestoreTaskEvents } from '../api/restores'
import { getDatabases } from '../api/databases'

const restoreTasks = ref([])
const databases = ref([])
const loading = ref(false)
const restoreLoading = ref(false)
const restoreDialogVisible = ref(false)
const eventsDialogVisible = ref(false)
const restoreFormRef = ref(null)
const currentTask = ref(null)
const events = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const restoreForm = reactive({
  backup_id: null,
  target_database_id: null,
  restore_mode: 'NEW_INSTANCE',
  dry_run: false,
})

const restoreRules = {
  backup_id: [{ required: true, message: '请输入备份ID', trigger: 'blur' }],
  restore_mode: [{ required: true, message: '请选择恢复模式', trigger: 'change' }],
}

const getStatusType = (status) => {
  const map = { COMPLETED: 'success', RUNNING: 'warning', FAILED: 'danger', PENDING: 'info', CANCELLED: 'info' }
  return map[status] || 'info'
}

const getDatabaseName = (id) => {
  if (!id) return null
  const db = databases.value.find((d) => d.id === id)
  return db ? db.name : null
}

const fetchData = async () => {
  loading.value = true
  try {
    const response = await getRestoreTasks({ page: page.value, page_size: pageSize.value })
    restoreTasks.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error) {
    console.error('Failed to fetch restore tasks:', error)
  } finally {
    loading.value = false
  }
}

const fetchDependencies = async () => {
  try {
    const dbRes = await getDatabases({ page_size: 100 })
    databases.value = dbRes.data.items || []
  } catch (error) {
    console.error('Failed to fetch dependencies:', error)
  }
}

const showRestoreDialog = () => {
  restoreDialogVisible.value = true
}

const handleRestore = async () => {
  const valid = await restoreFormRef.value.validate().catch(() => false)
  if (!valid) return

  restoreLoading.value = true
  try {
    await runRestore({
      backup_id: restoreForm.backup_id,
      target_database_id: restoreForm.target_database_id,
      restore_mode: restoreForm.restore_mode,
      dry_run: restoreForm.dry_run,
    })
    ElMessage.success('恢复任务已提交')
    restoreDialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Failed to run restore:', error)
  } finally {
    restoreLoading.value = false
  }
}

const showEvents = async (row) => {
  currentTask.value = row
  events.value = []
  eventsDialogVisible.value = true
  try {
    const response = await getRestoreTaskEvents(row.id)
    events.value = response.data || []
  } catch (error) {
    console.error('Failed to fetch events:', error)
  }
}

onMounted(() => {
  fetchData()
  fetchDependencies()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
</style>
