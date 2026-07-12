<template>
  <div class="database-browser">
    <el-card shadow="never">
      <template #header>
        <div class="browser-header">
          <span>{{ $t('browser.title') }}</span>
          <div class="selectors">
            <el-select v-model="databaseId" :placeholder="$t('browser.instance')" filterable @change="loadCatalogs">
              <el-option v-for="item in databases" :key="item.id" :label="`${item.name} (${item.db_type})`" :value="item.id" />
            </el-select>
            <el-select v-model="catalog" :placeholder="$t('browser.catalog')" filterable :disabled="!databaseId" @change="loadTables">
              <el-option v-for="item in catalogs" :key="item.name" :label="item.name" :value="item.name" />
            </el-select>
          </div>
        </div>
      </template>

      <el-container class="browser-content">
        <el-aside width="280px" class="table-list">
          <el-input v-model="tableFilter" :placeholder="$t('browser.filterTables')" clearable />
          <el-scrollbar>
            <el-menu :default-active="selectedKey" @select="selectTable">
              <el-menu-item v-for="item in filteredTables" :key="tableKey(item)" :index="tableKey(item)">
                <el-icon><Grid /></el-icon>
                <span>{{ item.schema_name }}.{{ item.name }}</span>
              </el-menu-item>
            </el-menu>
            <el-empty v-if="catalog && !loadingTables && !filteredTables.length" :description="$t('browser.noTables')" :image-size="64" />
          </el-scrollbar>
        </el-aside>

        <el-main class="preview">
          <el-empty v-if="!selectedTable" :description="$t('browser.selectTable')" />
          <el-tabs v-else v-model="activeTab">
            <el-tab-pane :label="$t('browser.data')" name="data">
              <el-table :data="displayRows" v-loading="loadingRows" border height="520" empty-text="No data">
                <el-table-column v-for="column in rowData.columns" :key="column" :prop="column" :label="column" min-width="140" show-overflow-tooltip>
                  <template #default="scope"><span :class="{ 'null-value': scope.row[column] === null }">{{ scope.row[column] === null ? 'NULL' : scope.row[column] }}</span></template>
                </el-table-column>
              </el-table>
              <el-pagination v-if="rowData.total" v-model:current-page="page" v-model:page-size="pageSize"
                :total="rowData.total" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next"
                @current-change="loadRows" @size-change="onPageSizeChange" />
            </el-tab-pane>
            <el-tab-pane :label="$t('browser.structure')" name="structure">
              <el-table :data="columns" v-loading="loadingColumns" border>
                <el-table-column prop="name" :label="$t('browser.column')" />
                <el-table-column prop="data_type" :label="$t('browser.type')" />
                <el-table-column prop="nullable" :label="$t('browser.nullable')" width="100">
                  <template #default="scope">{{ scope.row.nullable ? $t('common.yes') : $t('common.no') }}</template>
                </el-table-column>
                <el-table-column prop="primary_key" :label="$t('browser.primaryKey')" width="110">
                  <template #default="scope"><el-tag v-if="scope.row.primary_key" size="small">PK</el-tag></template>
                </el-table-column>
                <el-table-column prop="default" :label="$t('browser.defaultValue')" />
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </el-main>
      </el-container>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDatabases } from '../api/databases'
import { getCatalogs, getColumns, getRows, getTables } from '../api/browser'

const databases = ref([])
const databaseId = ref(null)
const catalogs = ref([])
const catalog = ref('')
const tables = ref([])
const tableFilter = ref('')
const selectedKey = ref('')
const selectedTable = ref(null)
const activeTab = ref('data')
const columns = ref([])
const rowData = ref({ columns: [], rows: [], total: 0 })
const page = ref(1)
const pageSize = ref(20)
const loadingTables = ref(false)
const loadingRows = ref(false)
const loadingColumns = ref(false)

const tableKey = (item) => `${item.schema_name}\u0000${item.name}`
const filteredTables = computed(() => {
  const keyword = tableFilter.value.toLowerCase()
  return tables.value.filter((item) => `${item.schema_name}.${item.name}`.toLowerCase().includes(keyword))
})
const displayRows = computed(() => rowData.value.rows.map((values) =>
  Object.fromEntries(rowData.value.columns.map((name, index) => [name, values[index]]))))

const showError = (error) => ElMessage.error(error?.response?.data?.error?.message || error.message)

async function loadCatalogs() {
  catalog.value = ''
  catalogs.value = []
  tables.value = []
  selectedTable.value = null
  if (!databaseId.value) return
  try {
    catalogs.value = (await getCatalogs(databaseId.value)).data
    const instance = databases.value.find((item) => item.id === databaseId.value)
    catalog.value = catalogs.value.find((item) => item.name === instance?.database_name)?.name || catalogs.value[0]?.name || ''
    if (catalog.value) await loadTables()
  } catch (error) { showError(error) }
}

async function loadTables() {
  selectedTable.value = null
  selectedKey.value = ''
  tables.value = []
  if (!catalog.value) return
  loadingTables.value = true
  try { tables.value = (await getTables(databaseId.value, catalog.value)).data }
  catch (error) { showError(error) }
  finally { loadingTables.value = false }
}

async function selectTable(key) {
  selectedTable.value = tables.value.find((item) => tableKey(item) === key)
  selectedKey.value = key
  page.value = 1
  await Promise.all([loadColumns(), loadRows()])
}

const tableParams = () => ({ catalog: catalog.value, schema: selectedTable.value.schema_name, table: selectedTable.value.name })
async function loadColumns() {
  loadingColumns.value = true
  try { columns.value = (await getColumns(databaseId.value, tableParams())).data }
  catch (error) { showError(error) }
  finally { loadingColumns.value = false }
}
async function loadRows() {
  loadingRows.value = true
  try { rowData.value = (await getRows(databaseId.value, { ...tableParams(), page: page.value, page_size: pageSize.value })).data }
  catch (error) { showError(error) }
  finally { loadingRows.value = false }
}
function onPageSizeChange() { page.value = 1; loadRows() }

onMounted(async () => {
  try { databases.value = (await getDatabases({ page_size: 100 })).data.items || [] }
  catch (error) { showError(error) }
})
</script>

<style scoped>
.browser-header, .selectors { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.selectors .el-select { width: 240px; }
.browser-content { min-height: 620px; }
.table-list { border-right: 1px solid var(--border-color); padding-right: 12px; }
.table-list .el-scrollbar { height: 570px; margin-top: 12px; }
.table-list .el-menu { border-right: none; }
.preview { padding: 0 0 0 20px; overflow: hidden; }
.el-pagination { margin-top: 16px; justify-content: flex-end; }
.null-value { color: var(--el-text-color-placeholder); font-style: italic; }
@media (max-width: 900px) { .selectors { flex-wrap: wrap; } .selectors .el-select { width: 180px; } .table-list { width: 220px !important; } }
</style>
