<template>
  <div class="audit">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ $t('audit.title') }}</span>
          <div class="header-filters">
            <el-input v-model="searchAction" :placeholder="$t('audit.searchAction')" clearable style="width: 180px" @input="applyFilters" />
            <el-select v-model="filterResult" :placeholder="$t('audit.resultFilter')" clearable style="width: 120px" @change="applyFilters">
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failure" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="logs" v-loading="loading" border stripe style="width: 100%" size="default" empty-text="No data available">
        <el-table-column prop="id" label="ID" width="80" sortable />
        <el-table-column prop="action" :label="$t('audit.action')" width="180" sortable />
        <el-table-column prop="actor_user_id" :label="$t('audit.actor')" width="100" sortable />
        <el-table-column prop="resource_type" :label="$t('audit.resourceType')" width="120" sortable />
        <el-table-column prop="result" :label="$t('audit.result')" width="100" sortable>
          <template #default="{ row }">
            <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" :label="$t('audit.ip')" width="140" sortable />
        <el-table-column prop="reason" :label="$t('audit.reason')" sortable />
        <el-table-column prop="created_at" :label="$t('common.time')" width="180" sortable>
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
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
import dayjs from 'dayjs'
import { getAuditLogs } from '../api/common'

const logs = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchAction = ref('')
const filterResult = ref('')

const formatTime = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (searchAction.value) {
      params.action = searchAction.value
    }
    if (filterResult.value) {
      params.result = filterResult.value
    }

    const response = await getAuditLogs(params)
    logs.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error) {
    console.error('Failed to fetch audit logs:', error)
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  page.value = 1
  fetchData()
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
