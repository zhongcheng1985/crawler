import axios from 'axios'
import { message } from 'ant-design-vue'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/',
  timeout: 5000
})

service.interceptors.request.use(
  config => {
    return config
  },
  error => {
    console.log(error) // for debug
    Promise.reject(error)
  }
)

service.interceptors.response.use(
  response => {
    const res = response.data
    // if (res.code !== 200) {
    //   message.error(res.message || 'Error')
    //   return Promise.reject(new Error(res.message || 'Error'))
    // }
    return res
  },
  error => {
    message.error(error.message)
    return Promise.reject(error)
  }
)

export default service