<template>
  <div class="backups">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>备份列表</span>
          <el-button type="primary" @click="showBackupDialog">
            <el-icon><Upload /></el-icon>
            立即备份
          </el-button>
        </div>
      </template>

      <el-table :data="backups" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
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
        <el-table-column prop="backup_type" label="类型" width="100" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="size_bytes" label="大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.size_bytes) }}
          </template>
        </el-table-column>
        <el-table-column prop="compression" label="压缩" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleVerify(row)" :disabled="row.status !== 'AVAILABLE'">校验</el-button>
            <el-button size="small" type="primary" @click="handleDownload(row)">下载</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
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

    <el-dialog v-model="backupDialogVisible" title="立即备份" width="500px">
      <el-form :model="backupForm" :rules="backupRules" ref="backupFormRef" label-width="100px">
        <el-form-item label="数据库" prop="database_id">
          <el-select v-model="backupForm.database_id" style="width: 100%" placeholder="选择数据库">
            <el-option v-for="db in databases" :key="db.id" :label="db.name" :value="db.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="存储" prop="storage_id">
          <el-select v-model="backupForm.storage_id" style="width: 100%" placeholder="选择存储">
            <el-option v-for="s in storages" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="压缩方式">
          <el-select v-model="backupForm.compression" style="width: 100%">
            <el-option label="zstd" value="zstd" />
            <el-option label="gzip" value="gzip" />
            <el-option label="无" value="none" />
          </el-select>
        </el-form-item>
        <el-form-item label="保留天数">
          <el-input-number v-model="backupForm.retention_days" :min="1" :max="365" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="backupDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBackup" :loading="backupLoading">开始备份</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getBackups, runBackup, deleteBackup, verifyBackup, downloadBackup } from '../api/backups'
import { getDatabases } from '../api/databases'
import { getStorages } from '../api/storages'

const backups = ref([])
const databases = ref([])
const storages = ref([])
const loading = ref(false)
const backupLoading = ref(false)
const backupDialogVisible = ref(false)
const backupFormRef = ref(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const backupForm = reactive({
  database_id: null,
  storage_id: null,
  compression: 'zstd',
  retention_days: 30,
})

const backupRules = {
  database_id: [{ required: true, message: '请选择数据库', trigger: 'change' }],
  storage_id: [{ required: true, message: '请选择存储', trigger: 'change' }],
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

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(2)} ${units[i]}`
}

const fetchData = async () => {
  loading.value = true
  try {
    const response = await getBackups({ page: page.value, page_size: pageSize.value })
    backups.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error) {
    console.error('Failed to fetch backups:', error)
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

const showBackupDialog = () => {
  backupDialogVisible.value = true
}

const handleBackup = async () => {
  const valid = await backupFormRef.value.validate().catch(() => false)
  if (!valid) return

  backupLoading.value = true
  try {
    await runBackup({
      database_id: backupForm.database_id,
      storage_id: backupForm.storage_id,
      compression: backupForm.compression,
      retention: { keep_days: backupForm.retention_days },
    })
    ElMessage.success('备份任务已提交')
    backupDialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Failed to run backup:', error)
  } finally {
    backupLoading.value = false
  }
}

const handleVerify = async (row) => {
  try {
    await verifyBackup(row.id)
    ElMessage.success('校验任务已提交')
  } catch (error) {
    console.error('Failed to verify:', error)
  }
}

const handleDownload = async (row) => {
  try {
    const response = await downloadBackup(row.id)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', row.filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (error) {
    console.error('Failed to download:', error)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除备份 "${row.filename}" 吗？`, '确认删除', { type: 'warning' })
    await deleteBackup(row.id)
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
