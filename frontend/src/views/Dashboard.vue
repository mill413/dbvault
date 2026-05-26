<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #409eff">
              <el-icon :size="32"><Coin /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.database_count || 0 }}</div>
              <div class="stat-label">数据库实例</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon :size="32"><Upload /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.backup_count || 0 }}</div>
              <div class="stat-label">备份总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #e6a23c">
              <el-icon :size="32"><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.job_count || 0 }}</div>
              <div class="stat-label">定时任务</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #f56c6c">
              <el-icon :size="32"><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.alert_count || 0 }}</div>
              <div class="stat-label">告警数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近备份</span>
            </div>
          </template>
          <el-table :data="recentBackups" style="width: 100%" size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="database.name" label="数据库" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="180" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近告警</span>
            </div>
          </template>
          <el-table :data="recentAlerts" style="width: 100%" size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="severity" label="级别" width="100">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'OPEN' ? 'danger' : 'success'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDashboardSummary, getBackupTrends, getAlerts } from '../api/common'
import { getBackups } from '../api/backups'

const stats = ref({})
const recentBackups = ref([])
const recentAlerts = ref([])

const getStatusType = (status) => {
  const map = { COMPLETED: 'success', RUNNING: 'warning', FAILED: 'danger', PENDING: 'info', SUCCESS: 'success' }
  return map[status] || 'info'
}

const getSeverityType = (severity) => {
  const map = { CRITICAL: 'danger', HIGH: 'danger', MEDIUM: 'warning', LOW: 'info' }
  return map[severity] || 'info'
}

onMounted(async () => {
  try {
    const summaryRes = await getDashboardSummary()
    stats.value = summaryRes.data || {}

    const backupsRes = await getBackups({ page: 1, page_size: 5 })
    recentBackups.value = backupsRes.data.items || []

    try {
      const alertsRes = await getAlerts({ page: 1, page_size: 5 })
      recentAlerts.value = alertsRes.data.items || []
    } catch {
      recentAlerts.value = []
    }
  } catch (error) {
    console.error('Failed to load dashboard:', error)
  }
})
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
</style>
