<template>
  <a-card :bordered="false">
    <div class="table-operator">
      <a-button type="primary" @click="refreshData">
        <template #icon><reload-outlined /></template>
        Refresh
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
        <template v-if="column.key === 'status'">
          <a-tag :color="record.status === 10 ? 'green' : record.status === 20 ? 'red' : record.status === 30 ? 'default' : 'default'">
            {{ crawlerStatus[record.status] }}
          </a-tag>
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

    <a-modal
      v-model:visible="visible"
      title="Edit Crawler"
      @ok="handleOk"
    >
      <a-form
        :model="formState"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-form-item label="Host Name">
          <a-input v-model:value="formState.host_name" disabled />
        </a-form-item>
        <a-form-item label="Alias" name="alias" :rules="[{ required: true, message: 'Please enter alias!' }]">
          <a-input v-model:value="formState.alias" />
        </a-form-item>
        <a-form-item label="Status">
          <a-tag :color="formState.status === 10 ? 'green' : formState.status === 20 ? 'red' : formState.status === 30 ? 'default' : 'default'">
            {{ crawlerStatus[formState.status] }}
          </a-tag>
        </a-form-item>
        <a-form-item label="Last Heartbeat">
          <a-input v-model:value="formState.last_heartbeat" disabled />
        </a-form-item>
      </a-form>
    </a-modal>
  </a-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { getCrawlerList, modifyCrawler } from '@/api/crawler'
import { crawlerStatus } from '@/data/dict'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id' },
  { title: 'Host Name', dataIndex: 'host_name', key: 'host_name' },
  { title: 'Alias', dataIndex: 'alias', key: 'alias' },
  { title: 'IP', dataIndex: 'ip', key: 'ip' },
  { title: 'OS', dataIndex: 'os', key: 'os' },
  { title: 'Agent', dataIndex: 'agent', key: 'agent' },
  { title: 'Last Heartbeat', dataIndex: 'last_heartbeat', key: 'last_heartbeat' },
  { title: 'Status', key: 'status' },
  { title: 'Action', key: 'action' }
]

const data = ref([])
const loading = ref(false)
const visible = ref(false)
const formState = ref({
  id: '',
  host_name: '',
  alias: '',
  status: '',
  last_heartbeat: ''
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

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getCrawlerList({
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

const refreshData = () => {
  pagination.value.current = 1
  fetchData()
}

const handleTableChange = (pag) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  fetchData()
}

const editItem = (record) => {
  currentItem.value = { ...record }
  formState.value = {
    id: record.id,
    host_name: record.host_name,
    alias: record.alias,
    status: record.status,
    last_heartbeat: record.last_heartbeat
  }
  visible.value = true
}

const handleOk = async () => {
  try {
    await modifyCrawler({
      id: formState.value.id,
      alias: formState.value.alias
    })
    
    // Update local data
    const index = data.value.findIndex(item => item.id === formState.value.id)
    if (index !== -1) {
      data.value[index].alias = formState.value.alias
    }
    
    visible.value = false
  } catch (error) {
    console.error('Failed to modify crawler:', error)
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