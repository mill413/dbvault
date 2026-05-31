<template>
  <div class="restores">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('restore.title') }}</span>
          <div class="header-filters">
            <el-select v-model="filterStatus" :placeholder="$t('restore.statusFilter')" clearable style="width: 140px" @change="fetchData">
              <el-option label="完成" value="COMPLETED" />
              <el-option label="运行中" value="RUNNING" />
              <el-option label="失败" value="FAILED" />
              <el-option label="待处理" value="PENDING" />
              <el-option label="已取消" value="CANCELLED" />
            </el-select>
            <el-button type="primary" @click="showRestoreDialog">
              <el-icon><Download /></el-icon>
              Restore Backup
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="restoreTasks" v-loading="loading" style="width: 100%" size="default" empty-text="No data available">
        <el-table-column prop="id" :label="$t('restore.taskId')" width="80" />
        <el-table-column prop="backup_id" :label="$t('restore.backupId')" width="100" />
        <el-table-column :label="$t('restore.targetDb')" width="150">
          <template #default="{ row }">
            {{ getDatabaseName(row.target_database_id) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="restore_mode" :label="$t('restore.restoreMode')" width="120" />
        <el-table-column prop="status" :label="$t('common.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phase" :label="$t('restore.phase')" width="100" />
        <el-table-column prop="progress" :label="$t('restore.progress')" width="100">
          <template #default="{ row }">
            {{ row.progress }}%
          </template>
        </el-table-column>
        <el-table-column prop="error_message" :label="$t('restore.errorMsg')" min-width="200" show-overflow-tooltip />
        <el-table-column prop="duration_seconds" :label="$t('restore.duration')" width="100">
          <template #default="{ row }">
            {{ row.duration_seconds ? row.duration_seconds.toFixed(1) : '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.createTime')" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEvents(row)">{{ $t('common.details') }}</el-button>
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

    <el-dialog v-model="restoreDialogVisible" :title="$t('restore.restoreBackup')" width="600px">
      <el-form :model="restoreForm" :rules="restoreRules" ref="restoreFormRef" label-width="120px">
        <el-form-item :label="$t('restore.restoreBackup')" prop="backup_id">
          <el-select v-model="restoreForm.backup_id" filterable placeholder="请选择备份" style="width: 100%">
            <el-option
              v-for="backup in backups"
              :key="backup.id"
              :label="`#${backup.id} - ${getDatabaseName(backup.database_id)} (${backup.status})`"
              :value="backup.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('restore.targetDb')" prop="target_database_id" v-if="restoreForm.restore_mode === 'NEW_INSTANCE'">
          <el-select v-model="restoreForm.target_database_id" filterable placeholder="请先选择备份" :disabled="!restoreForm.backup_id" style="width: 100%">
            <el-option
              v-for="db in availableTargetDatabases"
              :key="db.id"
              :label="`${db.name} (${db.db_type}: ${db.host}:${db.port})`"
              :value="db.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('restore.targetDb')" v-if="restoreForm.restore_mode === 'ORIGINAL_INSTANCE'">
          <el-input :value="sourceDatabaseDisplay" disabled />
        </el-form-item>
        <el-form-item :label="$t('restore.restoreMode')" prop="restore_mode">
          <el-select v-model="restoreForm.restore_mode" style="width: 100%" @change="onRestoreModeChange">
            <el-option label="恢复到新实例" value="NEW_INSTANCE" />
            <el-option label="原实例恢复" value="ORIGINAL_INSTANCE" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="dryRunResult">
          <el-alert
            :title="dryRunResult.ok ? t('restore.dryRunPass') : t('restore.dryRunFail')"
            :type="dryRunResult.ok ? 'success' : 'error'"
            :description="dryRunResult.message"
            show-icon
            :closable="false"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="restoreDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button @click="handleDryRun" :loading="dryRunLoading">{{ $t('restore.dryRun') }}</el-button>
        <el-button type="primary" @click="handleRestore" :loading="restoreLoading">{{ $t('restore.startRestore') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="confirmDialogVisible" :title="$t('restore.confirmRestore')" width="500px">
      <el-alert
        :title="$t('restore.highRisk')"
        :description="$t('restore.highRiskDesc')"
        type="error"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      />
      <p style="margin-bottom: 10px">{{ $t('restore.confirmPrompt', { text: currentTask?.confirm_required }) }}</p>
      <el-input v-model="confirmText" placeholder="输入确认文本" />
      <template #footer>
        <el-button @click="confirmDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="danger" @click="submitRestore" :loading="restoreLoading" :disabled="confirmText !== currentTask?.confirm_required">{{ $t('restore.confirmRestore') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="eventsDialogVisible" :title="$t('restore.taskDetails')" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item :label="$t('restore.taskId')">{{ currentTask?.id }}</el-descriptions-item>
        <el-descriptions-item :label="$t('restore.backupId')">{{ currentTask?.backup_id }}</el-descriptions-item>
        <el-descriptions-item :label="$t('common.status')">{{ currentTask?.status }}</el-descriptions-item>
        <el-descriptions-item :label="$t('restore.phase')">{{ currentTask?.phase }}</el-descriptions-item>
        <el-descriptions-item :label="$t('restore.progress')">{{ currentTask?.progress }}%</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ currentTask?.duration_seconds ? currentTask.duration_seconds.toFixed(1) + 's' : '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('restore.errorMsg')" :span="2">{{ currentTask?.error_message || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 20px">
        <h4>{{ $t('restore.logs') }}</h4>
        <el-table :data="events" style="width: 100%" max-height="300" size="default" empty-text="No data available">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="event_type" label="事件类型" width="120" />
          <el-table-column prop="message" :label="$t('alert.message')" min-width="200" show-overflow-tooltip />
          <el-table-column :label="$t('common.time')" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
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
const filterStatus = ref('')
const confirmText = ref('')
const { t } = useI18n()

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

const formatTime = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
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
    let items = response.data.items || []
    if (filterStatus.value) {
      items = items.filter((item) => item.status === filterStatus.value)
    }
    restoreTasks.value = items
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

.header-filters {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
