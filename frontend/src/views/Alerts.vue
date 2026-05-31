<template>
  <div class="alerts">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>告警管理</span>
          <div class="header-filters">
            <el-input v-model="searchTitle" placeholder="搜索标题" clearable style="width: 180px" />
            <el-select v-model="filterSeverity" placeholder="严重级别" clearable style="width: 130px">
              <el-option label="严重" value="CRITICAL" />
              <el-option label="错误" value="ERROR" />
              <el-option label="警告" value="WARNING" />
              <el-option label="信息" value="INFO" />
            </el-select>
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 130px">
              <el-option label="OPEN" value="OPEN" />
              <el-option label="RESOLVED" value="RESOLVED" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="filteredAlerts" v-loading="loading" style="width: 100%" size="default" empty-text="No data available">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="title" label="标题" width="200" />
        <el-table-column prop="alert_type" label="类型" width="120" />
        <el-table-column prop="severity" label="严重级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'OPEN' ? 'danger' : 'success'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" label="资源类型" width="120" />
        <el-table-column prop="message" label="消息" min-width="200" show-overflow-tooltip />
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="解决时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.resolved_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="handleResolve(row)" :disabled="row.status !== 'OPEN'">Resolve</el-button>
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
import { ref, onMounted, computed } from 'vue'
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

const getSeverityType = (severity) => {
  const map = { CRITICAL: 'danger', ERROR: 'danger', WARNING: 'warning', INFO: 'info' }
  return map[severity] || 'info'
}

const formatTime = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const filteredAlerts = computed(() => {
  let result = alerts.value
  if (searchTitle.value) {
    const keyword = searchTitle.value.toLowerCase()
    result = result.filter((a) => (a.title || '').toLowerCase().includes(keyword))
  }
  if (filterSeverity.value) {
    result = result.filter((a) => a.severity === filterSeverity.value)
  }
  return result
})

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
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

const handleResolve = async (row) => {
  try {
    await resolveAlert(row.id)
    ElMessage.success('告警已解决')
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
