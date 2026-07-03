<template>
  <div class="databases">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('database.list') }}</span>
          <div class="header-filters">
            <el-input v-model="searchName" :placeholder="$t('database.searchName')" clearable style="width: 180px" @input="applyFilters" />
            <el-select v-model="filterDbType" :placeholder="$t('database.type')" clearable style="width: 140px" @change="applyFilters">
              <el-option label="MySQL" value="mysql" />
              <el-option label="PostgreSQL" value="postgresql" />
              <el-option label="MariaDB" value="mariadb" />
            </el-select>
            <el-select v-model="filterEnv" :placeholder="$t('database.env')" clearable style="width: 120px" @change="applyFilters">
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

      <el-table :data="databases" v-loading="loading" border stripe style="width: 100%" size="default" :empty-text="$t('common.noData')">
        <el-table-column prop="id" label="ID" width="80" sortable />
        <el-table-column prop="name" :label="$t('database.name')" sortable />
        <el-table-column prop="db_type" :label="$t('database.type')" width="120" sortable>
          <template #default="{ row }">
            <el-tag>{{ row.db_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="connection_type" :label="$t('database.connectionType')" width="120" sortable>
          <template #default="{ row }">
            <el-tag :type="row.connection_type === 'kubernetes' ? 'warning' : 'primary'" size="small">
              {{ row.connection_type === 'kubernetes' ? 'K8s' : $t('database.directConnection') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" :label="$t('database.host')" sortable>
          <template #default="{ row }">
            {{ row.connection_type === 'kubernetes' ? '-' : (row.host || '-') }}
          </template>
        </el-table-column>
        <el-table-column prop="port" :label="$t('database.port')" width="80" sortable>
          <template #default="{ row }">
            {{ row.connection_type === 'kubernetes' ? '-' : (row.port || '-') }}
          </template>
        </el-table-column>
        <el-table-column prop="database_name" :label="$t('database.databaseName')" width="120" sortable>
          <template #default="{ row }">
            {{ row.database_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="environment" :label="$t('database.env')" width="100" sortable>
          <template #default="{ row }">
            <el-tag :type="getEnvType(row.environment)" size="small">{{ row.environment }}</el-tag>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? $t('database.editInstance') : $t('database.addInstance')" width="680px" top="5vh">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="140px">
        <el-form-item :label="$t('database.name')" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item :label="$t('database.connectionType')" prop="connection_type">
          <el-radio-group v-model="form.connection_type" @change="onConnectionTypeChange">
            <el-radio value="direct">{{ $t('database.directConnection') }}</el-radio>
            <el-radio value="kubernetes">Kubernetes</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('database.type')" prop="db_type">
          <el-select v-model="form.db_type" style="width: 100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="MariaDB" value="mariadb" />
          </el-select>
        </el-form-item>
        <template v-if="form.connection_type === 'direct'">
          <el-form-item :label="$t('database.host')" prop="host">
            <el-input v-model="form.host" placeholder="127.0.0.1" />
          </el-form-item>
          <el-form-item :label="$t('database.port')" prop="port">
            <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
          </el-form-item>
        </template>
        <el-form-item :label="$t('database.username')" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item :label="$t('database.password')" prop="password">
          <el-input v-model="form.password" type="password" show-password :placeholder="isEdit ? $t('database.passwordEditPlaceholder') : ''" />
        </el-form-item>
        <el-form-item :label="$t('database.databaseName')">
          <el-input v-model="form.database_name" :placeholder="$t('database.dbNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('database.env')" prop="environment">
          <el-select v-model="form.environment" style="width: 100%">
            <el-option :label="$t('database.envProd')" value="prod" />
            <el-option :label="$t('database.envTest')" value="test" />
            <el-option :label="$t('database.envDev')" value="dev" />
          </el-select>
        </el-form-item>

        <template v-if="form.connection_type === 'kubernetes'">
          <el-divider>{{ $t('database.k8sConfig') }}</el-divider>
          <el-form-item :label="$t('database.k8sCluster')">
            <div style="display: flex; gap: 8px; width: 100%">
              <el-select v-model="selectedKubeconfig" filterable style="flex: 1" :placeholder="$t('database.k8sClusterPlaceholder')" @change="onKubeconfigChange">
                <el-option v-for="kc in kubeconfigList" :key="kc.name" :label="kc.name" :value="kc.name" />
              </el-select>
              <el-button @click="showClusterDialog">
                {{ $t('database.k8sManageClusters') }}
              </el-button>
            </div>
          </el-form-item>
          <el-form-item :label="$t('database.k8sContext')">
            <el-select v-model="form.k8s_config.context" filterable allow-create :placeholder="$t('database.k8sContextPlaceholder')" style="width: 100%" @change="onContextChange">
              <el-option v-for="ctx in currentKubeconfigContexts" :key="ctx" :label="ctx" :value="ctx" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('database.k8sNamespace')" prop="k8s_config.namespace">
            <div style="display: flex; gap: 8px; width: 100%">
              <el-select v-model="form.k8s_config.namespace" filterable allow-create style="flex: 1" :loading="k8sNamespacesLoading">
                <el-option v-for="ns in k8sNamespaces" :key="ns" :label="ns" :value="ns" />
              </el-select>
              <el-button
                @click="fetchK8sNamespaces"
                :loading="k8sNamespacesLoading"
                :aria-label="$t('common.refresh')"
                :title="$t('common.refresh')"
              >
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </el-form-item>
          <el-form-item :label="$t('database.k8sPodSelector')">
            <el-radio-group v-model="k8sSelectorType" style="margin-bottom: 8px">
              <el-radio value="pod_name">{{ $t('database.k8sPodName') }}</el-radio>
              <el-radio value="label_selector">{{ $t('database.k8sLabelSelector') }}</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="k8sSelectorType === 'pod_name'" :label="$t('database.k8sPodName')" prop="k8s_config.pod_name">
            <div style="display: flex; gap: 8px; width: 100%">
              <el-select v-model="form.k8s_config.pod_name" filterable allow-create style="flex: 1" :loading="k8sPodsLoading" @change="onPodChange">
                <el-option v-for="pod in k8sPods" :key="pod.name" :label="pod.name" :value="pod.name">
                  <span style="float: left">{{ pod.name }}</span>
                  <el-tag :type="getPodStatusType(pod.status)" size="small" style="float: right">{{ pod.status }}</el-tag>
                </el-option>
              </el-select>
              <el-button
                @click="fetchK8sPods"
                :loading="k8sPodsLoading"
                :aria-label="$t('common.refresh')"
                :title="$t('common.refresh')"
              >
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </el-form-item>
          <el-form-item v-if="k8sSelectorType === 'label_selector'" :label="$t('database.k8sLabelSelector')" prop="k8s_config.label_selector">
            <el-input v-model="form.k8s_config.label_selector" placeholder="app=mysql" @input="clearPodName" />
          </el-form-item>
          <el-form-item :label="$t('database.k8sContainer')">
            <el-select v-model="form.k8s_config.container" filterable allow-create :placeholder="$t('database.k8sContainerPlaceholder')" style="width: 100%">
              <el-option v-for="c in k8sContainers" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
        </template>

        <el-form-item v-if="form.connection_type === 'direct'" :label="$t('database.enableSsl')">
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

    <el-dialog v-model="clusterDialogVisible" :title="$t('database.k8sManageClusters')" width="720px" top="5vh">
      <div style="margin-bottom: 16px">
        <el-alert :title="$t('database.k8sManageTip')" type="info" :closable="false" show-icon style="margin-bottom: 12px" />
        <el-form :model="uploadForm" :rules="uploadRules" ref="uploadFormRef" label-width="100px" size="small">
          <el-form-item :label="$t('database.k8sClusterName')" prop="name">
            <el-input v-model="uploadForm.name" :placeholder="$t('database.k8sClusterNamePlaceholder')" />
          </el-form-item>
          <el-form-item :label="$t('database.k8sKubeconfigContent')" prop="content">
            <el-input v-model="uploadForm.content" type="textarea" :rows="8" :placeholder="$t('database.k8sKubeconfigContentPlaceholder')" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleUploadKubeconfig" :loading="uploading">{{ $t('database.k8sUpload') }}</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-divider>{{ $t('database.k8sExistingClusters') }}</el-divider>
      <el-table :data="kubeconfigList" v-loading="kubeconfigLoading" border stripe size="small" :empty-text="$t('common.noData')">
        <el-table-column prop="name" :label="$t('database.k8sClusterName')" sortable />
        <el-table-column :label="$t('database.k8sContexts')" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="ctx in row.contexts" :key="ctx" size="small" style="margin: 2px" :type="ctx === row.current_context ? 'primary' : ''">
              {{ ctx }}{{ ctx === row.current_context ? ' *' : '' }}
            </el-tag>
            <span v-if="!row.contexts.length" style="color: #999">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('database.k8sTestStatus')" width="100">
          <template #default="{ row }">
            <el-tag v-if="kubeconfigTestResults[row.name] === true" type="success" size="small">{{ $t('common.ok') }}</el-tag>
            <el-tag v-else-if="kubeconfigTestResults[row.name] === false" type="danger" size="small">{{ $t('common.fail') }}</el-tag>
            <span v-else style="color: #999">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="140">
          <template #default="{ row }">
            <el-button size="small" @click="handleTestKubeconfig(row)">{{ $t('database.testConnection') }}</el-button>
            <el-button size="small" type="danger" @click="handleDeleteKubeconfig(row)">{{ $t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDatabases, createDatabase, updateDatabase, deleteDatabase, testSavedDatabase, getK8sNamespaces, getK8sPods } from '../api/databases'
import { getKubeconfigs, createKubeconfig, deleteKubeconfig, testKubeconfig } from '../api/kubeconfigs'

const databases = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)
const uploadFormRef = ref(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const { t } = useI18n()
const searchName = ref('')
const filterDbType = ref('')
const filterEnv = ref('')

const k8sSelectorType = ref('pod_name')
const k8sNamespaces = ref([])
const k8sPods = ref([])
const k8sContainers = ref([])
const k8sNamespacesLoading = ref(false)
const k8sPodsLoading = ref(false)

const kubeconfigList = ref([])
const kubeconfigLoading = ref(false)
const selectedKubeconfig = ref('')
const clusterDialogVisible = ref(false)
const uploading = ref(false)
const kubeconfigTestResults = reactive({})

const uploadForm = reactive({
  name: '',
  content: '',
})

const currentKubeconfigContexts = computed(() => {
  if (!selectedKubeconfig.value) return []
  const kc = kubeconfigList.value.find((k) => k.name === selectedKubeconfig.value)
  return kc ? kc.contexts : []
})

const defaultForm = {
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
  connection_type: 'direct',
  k8s_config: {
    namespace: 'default',
    pod_name: '',
    label_selector: '',
    container: '',
    kubeconfig: '',
    context: '',
  },
}

const form = reactive({ ...defaultForm, k8s_config: { ...defaultForm.k8s_config } })

const hasValue = (value) => value !== undefined && value !== null && value !== ''

const requireDirectConnection = (label) => (_rule, value, callback) => {
  if (form.connection_type === 'direct' && !hasValue(value)) {
    callback(new Error(label))
    return
  }
  callback()
}

const requireK8sConfig = (label, isActive) => (_rule, value, callback) => {
  if (form.connection_type === 'kubernetes' && isActive() && !hasValue(value)) {
    callback(new Error(label))
    return
  }
  callback()
}

const rules = computed(() => ({
  connection_type: [{ required: true, message: t('database.connectionType'), trigger: 'change' }],
  name: [{ required: true, message: t('database.name'), trigger: 'blur' }],
  db_type: [{ required: true, message: t('database.type'), trigger: 'change' }],
  host: [{ required: form.connection_type === 'direct', validator: requireDirectConnection(t('database.host')), trigger: 'blur' }],
  port: [{ required: form.connection_type === 'direct', validator: requireDirectConnection(t('database.port')), trigger: 'change' }],
  username: [{ required: true, message: t('database.username'), trigger: 'blur' }],
  password: [{ required: !isEdit.value, message: t('database.password'), trigger: 'blur' }],
  environment: [{ required: true, message: t('database.env'), trigger: 'change' }],
  'k8s_config.namespace': [{ required: form.connection_type === 'kubernetes', validator: requireK8sConfig(t('database.k8sNamespace'), () => true), trigger: 'change' }],
  'k8s_config.pod_name': [{ required: form.connection_type === 'kubernetes' && k8sSelectorType.value === 'pod_name', validator: requireK8sConfig(t('database.k8sPodName'), () => k8sSelectorType.value === 'pod_name'), trigger: 'change' }],
  'k8s_config.label_selector': [{ required: form.connection_type === 'kubernetes' && k8sSelectorType.value === 'label_selector', validator: requireK8sConfig(t('database.k8sLabelSelector'), () => k8sSelectorType.value === 'label_selector'), trigger: 'blur' }],
}))

const uploadRules = {
  name: [{ required: true, message: t('database.k8sClusterName'), trigger: 'blur' }],
  content: [{ required: true, message: t('database.k8sKubeconfigContent'), trigger: 'blur' }],
}

const getEnvType = (env) => {
  const map = { prod: 'danger', test: 'warning', dev: 'info' }
  return map[env] || 'info'
}

const getPodStatusType = (status) => {
  const map = { Running: 'success', Pending: 'warning', Failed: 'danger', Succeeded: 'info' }
  return map[status] || 'info'
}

const fetchKubeconfigList = async () => {
  kubeconfigLoading.value = true
  try {
    const res = await getKubeconfigs()
    kubeconfigList.value = res.data || []
  } catch {
    kubeconfigList.value = []
  } finally {
    kubeconfigLoading.value = false
  }
}

const showClusterDialog = () => {
  clusterDialogVisible.value = true
  fetchKubeconfigList()
}

const handleUploadKubeconfig = async () => {
  const valid = await uploadFormRef.value.validate().catch(() => false)
  if (!valid) return
  uploading.value = true
  try {
    await createKubeconfig({ name: uploadForm.name, content: uploadForm.content })
    ElMessage.success(t('database.k8sUploadSuccess'))
    uploadForm.name = ''
    uploadForm.content = ''
    fetchKubeconfigList()
  } catch (error) {
    console.error('Failed to upload kubeconfig:', error)
  } finally {
    uploading.value = false
  }
}

const handleDeleteKubeconfig = async (row) => {
  try {
    await ElMessageBox.confirm(t('database.k8sDeleteConfirm', { name: row.name }), t('common.confirm'), { type: 'warning' })
    await deleteKubeconfig(row.name)
    ElMessage.success(t('common.deleteSuccess'))
    delete kubeconfigTestResults[row.name]
    fetchKubeconfigList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete kubeconfig:', error)
    }
  }
}

const handleTestKubeconfig = async (row) => {
  try {
    const res = await testKubeconfig(row.name)
    kubeconfigTestResults[row.name] = res.data.ok
    if (res.data.ok) {
      ElMessage.success(t('database.k8sTestSuccess', { count: (res.data.namespaces || []).length }))
    } else {
      ElMessage.error(res.data.message || t('database.k8sTestFailed'))
    }
  } catch (error) {
    kubeconfigTestResults[row.name] = false
    console.error('Failed to test kubeconfig:', error)
  }
}

const onKubeconfigChange = (name) => {
  const kc = kubeconfigList.value.find((k) => k.name === name)
  if (kc) {
    form.k8s_config.kubeconfig = kc.path
    if (kc.current_context) {
      form.k8s_config.context = kc.current_context
    } else if (kc.contexts.length > 0) {
      form.k8s_config.context = kc.contexts[0]
    } else {
      form.k8s_config.context = ''
    }
  } else {
    form.k8s_config.kubeconfig = ''
    form.k8s_config.context = ''
  }
  fetchK8sNamespaces()
}

const onContextChange = () => {
  fetchK8sNamespaces()
}

const onConnectionTypeChange = () => {
  if (form.connection_type === 'kubernetes') {
    form.host = 'localhost'
    form.port = form.db_type === 'postgresql' ? 5432 : 3306
    fetchKubeconfigList()
  }
}

const clearPodName = () => {
  form.k8s_config.pod_name = ''
}

const onPodChange = (podName) => {
  const pod = k8sPods.value.find((p) => p.name === podName)
  if (pod && pod.containers && pod.containers.length > 0) {
    k8sContainers.value = pod.containers
    if (!form.k8s_config.container || !pod.containers.includes(form.k8s_config.container)) {
      form.k8s_config.container = pod.containers[0]
    }
  }
}

const fetchK8sNamespaces = async () => {
  k8sNamespacesLoading.value = true
  try {
    const params = {}
    if (form.k8s_config.kubeconfig) params.kubeconfig = form.k8s_config.kubeconfig
    if (form.k8s_config.context) params.context = form.k8s_config.context
    const res = await getK8sNamespaces(params)
    k8sNamespaces.value = res.data.namespaces || []
  } catch {
    k8sNamespaces.value = []
  } finally {
    k8sNamespacesLoading.value = false
  }
}

const fetchK8sPods = async () => {
  k8sPodsLoading.value = true
  try {
    const params = { namespace: form.k8s_config.namespace || 'default' }
    if (form.k8s_config.kubeconfig) params.kubeconfig = form.k8s_config.kubeconfig
    if (form.k8s_config.context) params.context = form.k8s_config.context
    const res = await getK8sPods(params)
    k8sPods.value = res.data.pods || []
  } catch {
    k8sPods.value = []
  } finally {
    k8sPodsLoading.value = false
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (searchName.value) {
      params.name = searchName.value
    }
    if (filterDbType.value) {
      params.db_type = filterDbType.value
    }
    if (filterEnv.value) {
      params.environment = filterEnv.value
    }
    const response = await getDatabases(params)
    databases.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error) {
    console.error('Failed to fetch databases:', error)
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  page.value = 1
  fetchData()
}

const resetForm = () => {
  Object.assign(form, { ...defaultForm, k8s_config: { ...defaultForm.k8s_config } })
  k8sSelectorType.value = 'pod_name'
  k8sNamespaces.value = []
  k8sPods.value = []
  k8sContainers.value = []
  selectedKubeconfig.value = ''
}

const showCreateDialog = () => {
  isEdit.value = false
  editId.value = null
  resetForm()
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  editId.value = row.id
  resetForm()
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
    connection_type: row.connection_type || 'direct',
  })
  if (row.k8s_config) {
    Object.assign(form.k8s_config, {
      namespace: row.k8s_config.namespace || 'default',
      pod_name: row.k8s_config.pod_name || '',
      label_selector: row.k8s_config.label_selector || '',
      container: row.k8s_config.container || '',
      kubeconfig: row.k8s_config.kubeconfig || '',
      context: row.k8s_config.context || '',
    })
    if (row.k8s_config.label_selector && !row.k8s_config.pod_name) {
      k8sSelectorType.value = 'label_selector'
    } else {
      k8sSelectorType.value = 'pod_name'
    }
    if (row.k8s_config.kubeconfig) {
      fetchKubeconfigList()
    }
  }
  if (form.connection_type === 'kubernetes') {
    fetchKubeconfigList()
    fetchK8sNamespaces()
    if (form.k8s_config.namespace) {
      fetchK8sPods()
    }
  }
  dialogVisible.value = true
}

const buildPayload = () => {
  const isK8s = form.connection_type === 'kubernetes'
  const payload = {
    name: form.name,
    db_type: form.db_type,
    host: isK8s ? null : form.host,
    port: isK8s ? null : form.port,
    username: form.username,
    password: form.password || null,
    database_name: form.database_name || null,
    ssl_enabled: isK8s ? false : form.ssl_enabled,
    environment: form.environment,
    description: form.description || null,
    connection_type: form.connection_type,
    k8s_config: null,
  }
  if (form.connection_type === 'kubernetes') {
    const k8s = {
      namespace: form.k8s_config.namespace || 'default',
      kubeconfig: form.k8s_config.kubeconfig || null,
      context: form.k8s_config.context || null,
      pod_name: null,
      label_selector: null,
      container: form.k8s_config.container || null,
    }
    if (k8sSelectorType.value === 'pod_name') {
      k8s.pod_name = form.k8s_config.pod_name || null
    } else {
      k8s.label_selector = form.k8s_config.label_selector || null
    }
    payload.k8s_config = k8s
  }
  return payload
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await updateDatabase(editId.value, payload)
      ElMessage.success(t('common.updateSuccess'))
    } else {
      await createDatabase(payload)
      ElMessage.success(t('common.createSuccess'))
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
    const res = await testSavedDatabase(row.id)
    const data = res.data || res
    if (data.ok) {
      ElMessage.success(t('database.testSuccess'))
    } else {
      ElMessage.error(data.message || t('database.testFailed'))
    }
  } catch (error) {
    ElMessage.error(error?.response?.data?.error?.message || t('database.testFailed'))
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
