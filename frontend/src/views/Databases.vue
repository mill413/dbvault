<template>
  <div class="databases">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据库实例列表</span>
          <div class="header-filters">
            <el-input v-model="searchName" placeholder="搜索实例名称" clearable style="width: 180px" @input="fetchData" />
            <el-select v-model="filterDbType" placeholder="数据库类型" clearable style="width: 140px" @change="fetchData">
              <el-option label="MySQL" value="mysql" />
              <el-option label="PostgreSQL" value="postgresql" />
              <el-option label="MariaDB" value="mariadb" />
            </el-select>
            <el-select v-model="filterEnv" placeholder="环境" clearable style="width: 120px" @change="fetchData">
              <el-option label="生产" value="prod" />
              <el-option label="测试" value="test" />
              <el-option label="开发" value="dev" />
            </el-select>
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              新增实例
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="databases" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="实例名称" />
        <el-table-column prop="db_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.db_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="database_name" label="数据库名" width="120">
          <template #default="{ row }">
            {{ row.database_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="environment" label="环境" width="100">
          <template #default="{ row }">
            <el-tag :type="getEnvType(row.environment)" size="small">{{ row.environment }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="testConnection(row)">测试连接</el-button>
            <el-button size="small" type="primary" @click="showEditDialog(row)">编辑</el-button>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑实例' : '新增实例'" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="实例名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="数据库类型" prop="db_type">
          <el-select v-model="form.db_type" style="width: 100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="MariaDB" value="mariadb" />
          </el-select>
        </el-form-item>
        <el-form-item label="主机" prop="host">
          <el-input v-model="form.host" placeholder="127.0.0.1" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="数据库名">
          <el-input v-model="form.database_name" />
        </el-form-item>
        <el-form-item label="环境">
          <el-select v-model="form.environment" style="width: 100%">
            <el-option label="生产环境" value="prod" />
            <el-option label="测试环境" value="test" />
            <el-option label="开发环境" value="dev" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用SSL">
          <el-switch v-model="form.ssl_enabled" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
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
  name: [{ required: true, message: '请输入实例名称', trigger: 'blur' }],
  db_type: [{ required: true, message: '请选择数据库类型', trigger: 'change' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
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
      ElMessage.success('更新成功')
    } else {
      await createDatabase(form)
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
    await ElMessageBox.confirm(`确定要删除实例 "${row.name}" 吗？`, '确认删除', { type: 'warning' })
    await deleteDatabase(row.id)
    ElMessage.success('删除成功')
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
    ElMessage.success('连接测试成功')
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
