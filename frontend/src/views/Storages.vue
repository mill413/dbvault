<template>
  <div class="storages">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('storage.title') }}</span>
          <div class="header-filters">
            <el-select v-model="filterType" :placeholder="$t('storage.typeFilter')" clearable style="width: 140px">
              <el-option label="Local" value="local" />
              <el-option label="S3" value="s3" />
            </el-select>
            <el-select v-model="filterStatus" :placeholder="$t('storage.statusFilter')" clearable style="width: 120px">
              <el-option label="ACTIVE" value="ACTIVE" />
              <el-option label="INACTIVE" value="INACTIVE" />
            </el-select>
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              {{ $t('common.add') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredStorages" v-loading="loading" style="width: 100%" size="default" empty-text="No data available">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" :label="$t('storage.name')" />
        <el-table-column prop="storage_type" :label="$t('storage.type')" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.storage_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_default" :label="$t('storage.isDefault')" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success" size="small">{{ $t('common.yes') }}</el-tag>
            <el-tag v-else type="info" size="small">{{ $t('common.no') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="$t('common.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('storage.capacityLimit')" width="140">
          <template #default="{ row }">
            {{ row.capacity_limit_bytes ? formatSize(row.capacity_limit_bytes) : '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="testStorage(row)">{{ $t('storage.test') }}</el-button>
            <el-button size="small" type="primary" @click="showEditDialog(row)">{{ $t('common.edit') }}</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">{{ $t('common.delete') }}</el-button>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? $t('storage.editStorage') : $t('storage.addStorage')" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item :label="$t('storage.name')" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item :label="$t('storage.type')" prop="storage_type">
          <el-select v-model="form.storage_type" style="width: 100%" @change="onTypeChange">
            <el-option label="Local" value="local" />
            <el-option label="MinIO/S3" value="s3" />
          </el-select>
        </el-form-item>

        <template v-if="form.storage_type === 'local'">
          <el-form-item :label="$t('storage.path')" prop="config.path">
            <el-input v-model="form.config.path" placeholder="/path/to/backups" />
          </el-form-item>
        </template>

        <template v-if="form.storage_type === 's3'">
          <el-form-item :label="$t('storage.endpoint')" prop="config.endpoint_url">
            <el-input v-model="form.config.endpoint_url" placeholder="http://minio:9000" />
          </el-form-item>
          <el-form-item :label="$t('storage.accessKey')" prop="config.access_key">
            <el-input v-model="form.config.access_key" />
          </el-form-item>
          <el-form-item :label="$t('storage.secretKey')" prop="config.secret_key">
            <el-input v-model="form.config.secret_key" type="password" show-password />
          </el-form-item>
          <el-form-item :label="$t('storage.bucket')" prop="config.bucket">
            <el-input v-model="form.config.bucket" />
          </el-form-item>
          <el-form-item :label="$t('storage.region')">
            <el-input v-model="form.config.region" placeholder="us-east-1" />
          </el-form-item>
        </template>

        <el-form-item :label="$t('storage.capacityLimit')">
          <el-input-number
            v-model="form.capacity_limit_gb"
            :min="0"
            :step="1"
            controls-position="right"
            :placeholder="$t('storage.capacityLimitPlaceholder')"
            style="width: 100%"
          />
          <span style="margin-left: 8px; color: #909399; font-size: 12px">GB</span>
        </el-form-item>
        <el-form-item :label="$t('storage.isDefault')">
          <el-switch v-model="form.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getStorages, createStorage, updateStorage, deleteStorage, testStorage as testStorageApi } from '../api/storages'

const storages = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)
const filterType = ref('')
const filterStatus = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const { t } = useI18n()

const form = reactive({
  name: '',
  storage_type: 'local',
  config: {},
  is_default: false,
})

const rules = {
  name: [{ required: true, message: t('storage.nameRequired'), trigger: 'blur' }],
  storage_type: [{ required: true, message: t('storage.typeRequired'), trigger: 'change' }],
}

const onTypeChange = () => {
  form.config = {}
}

const filteredStorages = computed(() => {
  let result = storages.value
  if (filterType.value) {
    result = result.filter(item => item.storage_type === filterType.value)
  }
  if (filterStatus.value) {
    result = result.filter(item => item.status === filterStatus.value)
  }
  return result
})

const formatSize = (bytes) => {
  if (!bytes) return '-'
  const gb = bytes / (1024 * 1024 * 1024)
  if (gb >= 1024) return `${(gb / 1024).toFixed(1)} TB`
  return `${gb.toFixed(1)} GB`
}

const fetchData = async () => {
  loading.value = true
  try {
    const response = await getStorages({ page: page.value, page_size: pageSize.value })
    storages.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error) {
    console.error('Failed to fetch storages:', error)
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  editId.value = null
  Object.assign(form, {
    name: '',
    storage_type: 'local',
    config: {},
    is_default: false,
    capacity_limit_gb: null,
  })
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    name: row.name,
    storage_type: row.storage_type,
    config: {},
    is_default: row.is_default,
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const config = form.storage_type === 'local'
    ? { path: form.config.path }
    : {
        endpoint_url: form.config.endpoint_url,
        access_key: form.config.access_key,
        secret_key: form.config.secret_key,
        bucket: form.config.bucket,
        region: form.config.region,
      }

  const capacity_limit_bytes = form.capacity_limit_gb && form.capacity_limit_gb > 0
    ? Math.round(form.capacity_limit_gb * 1024 * 1024 * 1024)
    : null

  const payload = {
    name: form.name,
    storage_type: form.storage_type,
    is_default: form.is_default,
    capacity_limit_bytes,
    config,
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateStorage(editId.value, payload)
      ElMessage.success(t('common.updateSuccess'))
    } else {
      await createStorage(payload)
      ElMessage.success(t('common.createSuccess'))
    }
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Failed to save storage:', error)
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(t('storage.deleteConfirm', { name: row.name }), t('common.confirm'), { type: 'warning' })
    await deleteStorage(row.id)
    ElMessage.success(t('common.deleteSuccess'))
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete:', error)
    }
  }
}

const testStorage = async (row) => {
  try {
    await testStorageApi(row.id)
    ElMessage.success(t('storage.testSuccess'))
  } catch (error) {
    console.error('Storage test failed:', error)
  }
}

onMounted(fetchData)
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
