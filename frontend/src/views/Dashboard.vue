<template>
  <div class="dashboard">
    <!-- Stat Cards -->
    <el-row :gutter="24">
      <el-col :span="6" v-for="(stat, index) in statCards" :key="index">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-card-content">
            <div class="stat-info">
              <div class="stat-label">{{ stat.label }}</div>
              <div class="stat-value">{{ stat.value }}</div>
            </div>
            <div class="stat-icon-wrapper" :style="{ color: stat.color, backgroundColor: stat.bgColor }">
              <el-icon :size="28"><component :is="stat.icon" /></el-icon>
            </div>
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
              <span>{{ $t('dashboard.backupTrends') }}</span>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>{{ $t('dashboard.storageUsage') }}</span>
            </div>
          </template>
          <div ref="storageChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="storageCapacityList.length > 0" shadow="never" class="mt-24">
      <template #header>
        <span class="card-title">{{ $t('dashboard.storageCapacity') }}</span>
      </template>
      <div v-for="item in storageCapacityList" :key="item.storage_id" class="capacity-item">
        <div class="capacity-header">
          <span class="capacity-name">{{ item.storage_name }}</span>
          <span class="capacity-text">
            {{ formatBytes(item.used_bytes) }}
            <template v-if="item.capacity_limit_bytes"> / {{ formatBytes(item.capacity_limit_bytes) }}</template>
          </span>
        </div>
        <el-progress
          v-if="item.usage_percent !== null"
          :percentage="Math.min(item.usage_percent, 100)"
          :status="item.usage_percent >= 90 ? 'exception' : item.usage_percent >= 70 ? 'warning' : 'success'"
          :stroke-width="12"
          :show-text="false"
        />
        <div v-if="item.usage_percent !== null" class="capacity-percent" :class="{ 'capacity-warning': item.usage_percent >= 90 }">
          {{ item.usage_percent }}%
        </div>
      </div>
    </el-card>

    <!-- Tables -->
    <el-row :gutter="24" class="mt-24">
      <el-col :span="12">
        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>{{ $t('dashboard.recentBackups') }}</span>
              <el-button type="primary" link @click="$router.push('/backups')">{{ $t('common.viewAll') }}</el-button>
            </div>
          </template>
          <el-table :data="recentBackups" border stripe style="width: 100%" size="default">
            <el-table-column prop="database_id" :label="$t('dashboard.database')" sortable>
              <template #default="{ row }">
                {{ databaseMap[row.database_id] || `DB #${row.database_id}` }}
              </template>
            </el-table-column>
            <el-table-column prop="status" :label="$t('common.status')" width="120" sortable>
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small" effect="light">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="$t('common.time')" width="160" sortable>
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
              <span>{{ $t('dashboard.activeAlerts') }}</span>
              <el-button type="primary" link @click="$router.push('/alerts')">{{ $t('common.viewAll') }}</el-button>
            </div>
          </template>
          <el-table :data="recentAlerts" border stripe style="width: 100%" size="default">
            <el-table-column prop="title" :label="$t('dashboard.title')" show-overflow-tooltip sortable />
            <el-table-column prop="severity" :label="$t('dashboard.severity')" width="100" sortable>
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)" size="small" effect="dark">{{ $t(`alert.severity${row.severity?.toUpperCase()}`) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="$t('common.time')" width="160" sortable>
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
import { ref, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import dayjs from 'dayjs'
import { useI18n } from 'vue-i18n'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { graphic, init, use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { getDashboardSummary, getBackupTrends, getAlerts, getStorageUsage } from '../api/common'
import { getBackups } from '../api/backups'
import { getAllStorageCapacity } from '../api/storages'
import { getDatabases } from '../api/databases'
import { formatBytes } from '../utils/format'

use([CanvasRenderer, GridComponent, LegendComponent, LineChart, PieChart, TooltipComponent])

const stats = ref({})
const recentBackups = ref([])
const recentAlerts = ref([])
const databaseMap = ref({})
const trendChartRef = ref(null)
const { t } = useI18n()
const storageChartRef = ref(null)
const storageCapacityList = ref([])

let trendChart = null
let storageChart = null

const statCards = computed(() => [
  { label: t('dashboard.totalDatabases'), value: stats.value.database_count || 0, icon: 'Coin', color: '#00d2ff', bgColor: 'rgba(0, 210, 255, 0.1)' },
  { label: t('dashboard.totalBackups'), value: stats.value.backup_count || 0, icon: 'Upload', color: '#00e676', bgColor: 'rgba(0, 230, 118, 0.1)' },
  { label: t('dashboard.activeJobs'), value: stats.value.job_count || 0, icon: 'Clock', color: '#ffb74d', bgColor: 'rgba(255, 183, 77, 0.1)' },
  { label: t('dashboard.openAlerts'), value: stats.value.alert_count || 0, icon: 'Warning', color: '#f1416c', bgColor: 'rgba(241, 65, 108, 0.1)' },
])

const formatTime = (date) => {
  if (!date) return '-'
  return dayjs(date).format('MM-DD HH:mm')
}

const getStatusType = (status) => {
  const map = { COMPLETED: 'success', RUNNING: 'warning', FAILED: 'danger', PENDING: 'info', SUCCESS: 'success', AVAILABLE: 'success', EXPIRED: 'info', IN_PROGRESS: 'warning' }
  return map[status] || 'info'
}

const getSeverityType = (severity) => {
  const map = { CRITICAL: 'danger', HIGH: 'danger', ERROR: 'danger', MEDIUM: 'warning', WARNING: 'warning', LOW: 'info', INFO: 'info' }
  return map[severity] || 'info'
}

const initTrendChart = (data) => {
  if (!trendChartRef.value) return
  trendChart = init(trendChartRef.value)
  
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
        areaStyle: { color: new graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(0, 230, 118, 0.3)' }, { offset: 1, color: 'rgba(0, 230, 118, 0.05)' }]) },
        data: success
      },
      {
        name: 'Failed', type: 'line', smooth: true,
        lineStyle: { width: 3, color: '#f1416c' },
        areaStyle: { color: new graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(241, 65, 108, 0.3)' }, { offset: 1, color: 'rgba(241, 65, 108, 0.05)' }]) },
        data: failed
      }
    ]
  }
  trendChart.setOption(option)
}

const initStorageChart = (data) => {
  if (!storageChartRef.value) return
  storageChart = init(storageChartRef.value)
  
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
  } catch {
    stats.value = {}
  }

  try {
    const capacityRes = await getAllStorageCapacity()
    storageCapacityList.value = capacityRes.data || []
  } catch {
    storageCapacityList.value = []
  }

  try {
    const backupsRes = await getBackups({ page: 1, page_size: 5 })
    recentBackups.value = backupsRes.data.items || []
  } catch {
    recentBackups.value = []
  }

  try {
    const dbsRes = await getDatabases({ page_size: 100 })
    const dbs = dbsRes.data.items || []
    const map = {}
    dbs.forEach(db => { map[db.id] = db.name })
    databaseMap.value = map
  } catch {
    databaseMap.value = {}
  }

  try {
    const alertsRes = await getAlerts({ page: 1, page_size: 5, status: 'OPEN' })
    recentAlerts.value = alertsRes.data.items || []
  } catch {
    recentAlerts.value = []
  }

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
  padding: 16px;
}

.stat-card-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-label {
  font-size: 14px;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-color);
  line-height: 1;
}

.stat-icon-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 16px;
  color: var(--text-color);
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

.capacity-item {
  margin-bottom: 20px;
}

.capacity-item:last-child {
  margin-bottom: 0;
}

.capacity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.capacity-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-color);
}

.capacity-text {
  font-size: 13px;
  color: var(--text-color-light);
}

.capacity-percent {
  text-align: right;
  font-size: 12px;
  color: var(--text-color-light);
  margin-top: 4px;
}

.capacity-warning {
  color: #f56c6c;
  font-weight: 600;
}
</style>
