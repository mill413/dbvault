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

    <el-dialog v-model="restoreDialogVisible" title="恢复备份" width="600px">
      <el-form :model="restoreForm" :rules="restoreRules" ref="restoreFormRef" label-width="120px">
        <el-form-item label="选择备份" prop="backup_id">
          <el-select v-model="restoreForm.backup_id" filterable placeholder="请选择备份" style="width: 100%">
            <el-option
              v-for="backup in backups"
              :key="backup.id"
              :label="`#${backup.id} - ${getDatabaseName(backup.database_id)} (${backup.status})`"
              :value="backup.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="目标数据库" prop="target_database_id" v-if="restoreForm.restore_mode === 'NEW_INSTANCE'">
          <el-select v-model="restoreForm.target_database_id" filterable placeholder="请先选择备份" :disabled="!restoreForm.backup_id" style="width: 100%">
            <el-option
              v-for="db in availableTargetDatabases"
              :key="db.id"
              :label="`${db.name} (${db.db_type}: ${db.host}:${db.port})`"
              :value="db.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="目标数据库" v-if="restoreForm.restore_mode === 'ORIGINAL_INSTANCE'">
          <el-input :value="sourceDatabaseDisplay" disabled />
        </el-form-item>
        <el-form-item label="恢复模式" prop="restore_mode">
          <el-select v-model="restoreForm.restore_mode" style="width: 100%" @change="onRestoreModeChange">
            <el-option label="恢复到新实例" value="NEW_INSTANCE" />
            <el-option label="原实例恢复" value="ORIGINAL_INSTANCE" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="dryRunResult">
          <el-alert
            :title="dryRunResult.ok ? '预检查通过' : '预检查未通过'"
            :type="dryRunResult.ok ? 'success' : 'error'"
            :description="dryRunResult.message"
            show-icon
            :closable="false"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="restoreDialogVisible = false">取消</el-button>
        <el-button @click="handleDryRun" :loading="dryRunLoading">预检查</el-button>
        <el-button type="primary" @click="handleRestore" :loading="restoreLoading">开始恢复</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="confirmDialogVisible" title="确认恢复" width="500px">
      <el-alert
        title="高风险操作"
        description="您正在执行原实例恢复操作，这将覆盖目标数据库的所有数据。"
        type="error"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      />
      <p style="margin-bottom: 10px">请输入 <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 4px">{{ currentTask?.confirm_required }}</code> 以确认：</p>
      <el-input v-model="confirmText" placeholder="输入确认文本" />
      <template #footer>
        <el-button @click="confirmDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="submitRestore" :loading="restoreLoading" :disabled="confirmText !== currentTask?.confirm_required">确认恢复</el-button>
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getRestoreTasks, runRestore, getRestoreTaskEvents, dryRunRestore } from '../api/restores'
import { getDatabases } from '../api/databases'
import { getBackups } from '../api/backups'

const restoreTasks = ref([])
const databases = ref([])
const backups = ref([])
const loading = ref(false)
const restoreLoading = ref(false)
const dryRunLoading = ref(false)
const restoreDialogVisible = ref(false)
const confirmDialogVisible = ref(false)
const dryRunResult = ref(null)
const eventsDialogVisible = ref(false)
const restoreFormRef = ref(null)
const currentTask = ref(null)
const events = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const confirmText = ref('')

const restoreForm = reactive({
  backup_id: null,
  target_database_id: null,
  restore_mode: 'NEW_INSTANCE',
  dry_run: false,
})

const restoreRules = {
  backup_id: [{ required: true, message: '请选择备份', trigger: 'change' }],
  restore_mode: [{ required: true, message: '请选择恢复模式', trigger: 'change' }],
}

const getStatusType = (status) => {
  const map = { COMPLETED: 'success', RUNNING: 'warning', FAILED: 'danger', PENDING: 'info', CANCELLED: 'info' }
  return map[status] || 'info'
}

const getDatabaseName = (id) => {
  if (!id) return '未知数据库'
  const db = databases.value.find((d) => d.id === id)
  return db ? db.name : `数据库ID: ${id}`
}

const getSelectedBackup = () => {
  if (!restoreForm.backup_id) return null
  return backups.value.find((b) => b.id === restoreForm.backup_id)
}

const sourceDatabaseDisplay = computed(() => {
  const backup = getSelectedBackup()
  if (!backup) return '请先选择备份'
  const db = databases.value.find((d) => d.id === backup.database_id)
  return db ? `${db.name} (${db.db_type}: ${db.host}:${db.port})` : `数据库ID: ${backup.database_id}`
})

const availableTargetDatabases = computed(() => {
  const backup = getSelectedBackup()
  if (!backup) return databases.value
  return databases.value.filter((d) => d.id !== backup.database_id)
})

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
    const backupRes = await getBackups({ page_size: 100 })
    backups.value = backupRes.data.items || []
  } catch (error) {
    console.error('Failed to fetch dependencies:', error)
  }
}

const showRestoreDialog = () => {
  restoreForm.backup_id = null
  restoreForm.target_database_id = null
  restoreForm.restore_mode = 'NEW_INSTANCE'
  restoreForm.dry_run = false
  dryRunResult.value = null
  restoreDialogVisible.value = true
}

const onRestoreModeChange = () => {
  if (restoreForm.restore_mode === 'ORIGINAL_INSTANCE') {
    const backup = getSelectedBackup()
    if (backup) {
      restoreForm.target_database_id = backup.database_id
    }
  } else {
    restoreForm.target_database_id = null
  }
}

const validateRestoreMode = () => {
  const backup = getSelectedBackup()
  if (!backup || !restoreForm.target_database_id) return true

  const sourceDbId = backup.database_id
  const targetDbId = restoreForm.target_database_id

  if (restoreForm.restore_mode === 'NEW_INSTANCE' && sourceDbId === targetDbId) {
    ElMessage.warning('恢复到新实例模式下，目标数据库应与备份来源数据库不同')
    return false
  }

  if (restoreForm.restore_mode === 'ORIGINAL_INSTANCE' && sourceDbId !== targetDbId) {
    ElMessage.warning('原实例恢复模式下，目标数据库必须与备份来源数据库相同')
    return false
  }

  return true
}

const handleDryRun = async () => {
  const valid = await restoreFormRef.value.validate().catch(() => false)
  if (!valid) return

  if (!validateRestoreMode()) return

  dryRunLoading.value = true
  try {
    const response = await dryRunRestore({
      backup_id: restoreForm.backup_id,
      target_database_id: restoreForm.target_database_id,
    })
    dryRunResult.value = response.data
    if (response.data.ok) {
      ElMessage.success('预检查通过，可以执行恢复')
    } else {
      ElMessage.warning('预检查未通过，请检查错误信息')
    }
  } catch (error) {
    console.error('Dry run failed:', error)
  } finally {
    dryRunLoading.value = false
  }
}

const handleRestore = async () => {
  const valid = await restoreFormRef.value.validate().catch(() => false)
  if (!valid) return

  if (!validateRestoreMode()) return

  if (restoreForm.restore_mode === 'ORIGINAL_INSTANCE') {
    const backup = getSelectedBackup()
    const sourceDb = databases.value.find((d) => d.id === backup?.database_id)
    if (sourceDb) {
      confirmText.value = ''
      currentTask.value = { target_name: sourceDb.name, confirm_required: `restore ${sourceDb.name}` }
      confirmDialogVisible.value = true
      return
    }
  }

  submitRestore()
}

const submitRestore = async () => {
  restoreLoading.value = true
  try {
    const payload = {
      backup_id: restoreForm.backup_id,
      target_database_id: restoreForm.target_database_id,
      restore_mode: restoreForm.restore_mode,
      dry_run: restoreForm.dry_run,
    }
    if (restoreForm.restore_mode === 'ORIGINAL_INSTANCE' && currentTask.value?.confirm_required) {
      payload.confirm_text = confirmText.value
    }
    await runRestore(payload)
    ElMessage.success('恢复任务已提交')
    restoreDialogVisible.value = false
    confirmDialogVisible.value = false
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
