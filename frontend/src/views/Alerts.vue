<template>
  <div class="alerts">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('alert.title') }}</span>
          <div class="header-filters">
            <el-input v-model="searchTitle" :placeholder="$t('alert.searchTitle')" clearable style="width: 180px" @input="applyFilters" />
            <el-select v-model="filterSeverity" :placeholder="$t('alert.severityFilter')" clearable style="width: 130px" @change="applyFilters">
              <el-option label="严重" value="CRITICAL" />
              <el-option label="错误" value="ERROR" />
              <el-option label="警告" value="WARNING" />
              <el-option label="信息" value="INFO" />
            </el-select>
            <el-select v-model="statusFilter" :placeholder="$t('alert.statusFilter')" clearable style="width: 130px" @change="applyFilters">
              <el-option label="OPEN" value="OPEN" />
              <el-option label="RESOLVED" value="RESOLVED" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="alerts" v-loading="loading" border stripe style="width: 100%" size="default" empty-text="No data available">
        <el-table-column prop="id" label="ID" width="80" sortable />
        <el-table-column prop="title" :label="$t('dashboard.title')" width="200" sortable />
        <el-table-column prop="alert_type" :label="$t('alert.alertType')" width="120" sortable />
        <el-table-column prop="severity" :label="$t('dashboard.severity')" width="100" sortable>
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="$t('common.status')" width="100" sortable>
          <template #default="{ row }">
            <el-tag :type="row.status === 'OPEN' ? 'danger' : 'success'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" :label="$t('alert.resourceType')" width="120" sortable />
        <el-table-column prop="message" :label="$t('alert.message')" min-width="200" show-overflow-tooltip sortable />
        <el-table-column prop="created_at" :label="$t('common.createTime')" width="180" sortable>
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="resolved_at" :label="$t('alert.resolvedAt')" width="180" sortable>
          <template #default="{ row }">
            {{ formatTime(row.resolved_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="handleResolve(row)" :disabled="row.status !== 'OPEN'">{{ $t('alert.resolve') }}</el-button>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { getAlerts, resolveAlert } from '../api/alerts'

const alerts = ref([])
const loading = ref(false)
const statusFilter = ref('')
const filterSeverity = ref('')
const searchTitle = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const { t } = useI18n()

const getSeverityType = (severity) => {
  const map = { CRITICAL: 'danger', ERROR: 'danger', WARNING: 'warning', INFO: 'info' }
  return map[severity] || 'info'
}

const formatTime = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (searchTitle.value) {
      params.title = searchTitle.value
    }
    if (filterSeverity.value) {
      params.severity = filterSeverity.value
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    const response = await getAlerts(params)
    alerts.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error) {
    console.error('Failed to fetch alerts:', error)
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  page.value = 1
  fetchData()
}

const handleResolve = async (row) => {
  try {
    await resolveAlert(row.id)
    ElMessage.success(t('alert.resolvedSuccess'))
    fetchData()
  } catch (error) {
    console.error('Failed to resolve alert:', error)
  }
}

onMounted(() => {
  fetchData()
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
