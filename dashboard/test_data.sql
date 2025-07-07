-- Use the database
USE `dashboard`;

-- Insert sample data into crawler_info
INSERT INTO `crawler_info` (`alias`, `max_browser_count`) VALUES
('Crawler Node 1', 5),
('Crawler Node 2', 3),
('Test Crawler', 10),
('Production Crawler', 8),
('Backup Crawler Node', 2);

-- Insert sample data into crawler_status
INSERT INTO `crawler_status` (`crawler_id`, `host_name`, `ip`, `os`, `agent`, `last_heartbeat`, `status`) VALUES
(1, 'node1-server', '192.168.1.101', 'Linux', 'pAgent/1.0.0', '2023-06-15 10:00:00', 10),
(2, 'node2-server', '192.168.1.102', 'Windows', 'pAgent/1.0.0', '2023-06-15 10:01:23', 20),
(3, 'test-node', '10.0.0.101', 'Linux', 'pAgent/1.0.0', '2023-06-15 09:45:30', 10),
(4, 'prod-node1', '172.16.0.10', 'Linux', 'pAgent/1.0.0', '2023-06-15 11:20:15', 10),
(5, 'backup-node', '192.168.2.100', 'Windows', 'pAgent/1.0.0', '2023-06-14 22:30:45', 30);

-- Insert sample data into crawler_session
INSERT INTO `crawler_session` (`crawler_id`, `session`, `init_time`, `url`, `title`, `destroy_time`) VALUES
(1, 'sess_abc123', '2023-06-15 09:30:00', 'https://example.com/page1', 'Example Page 1', NULL),
(1, 'sess_def456', '2023-06-15 10:15:00', 'https://example.com/page2', 'Example Page 2', '2023-06-15 11:00:00'),
(2, 'sess_ghi789', '2023-06-15 08:45:00', 'https://test.com/home', 'Test Homepage', '2023-06-15 09:30:00'),
(3, 'sess_jkl012', '2023-06-15 10:00:00', 'https://api.example.com/data', 'API Data Endpoint', NULL),
(4, 'sess_mno345', '2023-06-15 11:00:00', 'https://prod.example.com', 'Production Site', NULL);

-- Insert sample data into api_log
INSERT INTO `api_log` (`crawler_session_id`, `api`, `request_time`, `response_time`, `status_code`) VALUES
(1, '/api/data/get', '2023-06-15 09:35:00', '2023-06-15 09:35:02', 200),
(1, '/api/data/post', '2023-06-15 09:40:00', '2023-06-15 09:40:01', 201),
(2, '/api/user/info', '2023-06-15 10:20:00', '2023-06-15 10:20:03', 200),
(3, '/api/test/run', '2023-06-15 08:50:00', '2023-06-15 08:50:45', 500),
(4, '/api/data/fetch', '2023-06-15 10:05:00', NULL, NULL),
(5, '/api/prod/metrics', '2023-06-15 11:05:00', '2023-06-15 11:05:10', 200);
