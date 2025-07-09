export default [
    /** ==================== crawler ==================== */
    {
      url: '/api/crawler/grid',
      method: 'post',
      response() {
        return {
          'total': 3,
          'rows': [
            {'id': 101, host_name: 'DESKTOP-V08AOH1',alias: 'Crawler_1',last_heartbeat_time: '2025-07-04 13:30:25',status: 10},
            {'id': 102, host_name: 'DESKTOP-V08AOH2',alias: 'Crawler_2',last_heartbeat_time: '2025-07-04 13:30:25',status: 20},
          ]
        }
      }
    }
  ]