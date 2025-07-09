import request from '@/utils/request'

export function getLogList(data) {
  return request({
    url: '/api/log/grid',
    method: 'post',
    data
  })
}