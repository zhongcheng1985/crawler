-- Create the database
CREATE DATABASE IF NOT EXISTS `dashboard` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_0900_ai_ci;

-- Use the database
USE `dashboard`;

-- Create crawler_info table
CREATE TABLE IF NOT EXISTS `crawler_info` (
  `id` int NOT NULL AUTO_INCREMENT,
  `uuid` varchar(50) DEFAULT NULL,
  `host_name` varchar(50) DEFAULT NULL,
  `internal_ip` varchar(50) DEFAULT NULL,
  `external_ip` varchar(50) DEFAULT NULL,
  `os` varchar(50) DEFAULT NULL,
  `agent` varchar(50) DEFAULT NULL,
  `last_heartbeat` datetime DEFAULT NULL,
  `status` int DEFAULT NULL COMMENT '10:online, 20:offline, 30:shutdown',
  `cpu_usage` float DEFAULT NULL,
  `memory_usage` float DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create crawler_setting table
CREATE TABLE IF NOT EXISTS `crawler_setting` (
  `id` int NOT NULL AUTO_INCREMENT,
  `crawler_id` int DEFAULT NULL,
  `alias` varchar(50) DEFAULT NULL,
  `max_browser_count` int DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_crawler_setting_info` (`crawler_id`),
  CONSTRAINT `fk_crawler_setting_info` FOREIGN KEY (`crawler_id`) REFERENCES `crawler_info` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create crawler_session table
CREATE TABLE IF NOT EXISTS `crawler_session` (
  `id` int NOT NULL AUTO_INCREMENT,
  `crawler_id` int DEFAULT NULL,
  `uuid` varchar(50) DEFAULT NULL,
  `init_time` datetime DEFAULT NULL,
  `url` varchar(500) DEFAULT NULL,
  `destroy_time` datetime DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_crawler_session_info` FOREIGN KEY (`crawler_id`) REFERENCES `crawler_info` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create crawler_log table
CREATE TABLE IF NOT EXISTS `crawler_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `crawler_session_id` int DEFAULT NULL,
  `url` varchar(500) DEFAULT NULL,
  `request_time` datetime DEFAULT NULL,
  `response_time` datetime DEFAULT NULL,
  `status_code` int DEFAULT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_crawler_log_session` FOREIGN KEY (`crawler_session_id`) REFERENCES `crawler_session` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
