<template>
  <a-card :bordered="false">
    <div class="table-operator">
      <a-input v-model:value="searchKeyword" placeholder="Search..." style="width:200px;margin-right:8px;" @pressEnter="handleSearch" />
      <a-button type="primary" @click="handleSearch">
        <template #icon><search-outlined /></template>
        Search
      </a-button>
      <a-button @click="handleReset" style="margin-left: 8px;">
        Reset
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="data"
      :pagination="pagination"
      :loading="loading"
      @change="handleTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'server'">
          {{ getServerDisplay(record) }}
        </template>
        <template v-else-if="column.key === 'crawler_server'">
          {{ getCrawlerName(record.crawler_id) }}
        </template>
      </template>
    </a-table>
  </a-card>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import { getSessions, getCrawlerList } from '@/api/crawler'
import { useRoute } from 'vue-router'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id' },
  { title: 'Server', key: 'server' },
  { title: 'Session', dataIndex: 'session', key: 'session' },
  { title: 'URL', dataIndex: 'url', key: 'url' },
  { title: 'Init Time', dataIndex: 'init_time', key: 'init_time' },
  { title: 'Destroy Time', dataIndex: 'destroy_time', key: 'destroy_time' }
]

const data = ref([])
const crawlers = ref([])
const loading = ref(false)

const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50'],
  showTotal: total => `Total ${total} items`
})
const searchKeyword = ref('')
const route = useRoute()
const crawlerId = ref(route.query.crawler_id || '')

const getCrawlerName = (id) => {
  const crawler = crawlers.value.find(c => c.id === id)
  return crawler ? `${crawler.alias} (${crawler.host_name})` : 'Unknown'
}

const getServerDisplay = (record) => {
  if (record.host_name && record.host_name.trim()) return record.host_name
  if (record.alias && record.alias.trim()) return record.alias
  if (record.ip && record.ip.trim()) return record.ip
  return ''
}

const fetchCrawlers = async () => {
  const res = await getCrawlerList({ page: 1, page_size: 100 })
  crawlers.value = res.data.items
}

const fetchData = async () => {
  loading.value = true
  try {
    // Build parameter object
    const params = {
      pagination: {
        page_num: pagination.value.current,
        page_size: pagination.value.pageSize
      },
      keyword: searchKeyword.value,
      crawler_id: crawlerId.value
    }
    // Filter out empty parameters
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
    const res = await getSessions(params)
    data.value = res.rows
    pagination.value.total = res.total
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.value.current = 1
  fetchData()
}

const handleReset = () => {
  searchKeyword.value = ''
  pagination.value.current = 1
  fetchData()
}

const handleTableChange = (pag) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  fetchData()
}

onMounted(() => {
  fetchData()
})

// Watch for route changes to update crawlerId and refetch data
watch(() => route.query.crawler_id, (newId) => {
  crawlerId.value = newId
  fetchData()
})
</script>

<style scoped>
.table-operator {
  margin-bottom: 16px;
}
</style>