-- Create the database
CREATE DATABASE IF NOT EXISTS `dashboard` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_0900_ai_ci;

-- Use the database
USE `dashboard`;

-- Create crawler_info table
CREATE TABLE IF NOT EXISTS `crawler_info` (
  `id` int NOT NULL AUTO_INCREMENT,
  `alias` varchar(50) DEFAULT NULL,
  `max_browser_count` int DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create crawler_status table
CREATE TABLE IF NOT EXISTS `crawler_status` (
  `id` int NOT NULL AUTO_INCREMENT,
  `crawler_id` int NOT NULL,
  `host_name` varchar(50) DEFAULT NULL,
  `ip` varchar(50) DEFAULT NULL,
  `os` varchar(50) DEFAULT NULL,
  `agent` varchar(50) DEFAULT NULL,
  `last_heartbeat` datetime DEFAULT NULL,
  `status` int DEFAULT NULL COMMENT '10:online, 20:offline, 30:shutdown',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `crawler_id_UNIQUE` (`crawler_id`),
  CONSTRAINT `fk_crawler_status_info` FOREIGN KEY (`crawler_id`) REFERENCES `crawler_info` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create crawler_session table
CREATE TABLE IF NOT EXISTS `crawler_session` (
  `id` int NOT NULL AUTO_INCREMENT,
  `crawler_id` int NOT NULL,
  `session` varchar(50) DEFAULT NULL,
  `init_time` datetime DEFAULT NULL,
  `url` varchar(500) DEFAULT NULL,
  `title` varchar(50) DEFAULT NULL,
  `destroy_time` datetime DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_crawler_session_info` FOREIGN KEY (`crawler_id`) REFERENCES `crawler_info` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create api_log table
CREATE TABLE IF NOT EXISTS `api_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `crawler_session_id` int NOT NULL,
  `api` varchar(500) DEFAULT NULL,
  `request_time` datetime DEFAULT NULL,
  `response_time` datetime DEFAULT NULL,
  `status_code` int DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_api_log_session` FOREIGN KEY (`crawler_session_id`) REFERENCES `crawler_session` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create indexes for better performance
CREATE INDEX `idx_crawler_status_status` ON `crawler_status` (`status`);
CREATE INDEX `idx_crawler_status_heartbeat` ON `crawler_status` (`last_heartbeat`);
CREATE INDEX `idx_crawler_session_session` ON `crawler_session` (`session`);
CREATE INDEX `idx_crawler_session_init` ON `crawler_session` (`init_time`);
CREATE INDEX `idx_api_log_request` ON `api_log` (`request_time`);
CREATE INDEX `idx_api_log_status` ON `api_log` (`status_code`);
