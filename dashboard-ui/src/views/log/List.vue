<template>
  <a-card :bordered="false">
    <div class="table-operator">
      <a-input v-model:value="keyword" placeholder="UUID/IP/Host Name/Alias/Session/Url" style="width:280px;margin-right:8px;" @pressEnter="handleSearch" />
      <a-button type="primary" @click="handleSearch">
        <template #icon><search-outlined /></template>
        Search
      </a-button>
      <a-button @click="handleReset" style="margin-left: 8px;">
        Reset
      </a-button>
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
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'crawler'">
          <a-tooltip placement="top" :overlay-inner-style="{ whiteSpace: 'pre-line' }">
            <template #title>
              <div v-html="getServerTooltip(record)"></div>
            </template>
            <span>{{ getServerDisplay(record) }}</span>
          </a-tooltip>
        </template>
        <template v-else-if="column.key === 'status_code'">
          <a-tag :color="getStatusCodeColor(record.status_code)">
            {{ record.status_code }}
          </a-tag>
        </template>
        <template v-else>
          {{ record[column.dataIndex] }}
        </template>
      </template>
    </a-table>
  </a-card>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { DeleteOutlined } from '@ant-design/icons-vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import { getLogList } from '@/api/log'
import { deleteLogs } from '@/api/log'
import { useRoute } from 'vue-router'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id' },
  { title: 'Crawler', key: 'crawler' },
  { title: 'Session', dataIndex: 'uuid', key: 'uuid' },
  { title: 'URL', dataIndex: 'url', key: 'url' },
  { title: 'Request Time', dataIndex: 'request_time', key: 'request_time' },
  { title: 'Response Time', dataIndex: 'response_time', key: 'response_time' },
  { title: 'Status Code', dataIndex: 'status_code', key: 'status_code' }
]

const data = ref([])
const loading = ref(false)
const keyword = ref('')
const route = useRoute()
const crawlerId = ref(route.query.crawler_id || '')
const sessionId = ref(route.query.session_id || '')

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

const getStatusCodeColor = (code) => {
  if (code >= 200 && code < 300) return 'green' // Success
  if (code >= 300 && code < 400) return 'blue'  // Redirection
  if (code >= 400 && code < 500) return 'orange' // Client Error
  if (code >= 500 && code < 600) return 'red' // Server Error
  return 'default' // Others
}

const getServerDisplay = (record) => {
  if (record.crawler_uuid && record.crawler_uuid.trim()) return record.crawler_uuid
  return ''
}

const getServerTooltip = (record) => {
  const tooltipParts = []
  
  if (record.host_name && record.host_name.trim()) {
    tooltipParts.push(`Host: ${record.host_name}`)
  }
  
  if (record.alias && record.alias.trim()) {
    tooltipParts.push(`Alias: ${record.alias}`)
  }
  
  if (record.external_ip && record.external_ip.trim()) {
    tooltipParts.push(`External IP: ${record.external_ip}`)
  }

  if (record.internal_ip && record.internal_ip.trim()) {
    tooltipParts.push(`Internal IP: ${record.internal_ip}`)
  }
  
  return tooltipParts.length > 0 ? tooltipParts.join('<br>') : 'No server information'
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      pagination: {
        page_num: pagination.value.current,
        page_size: pagination.value.pageSize
      },
      keyword: keyword.value,
      crawler_id: crawlerId.value,
      session_id: sessionId.value
    }
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })
    if (params.pagination) {
      Object.keys(params.pagination).forEach(key => {
        if (
          params.pagination[key] === '' ||
          params.pagination[key] === null ||
          params.pagination[key] === undefined
        ) {
          delete params.pagination[key]
        }
      })
    }
    const res = await getLogList(params)
    const rows = res?.rows || res?.data?.rows || [];
    const total = res?.total ?? res?.data?.total ?? 0;
    data.value = rows
    pagination.value.total = total
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.value.current = 1
  fetchData()
}

const handleReset = () => {
  keyword.value = ''
  pagination.value.current = 1
  fetchData()
}

const handleTableChange = (pag) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  fetchData()
}

const handleBatchDelete = async () => {
  if (!selectedRowKeys.value.length) return
  try {
    await deleteLogs({ ids: selectedRowKeys.value })
    selectedRowKeys.value = []
    fetchData()
  } catch (error) {
    console.error('Failed to delete logs:', error)
  }
}

onMounted(() => {
  fetchData()
})

// Watch for route changes to update crawlerId and sessionId and refetch data
watch(() => route.query.crawler_id, (newId) => {
  crawlerId.value = newId
  fetchData()
})
watch(() => route.query.session_id, (newId) => {
  sessionId.value = newId
  fetchData()
})
</script>

<style scoped>
.table-operator {
  margin-bottom: 16px;
}
</style>