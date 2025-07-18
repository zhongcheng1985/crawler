import request from '@/utils/request'

export function getCrawlerList(data) {
  return request({
    url: '/api/crawler/grid',
    method: 'post',
    data
  })
}

export function modifyCrawler(data) {
  return request({
    url: '/api/crawler/modify',
    method: 'post',
    data
  })
}

export function getSessions(data) {
  return request({
    url: '/api/session/grid',
    method: 'post',
    data
  })
}

export function getCrawlerRequestList(data) {
  return request({
    url: '/api/crawler_request/grid',
    method: 'post',
    data
  })
}

export function deleteCrawlers(data) {
  return request({
    url: '/api/crawler/delete',
    method: 'post',
    data
  })
}