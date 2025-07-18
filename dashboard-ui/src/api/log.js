import request from '@/utils/request'

export function getLogList(data) {
  return request({
    url: '/api/log/grid',
    method: 'post',
    data
  })
}

export function deleteLogs(data) {
  return request({
    url: '/api/log/delete',
    method: 'post',
    data
  })
}