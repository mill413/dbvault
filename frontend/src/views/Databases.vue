<template>
  <div class="databases">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('database.list') }}</span>
          <div class="header-filters">
            <el-input v-model="searchName" :placeholder="$t('database.searchName')" clearable style="width: 180px" @input="fetchData" />
            <el-select v-model="filterDbType" :placeholder="$t('database.type')" clearable style="width: 140px" @change="fetchData">
              <el-option label="MySQL" value="mysql" />
              <el-option label="PostgreSQL" value="postgresql" />
              <el-option label="MariaDB" value="mariadb" />
            </el-select>
            <el-select v-model="filterEnv" :placeholder="$t('database.env')" clearable style="width: 120px" @change="fetchData">
              <el-option :label="$t('database.envProd')" value="prod" />
              <el-option :label="$t('database.envTest')" value="test" />
              <el-option :label="$t('database.envDev')" value="dev" />
            </el-select>
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              {{ $t('common.add') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="databases" v-loading="loading" style="width: 100%" size="default" :empty-text="$t('common.noData')">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" :label="$t('database.name')" />
        <el-table-column prop="db_type" :label="$t('database.type')" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.db_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" :label="$t('database.host')" />
        <el-table-column prop="port" :label="$t('database.port')" width="80" />
        <el-table-column prop="database_name" :label="$t('database.databaseName')" width="120">
          <template #default="{ row }">
            {{ row.database_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="environment" :label="$t('database.env')" width="100">
          <template #default="{ row }">
            <el-tag :type="getEnvType(row.environment)" size="small">{{ row.environment }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="$t('common.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="testConnection(row)">{{ $t('database.testConnection') }}</el-button>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? $t('database.editInstance') : $t('database.addInstance')" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item :label="$t('database.name')" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item :label="$t('database.type')" prop="db_type">
          <el-select v-model="form.db_type" style="width: 100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="MariaDB" value="mariadb" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('database.host')" prop="host">
          <el-input v-model="form.host" placeholder="127.0.0.1" />
        </el-form-item>
        <el-form-item :label="$t('database.port')" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item :label="$t('database.username')" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item :label="$t('database.password')" prop="password">
          <el-input v-model="form.password" type="password" show-password :placeholder="isEdit ? $t('database.passwordEditPlaceholder') : ''" />
        </el-form-item>
        <el-form-item :label="$t('database.databaseName')">
          <el-input v-model="form.database_name" :placeholder="$t('database.dbNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('database.env')">
          <el-select v-model="form.environment" style="width: 100%">
            <el-option :label="$t('database.envProd')" value="prod" />
            <el-option :label="$t('database.envTest')" value="test" />
            <el-option :label="$t('database.envDev')" value="dev" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('database.enableSsl')">
          <el-switch v-model="form.ssl_enabled" />
        </el-form-item>
        <el-form-item :label="$t('database.desc')">
          <el-input v-model="form.description" type="textarea" :rows="3" />
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
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDatabases, createDatabase, updateDatabase, deleteDatabase, testSavedDatabase } from '../api/databases'

const databases = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const { t } = useI18n()
const searchName = ref('')
const filterDbType = ref('')
const filterEnv = ref('')

const form = reactive({
  name: '',
  db_type: 'mysql',
  host: '',
  port: 3306,
  username: '',
  password: '',
  database_name: '',
  environment: 'prod',
  ssl_enabled: false,
  description: '',
})

const rules = {
  name: [{ required: true, message: t('database.name'), trigger: 'blur' }],
  db_type: [{ required: true, message: t('database.type'), trigger: 'change' }],
  host: [{ required: true, message: t('database.host'), trigger: 'blur' }],
  port: [{ required: true, message: t('database.port'), trigger: 'blur' }],
  username: [{ required: true, message: t('database.username'), trigger: 'blur' }],
  password: [{ required: true, message: t('database.password'), trigger: 'blur' }],
}

const getEnvType = (env) => {
  const map = { prod: 'danger', test: 'warning', dev: 'info' }
  return map[env] || 'info'
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filterDbType.value) {
      params.db_type = filterDbType.value
    }
    if (filterEnv.value) {
      params.environment = filterEnv.value
    }
    const response = await getDatabases(params)
    let items = response.data.items || []
    if (searchName.value) {
      const keyword = searchName.value.toLowerCase()
      items = items.filter((item) => item.name.toLowerCase().includes(keyword))
    }
    databases.value = items
    total.value = response.data.total || 0
  } catch (error) {
    console.error('Failed to fetch databases:', error)
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  editId.value = null
  Object.assign(form, {
    name: '',
    db_type: 'mysql',
    host: '',
    port: 3306,
    username: '',
    password: '',
    database_name: '',
    environment: 'prod',
    ssl_enabled: false,
    description: '',
  })
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    name: row.name,
    db_type: row.db_type,
    host: row.host,
    port: row.port,
    username: row.username,
    password: '',
    database_name: row.database_name || '',
    environment: row.environment,
    ssl_enabled: row.ssl_enabled,
    description: row.description || '',
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      await updateDatabase(editId.value, form)
      ElMessage.success(t('database.testSuccess'))
    } else {
      await createDatabase(form)
      ElMessage.success(t('database.testSuccess'))
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
    await ElMessageBox.confirm(t('database.deleteConfirm', { name: row.name }), t('common.confirm'), { type: 'warning' })
    await deleteDatabase(row.id)
    ElMessage.success(t('common.deleteSuccess'))
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete:', error)
    }
  }
}

const testConnection = async (row) => {
  try {
    await testSavedDatabase(row.id)
    ElMessage.success(t('database.testSuccess'))
  } catch (error) {
    console.error('Connection test failed:', error)
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
