<template>
  <div class="jobs">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>定时任务列表</span>
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            新增任务
          </el-button>
        </div>
      </template>

      <el-table :data="jobs" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="任务名称" />
        <el-table-column label="数据库">
          <template #default="{ row }">
            {{ getDatabaseName(row.database_id) }}
          </template>
        </el-table-column>
        <el-table-column label="存储" width="120">
          <template #default="{ row }">
            {{ getStorageName(row.storage_id) }}
          </template>
        </el-table-column>
        <el-table-column prop="schedule_type" label="调度类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ getScheduleLabel(row.schedule_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cron_expr" label="Cron表达式" width="120" />
        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="handleToggle(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="last_status" label="上次执行" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.last_status" :type="getStatusType(row.last_status)" size="small">{{ row.last_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="next_run_at" label="下次执行" width="180">
          <template #default="{ row }">
            {{ row.next_run_at ? formatDate(row.next_run_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="showEditDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑任务' : '新增任务'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="数据库" prop="database_id">
          <el-select v-model="form.database_id" style="width: 100%" placeholder="选择数据库">
            <el-option v-for="db in databases" :key="db.id" :label="db.name" :value="db.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="存储" prop="storage_id">
          <el-select v-model="form.storage_id" style="width: 100%" placeholder="选择存储">
            <el-option v-for="s in storages" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="调度类型" prop="schedule_type">
          <el-select v-model="form.schedule_type" style="width: 100%">
            <el-option label="Cron" value="cron" />
            <el-option label="间隔" value="interval" />
            <el-option label="一次性" value="once" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.schedule_type === 'cron'" label="Cron表达式" prop="cron_expr">
          <el-input v-model="form.cron_expr" placeholder="0 2 * * *" />
        </el-form-item>
        <el-form-item v-if="form.schedule_type === 'interval'" label="间隔(秒)" prop="interval_seconds">
          <el-input-number v-model="form.interval_seconds" :min="60" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="form.schedule_type === 'once'" label="执行时间" prop="run_at">
          <el-date-picker v-model="form.run_at" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-form-item label="压缩方式">
          <el-select v-model="form.backup_config.compression" style="width: 100%">
            <el-option label="zstd" value="zstd" />
            <el-option label="gzip" value="gzip" />
          </el-select>
        </el-form-item>
        <el-form-item label="保留天数">
          <el-input-number v-model="form.retention_days" :min="1" :max="365" style="width: 100%" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getJobs, createJob, updateJob, deleteJob, enableJob, disableJob } from '../api/jobs'
import { getDatabases } from '../api/databases'
import { getStorages } from '../api/storages'

const jobs = ref([])
const databases = ref([])
const storages = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)

const form = reactive({
  name: '',
  database_id: null,
  storage_id: null,
  schedule_type: 'cron',
  cron_expr: '0 2 * * *',
  interval_seconds: 86400,
  run_at: null,
  enabled: true,
  backup_config: { compression: 'zstd' },
  retention_days: 30,
})

const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  database_id: [{ required: true, message: '请选择数据库', trigger: 'change' }],
  storage_id: [{ required: true, message: '请选择存储', trigger: 'change' }],
  schedule_type: [{ required: true, message: '请选择调度类型', trigger: 'change' }],
}

const getScheduleLabel = (type) => {
  const map = { cron: 'Cron', interval: '间隔', once: '一次性' }
  return map[type] || type
}

const getStatusType = (status) => {
  const map = { COMPLETED: 'success', RUNNING: 'warning', FAILED: 'danger', PENDING: 'info' }
  return map[status] || 'info'
}

const getDatabaseName = (id) => {
  const db = databases.value.find((d) => d.id === id)
  return db ? db.name : id
}

const getStorageName = (id) => {
  const storage = storages.value.find((s) => s.id === id)
  return storage ? storage.name : id
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const fetchData = async () => {
  loading.value = true
  try {
    const response = await getJobs({ page_size: 100 })
    jobs.value = response.data.items || []
  } catch (error) {
    console.error('Failed to fetch jobs:', error)
  } finally {
    loading.value = false
  }
}

const fetchDependencies = async () => {
  try {
    const [dbRes, storageRes] = await Promise.all([getDatabases({ page_size: 100 }), getStorages({ page_size: 100 })])
    databases.value = dbRes.data.items || []
    storages.value = storageRes.data.items || []
  } catch (error) {
    console.error('Failed to fetch dependencies:', error)
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  editId.value = null
  Object.assign(form, {
    name: '',
    database_id: null,
    storage_id: null,
    schedule_type: 'cron',
    cron_expr: '0 2 * * *',
    interval_seconds: 86400,
    run_at: null,
    enabled: true,
    backup_config: { compression: 'zstd' },
    retention_days: 30,
  })
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    name: row.name,
    database_id: row.database_id,
    storage_id: row.storage_id,
    schedule_type: row.schedule_type,
    cron_expr: row.cron_expr || '',
    interval_seconds: row.interval_seconds || 86400,
    run_at: row.run_at,
    enabled: row.enabled,
    backup_config: row.backup_config || { compression: 'zstd' },
    retention_days: row.retention_policy?.keep_days || 30,
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const data = {
      name: form.name,
      database_id: form.database_id,
      storage_id: form.storage_id,
      schedule_type: form.schedule_type,
      enabled: form.enabled,
      backup_config: form.backup_config,
      retention_policy: { keep_days: form.retention_days },
    }
    if (form.schedule_type === 'cron') {
      data.cron_expr = form.cron_expr
    } else if (form.schedule_type === 'interval') {
      data.interval_seconds = form.interval_seconds
    } else {
      data.run_at = form.run_at
    }

    if (isEdit.value) {
      await updateJob(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createJob(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Failed to submit:', error)
  } finally {
    submitting.value = false
  }
}

const handleToggle = async (row) => {
  try {
    if (row.enabled) {
      await enableJob(row.id)
    } else {
      await disableJob(row.id)
    }
    ElMessage.success('状态已更新')
  } catch (error) {
    row.enabled = !row.enabled
    console.error('Failed to toggle:', error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除任务 "${row.name}" 吗？`, '确认删除', { type: 'warning' })
    await deleteJob(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete:', error)
    }
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
