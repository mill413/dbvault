<template>
  <div class="audit">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
          <div class="header-filters">
            <el-input v-model="searchAction" placeholder="搜索操作" clearable style="width: 180px" />
            <el-select v-model="filterResult" placeholder="结果筛选" clearable style="width: 120px">
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failure" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="filteredLogs" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="action" label="操作" width="180" />
        <el-table-column prop="actor_user_id" label="操作人" width="100" />
        <el-table-column prop="resource_type" label="资源类型" width="120" />
        <el-table-column prop="result" label="结果" width="100">
          <template #default="{ row }">
            <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">{{ row.result }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column prop="reason" label="原因" />
        <el-table-column label="时间" width="180">
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
import { ref, reactive, onMounted, computed } from 'vue'
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

const filteredLogs = computed(() => {
  let result = logs.value
  if (searchAction.value) {
    const keyword = searchAction.value.toLowerCase()
    result = result.filter((l) => (l.action || '').toLowerCase().includes(keyword))
  }
  if (filterResult.value) {
    result = result.filter((l) => l.result === filterResult.value)
  }
  return result
})

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
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
