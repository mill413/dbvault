<template>
  <div class="dashboard">
    <!-- Stat Cards -->
    <el-row :gutter="24">
      <el-col :span="6" v-for="(stat, index) in statCards" :key="index">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon-wrapper" :style="{ backgroundColor: stat.bgColor }">
            <el-icon :size="28" :style="{ color: stat.color }"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
          <div class="stat-bg-icon">
            <el-icon><component :is="stat.icon" /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts -->
    <el-row :gutter="24" class="mt-24">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>Backup Success Trends (Last 7 Days)</span>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>Storage Usage Distribution</span>
            </div>
          </template>
          <div ref="storageChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Tables -->
    <el-row :gutter="24" class="mt-24">
      <el-col :span="12">
        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>Recent Backups</span>
              <el-button type="primary" link @click="$router.push('/backups')">View All</el-button>
            </div>
          </template>
          <el-table :data="recentBackups" style="width: 100%" size="default">
            <el-table-column prop="database.name" label="Database" />
            <el-table-column prop="status" label="Status" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small" effect="light">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Time" width="160">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>Active Alerts</span>
              <el-button type="primary" link @click="$router.push('/alerts')">View All</el-button>
            </div>
          </template>
          <el-table :data="recentAlerts" style="width: 100%" size="default">
            <el-table-column prop="title" label="Title" show-overflow-tooltip />
            <el-table-column prop="severity" label="Severity" width="100">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)" size="small" effect="dark">{{ row.severity }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Time" width="160">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import dayjs from 'dayjs'
import * as echarts from 'echarts'
import { getDashboardSummary, getBackupTrends, getAlerts, getStorageUsage } from '../api/common'
import { getBackups } from '../api/backups'

const stats = ref({})
const recentBackups = ref([])
const recentAlerts = ref([])
const trendChartRef = ref(null)
const storageChartRef = ref(null)

let trendChart = null
let storageChart = null

const statCards = ref([
  { label: 'Total Databases', value: 0, icon: 'Coin', color: '#00d2ff', bgColor: 'rgba(0, 210, 255, 0.1)' },
  { label: 'Total Backups', value: 0, icon: 'Upload', color: '#00e676', bgColor: 'rgba(0, 230, 118, 0.1)' },
  { label: 'Active Jobs', value: 0, icon: 'Clock', color: '#ffb74d', bgColor: 'rgba(255, 183, 77, 0.1)' },
  { label: 'Open Alerts', value: 0, icon: 'Warning', color: '#f1416c', bgColor: 'rgba(241, 65, 108, 0.1)' },
])

const formatTime = (date) => {
  if (!date) return '-'
  return dayjs(date).format('MM-DD HH:mm')
}

const getStatusType = (status) => {
  const map = { COMPLETED: 'success', RUNNING: 'warning', FAILED: 'danger', PENDING: 'info', SUCCESS: 'success' }
  return map[status] || 'info'
}

const getSeverityType = (severity) => {
  const map = { CRITICAL: 'danger', HIGH: 'danger', ERROR: 'danger', MEDIUM: 'warning', WARNING: 'warning', LOW: 'info', INFO: 'info' }
  return map[severity] || 'info'
}

const initTrendChart = (data) => {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value)
  
  const dates = data.map(item => item.date)
  const success = data.map(item => item.success_count)
  const failed = data.map(item => item.failed_count)

  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Success', 'Failed'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: dates, axisLine: { lineStyle: { color: '#e4e6ef' } }, axisLabel: { color: '#a1a5b7' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#eff2f5', type: 'dashed' } }, axisLabel: { color: '#a1a5b7' } },
    series: [
      {
        name: 'Success', type: 'line', smooth: true,
        lineStyle: { width: 3, color: '#00e676' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(0, 230, 118, 0.3)' }, { offset: 1, color: 'rgba(0, 230, 118, 0.05)' }]) },
        data: success
      },
      {
        name: 'Failed', type: 'line', smooth: true,
        lineStyle: { width: 3, color: '#f1416c' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(241, 65, 108, 0.3)' }, { offset: 1, color: 'rgba(241, 65, 108, 0.05)' }]) },
        data: failed
      }
    ]
  }
  trendChart.setOption(option)
}

const initStorageChart = (data) => {
  if (!storageChartRef.value) return
  storageChart = echarts.init(storageChartRef.value)
  
  const chartData = data && data.length > 0 ? data.map(item => ({ name: item.storage_name, value: item.used_bytes })) : [{ name: 'No Data', value: 0 }]

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const val = (params.value / (1024 * 1024)).toFixed(2)
        return `${params.name}: ${val} MB`
      }
    },
    legend: { top: 'bottom' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: chartData,
        color: ['#00d2ff', '#4ddbff', '#80e5ff', '#b3f0ff', '#e6faff']
      }
    ]
  }
  storageChart.setOption(option)
}

onMounted(async () => {
  try {
    const summaryRes = await getDashboardSummary()
    stats.value = summaryRes.data || {}
    
    statCards.value[0].value = stats.value.database_count || 0
    statCards.value[1].value = stats.value.backup_count || 0
    statCards.value[2].value = stats.value.job_count || 0
    statCards.value[3].value = stats.value.alert_count || 0

    const backupsRes = await getBackups({ page: 1, page_size: 5 })
    recentBackups.value = backupsRes.data.items || []

    try {
      const alertsRes = await getAlerts({ page: 1, page_size: 5, status: 'OPEN' })
      recentAlerts.value = alertsRes.data.items || []
    } catch {
      recentAlerts.value = []
    }

    // Load chart data
    nextTick(async () => {
      try {
        const trendRes = await getBackupTrends()
        initTrendChart(trendRes.data || [])
      } catch {
        initTrendChart([])
      }
      
      try {
        const storageRes = await getStorageUsage()
        initStorageChart(storageRes.data || [])
      } catch {
        initStorageChart([])
      }
    })

    window.addEventListener('resize', handleResize)
  } catch (error) {
    console.error('Failed to load dashboard:', error)
  }
})

const handleResize = () => {
  if (trendChart) trendChart.resize()
  if (storageChart) storageChart.resize()
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (trendChart) trendChart.dispose()
  if (storageChart) storageChart.dispose()
})
</script>

<style scoped>
.mt-24 {
  margin-top: 24px;
}

.stat-card {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 8px;
}

.stat-icon-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  z-index: 1;
}

.stat-info {
  z-index: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #181c32;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #a1a5b7;
  font-weight: 500;
  margin-top: 4px;
}

.stat-bg-icon {
  position: absolute;
  right: -20px;
  top: -20px;
  font-size: 120px;
  color: #f5f8fa;
  opacity: 0.5;
  z-index: 0;
  transform: rotate(-15deg);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 16px;
  color: #181c32;
}

.chart-container {
  height: 300px;
  width: 100%;
}

.table-card :deep(.el-card__body) {
  padding: 0;
}

.table-card .el-table {
  border-radius: 0 0 12px 12px;
}
</style>
