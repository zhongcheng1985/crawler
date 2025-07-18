import request from '@/utils/request'

export function getSessionList(data) {
  return request({
    url: '/api/session/grid',
    method: 'post',
    data
  })
}

export function deleteSessions(data) {
  return request({
    url: '/api/session/delete',
    method: 'post',
    data
  })
}