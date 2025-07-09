import request from '@/utils/request'

export function getSessionList(data) {
  return request({
    url: '/api/session/grid',
    method: 'post',
    data
  })
}