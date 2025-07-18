<template>
  <a-card :bordered="false">
    <div class="table-operator">
      <a-input v-model:value="keyword" placeholder="UUID/IP/Host Name/Alias" style="width: 280px; margin-right: 8px;" @pressEnter="handleSearch" />
      <a-button type="primary" @click="handleSearch">
        <template #icon><search-outlined /></template>
        Search
      </a-button>
      <a-button @click="handleReset" style="margin-left: 8px;">Reset</a-button>
      <a-button type="danger" :disabled="!selectedRowKeys.length" @click="handleBatchDelete" style="margin-left: 8px;">
        <template #icon><delete-outlined /></template>
        Delete Selected
      </a-button>
    </div>
  
    <a-table
      :columns="columns"
      :data-source="data"
      :pagination="pagination"
      :loading="loading"
      @change="handleTableChange"
      :row-selection="rowSelection"
      :row-key="'id'"
    >
      <template #headerCell="{ column }">
        <template v-if="column.key === 'ip'">
          <div>
            <div>External IP</div>
            <div>Internal IP</div>
          </div>
        </template>
        <template v-else-if="column.key === 'host'">
          <div>
            <div>Host Name</div>
            <div>Alias</div>
          </div>
        </template>
        <template v-else-if="column.key === 'os'">
          <div>
            <div>OS</div>
            <div>Agent</div>
          </div>
        </template>
        <template v-else-if="column.key === 'usage'">
          <div>
            <div>CPU Usage</div>
            <div>Memory Usage</div>
          </div>
        </template>
        <template v-else-if="column.key === 'status'">
          <div>
            <div>Status</div>
            <div>Last Heartbeat</div>
          </div>
        </template>
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <div>
            <a-tag :color="record.status === 10 ? 'green' : record.status === 20 ? 'red' : record.status === 30 ? 'default' : 'default'">
              {{ crawlerStatus[record.status] }}
            </a-tag>
            <div>{{ record.last_heartbeat }}</div>
          </div>
        </template>
        <template v-else-if="column.key === 'ip'">
          <div>{{ record.external_ip }}</div>
          <div>{{ record.internal_ip }}</div>
        </template>
        <template v-else-if="column.key === 'host'">
          <div>{{ record.host_name }}</div>
          <div>{{ record.alias }}</div>
        </template>
        <template v-else-if="column.key === 'os'">
          <div>{{ record.os }}</div>
          <div>{{ record.agent }}</div>
        </template>
        <template v-else-if="column.key === 'usage'">
          <div>{{ record.cpu_usage }}%</div>
          <div>{{ record.memory_usage }}%</div>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a @click="editItem(record)">Edit</a>
            <a-divider type="vertical" />
            <router-link :to="`/session?crawler_id=${record.id}`">Session</router-link>
            <a-divider type="vertical" />
            <router-link :to="`/log?crawler_id=${record.id}`">Log</router-link>
          </a-space>
        </template>
      </template>
    </a-table>
  </a-card>

  <a-modal
    v-model:visible="visible"
    title="Edit Crawler"
    @ok="handleOk"
  >
    <a-form
      :model="formState"
      :label-col="{ span: 8 }"
      :wrapper-col="{ span: 14 }"
    >
      <a-form-item label="Host Name">
        <a-input v-model:value="formState.host_name" disabled />
      </a-form-item>
      <a-form-item label="Alias" name="alias" :rules="[{ required: true, message: 'Please enter alias!' }]">
        <a-input v-model:value="formState.alias" />
      </a-form-item>
      <a-form-item label="Max Browser Count" name="max_browser_count">
        <a-input-number v-model:value="formState.max_browser_count" :min="1" :max="100" style="width: 100%" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ReloadOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { getCrawlerList, modifyCrawler, deleteCrawlers } from '@/api/crawler'
import { crawlerStatus } from '@/data/dict'

const keyword = ref('')

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id' },
  { title: 'UUID', dataIndex: 'uuid', key: 'uuid' },
  { title: 'IP', key: 'ip' },
  { title: 'Host', key: 'host' },
  { title: 'OS', key: 'os' },
  { title: 'Usage', key: 'usage' },
  { title: 'Status', key: 'status' },
  { title: 'Max Browser Count', dataIndex: 'max_browser_count', key: 'max_browser_count' },
  { title: 'Action', key: 'action' }
]

const data = ref([])
const loading = ref(false)
const visible = ref(false)
const formState = ref({
  id: '',
  host_name: '',
  alias: '',
  max_browser_count: null
})
const currentItem = ref({})
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50'],
  showTotal: total => `Total ${total} items`
})

const selectedRowKeys = ref([])
const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys) => {
    selectedRowKeys.value = keys
  }
}))

const handleSearch = () => {
  pagination.value.current = 1
  fetchData()
}

const handleReset = () => {
  keyword.value = ''
  pagination.value.current = 1
  fetchData()
}

const editItem = (record) => {
  currentItem.value = { ...record }
  formState.value = {
    id: record.id,
    host_name: record.host_name,
    alias: record.alias,
    max_browser_count: record.max_browser_count || null
  }
  visible.value = true
}

const handleOk = async () => {
  try {
    await modifyCrawler({
      id: formState.value.id,
      alias: formState.value.alias,
      max_browser_count: formState.value.max_browser_count
    })
    
    // Update local data
    const index = data.value.findIndex(item => item.id === formState.value.id)
    if (index !== -1) {
      data.value[index].alias = formState.value.alias
      data.value[index].max_browser_count = formState.value.max_browser_count
    }
    
    visible.value = false
  } catch (error) {
    console.error('Failed to modify crawler:', error)
  }
}

const handleBatchDelete = async () => {
  if (!selectedRowKeys.value.length) return
  try {
    await deleteCrawlers({ ids: selectedRowKeys.value })
    selectedRowKeys.value = []
    fetchData()
  } catch (error) {
    console.error('Failed to delete crawlers:', error)
  }
}

const handleTableChange = (pag) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  fetchData()
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getCrawlerList({
      keyword: keyword.value,
      pagination: {
        page_num: pagination.value.current,
        page_size: pagination.value.pageSize
      }
    })
    data.value = res.rows
    pagination.value.total = res.total
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.table-operator {
  margin-bottom: 16px;
}
</style>