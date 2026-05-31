<template>
  <div class="storages">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('storage.title') }}</span>
          <div class="header-filters">
            <el-select v-model="filterType" :placeholder="$t('storage.typeFilter')" clearable style="width: 140px">
              <el-option label="本地存储" value="local" />
              <el-option label="S3" value="s3" />
            </el-select>
            <el-select v-model="filterStatus" :placeholder="$t('storage.statusFilter')" clearable style="width: 120px">
              <el-option label="ACTIVE" value="ACTIVE" />
              <el-option label="INACTIVE" value="INACTIVE" />
            </el-select>
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              Add Storage
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
            <el-tag v-if="row.is_default" type="success" size="small">是</el-tag>
            <el-tag v-else type="info" size="small">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="$t('common.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
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
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? $t('storage.editStorage') : $t('storage.addStorage')" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item :label="$t('storage.name')" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item :label="$t('storage.type')" prop="storage_type">
          <el-select v-model="form.storage_type" style="width: 100%" @change="onTypeChange">
            <el-option label="本地存储" value="local" />
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
const { t } = useI18n()

const form = reactive({
  name: '',
  storage_type: 'local',
  config: {},
  is_default: false,
})

const rules = {
  name: [{ required: true, message: '请输入存储名称', trigger: 'blur' }],
  storage_type: [{ required: true, message: '请选择存储类型', trigger: 'change' }],
}

const onTypeChange = () => {
  form.config = {}
}

const filteredStorages = computed(() => {
  let result = storages.value
  if (filterType.value) {
    result = result.filter((s) => s.storage_type === filterType.value)
  }
  if (filterStatus.value) {
    result = result.filter((s) => s.status === filterStatus.value)
  }
  return result
})

const fetchData = async () => {
  loading.value = true
  try {
    const response = await getStorages({ page_size: 100 })
    storages.value = response.data.items || []
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

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateStorage(editId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createStorage(form)
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

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(t('storage.deleteConfirm', { name: row.name }), t('common.confirm'), { type: 'warning' })
    await deleteStorage(row.id)
    ElMessage.success('删除成功')
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
