-- =====================================================
-- PERFORMANCE OPTIMIZATION RECOMMENDATIONS
-- For handling large datasets with 360 days of data efficiently
-- =====================================================

-- =====================================================
-- 1. PARTITIONING STRATEGY
-- Partition tables by date for better performance with 360-day data
-- =====================================================

-- Partition project_data table by date (monthly partitions)
ALTER TABLE project_data PARTITION BY RANGE (TO_DAYS(date)) (
    PARTITION p202401 VALUES LESS THAN (TO_DAYS('2024-02-01')),
    PARTITION p202402 VALUES LESS THAN (TO_DAYS('2024-03-01')),
    PARTITION p202403 VALUES LESS THAN (TO_DAYS('2024-04-01')),
    PARTITION p202404 VALUES LESS THAN (TO_DAYS('2024-05-01')),
    PARTITION p202405 VALUES LESS THAN (TO_DAYS('2024-06-01')),
    PARTITION p202406 VALUES LESS THAN (TO_DAYS('2024-07-01')),
    PARTITION p202407 VALUES LESS THAN (TO_DAYS('2024-08-01')),
    PARTITION p202408 VALUES LESS THAN (TO_DAYS('2024-09-01')),
    PARTITION p202409 VALUES LESS THAN (TO_DAYS('2024-10-01')),
    PARTITION p202410 VALUES LESS THAN (TO_DAYS('2024-11-01')),
    PARTITION p202411 VALUES LESS THAN (TO_DAYS('2024-12-01')),
    PARTITION p202412 VALUES LESS THAN (TO_DAYS('2025-01-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- Partition combined_data table by date (monthly partitions)
ALTER TABLE combined_data PARTITION BY RANGE (TO_DAYS(date)) (
    PARTITION p202401 VALUES LESS THAN (TO_DAYS('2024-02-01')),
    PARTITION p202402 VALUES LESS THAN (TO_DAYS('2024-03-01')),
    PARTITION p202403 VALUES LESS THAN (TO_DAYS('2024-04-01')),
    PARTITION p202404 VALUES LESS THAN (TO_DAYS('2024-05-01')),
    PARTITION p202405 VALUES LESS THAN (TO_DAYS('2024-06-01')),
    PARTITION p202406 VALUES LESS THAN (TO_DAYS('2024-07-01')),
    PARTITION p202407 VALUES LESS THAN (TO_DAYS('2024-08-01')),
    PARTITION p202408 VALUES LESS THAN (TO_DAYS('2024-09-01')),
    PARTITION p202409 VALUES LESS THAN (TO_DAYS('2024-10-01')),
    PARTITION p202410 VALUES LESS THAN (TO_DAYS('2024-11-01')),
    PARTITION p202411 VALUES LESS THAN (TO_DAYS('2024-12-01')),
    PARTITION p202412 VALUES LESS THAN (TO_DAYS('2025-01-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- Partition joined_result table by date (monthly partitions)
ALTER TABLE joined_result PARTITION BY RANGE (TO_DAYS(date)) (
    PARTITION p202401 VALUES LESS THAN (TO_DAYS('2024-02-01')),
    PARTITION p202402 VALUES LESS THAN (TO_DAYS('2024-03-01')),
    PARTITION p202403 VALUES LESS THAN (TO_DAYS('2024-04-01')),
    PARTITION p202404 VALUES LESS THAN (TO_DAYS('2024-05-01')),
    PARTITION p202405 VALUES LESS THAN (TO_DAYS('2024-06-01')),
    PARTITION p202406 VALUES LESS THAN (TO_DAYS('2024-07-01')),
    PARTITION p202407 VALUES LESS THAN (TO_DAYS('2024-08-01')),
    PARTITION p202408 VALUES LESS THAN (TO_DAYS('2024-09-01')),
    PARTITION p202409 VALUES LESS THAN (TO_DAYS('2024-10-01')),
    PARTITION p202410 VALUES LESS THAN (TO_DAYS('2024-11-01')),
    PARTITION p202411 VALUES LESS THAN (TO_DAYS('2024-12-01')),
    PARTITION p202412 VALUES LESS THAN (TO_DAYS('2025-01-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- =====================================================
-- 2. ADVANCED INDEXING STRATEGIES
-- Create composite indexes for optimized join performance
-- =====================================================

-- Composite indexes for project_data table
CREATE INDEX idx_project_date_student ON project_data (date, student_id, project_id);
CREATE INDEX idx_project_date_personal ON project_data (date, personal_id, project_id);
CREATE INDEX idx_project_updated_date ON project_data (updated_at, date);

-- Composite indexes for combined_data table
CREATE INDEX idx_combined_date_id ON combined_data (date, combined_id, used_id);
CREATE INDEX idx_combined_updated_date ON combined_data (updated_at, date);

-- Covering indexes to avoid table lookups
CREATE INDEX idx_project_covering ON project_data (date, student_id, personal_id) 
    INCLUDE (project_id, updated_at);
CREATE INDEX idx_combined_covering ON combined_data (date, combined_id) 
    INCLUDE (used_id, updated_at);

-- =====================================================
-- 3. MATERIALIZED VIEWS FOR COMMON QUERIES
-- Pre-compute frequently accessed data combinations
-- =====================================================

-- Materialized view for daily aggregated data
CREATE TABLE daily_join_summary AS
SELECT 
    date,
    COUNT(*) as total_joins,
    COUNT(DISTINCT project_id) as unique_projects,
    COUNT(DISTINCT combined_id) as unique_combined_ids,
    COUNT(DISTINCT student_id) as unique_students,
    COUNT(DISTINCT personal_id) as unique_personal_ids
FROM joined_result
GROUP BY date;

-- Index for daily summary
CREATE INDEX idx_daily_summary_date ON daily_join_summary (date);

-- Refresh procedure for daily summary
DELIMITER $$
CREATE PROCEDURE RefreshDailySummary(IN target_date DATE)
BEGIN
    DELETE FROM daily_join_summary WHERE date = target_date;
    
    INSERT INTO daily_join_summary 
    SELECT 
        date,
        COUNT(*) as total_joins,
        COUNT(DISTINCT project_id) as unique_projects,
        COUNT(DISTINCT combined_id) as unique_combined_ids,
        COUNT(DISTINCT student_id) as unique_students,
        COUNT(DISTINCT personal_id) as unique_personal_ids
    FROM joined_result
    WHERE date = target_date
    GROUP BY date;
END$$
DELIMITER ;

-- =====================================================
-- 4. BATCH PROCESSING OPTIMIZATION
-- Optimize for processing large batches efficiently
-- =====================================================

-- Create staging tables for batch loading
CREATE TABLE project_data_staging LIKE project_data;
CREATE TABLE combined_data_staging LIKE combined_data;

-- Disable foreign key checks for faster batch loading
-- Use this during bulk data loading operations
-- SET FOREIGN_KEY_CHECKS = 0;
-- ... perform bulk loading ...
-- SET FOREIGN_KEY_CHECKS = 1;

-- Batch insert procedure with error handling
DELIMITER $$
CREATE PROCEDURE BatchProcessIncrementalJoin(IN batch_size INT DEFAULT 1000)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE batch_count INT DEFAULT 0;
    DECLARE total_processed INT DEFAULT 0;
    
    DECLARE CONTINUE HANDLER FOR SQLEXCEPTION 
    BEGIN
        ROLLBACK;
        GET DIAGNOSTICS CONDITION 1
            @errno = MYSQL_ERRNO, @text = MESSAGE_TEXT;
        INSERT INTO error_log (error_message, error_time) 
        VALUES (CONCAT('Batch processing error: ', @text), NOW());
    END;
    
    -- Process in batches to avoid memory issues
    WHILE batch_count < 1000 DO  -- Limit to prevent infinite loops
        START TRANSACTION;
        
        -- Process one batch
        INSERT INTO joined_result (project_id, student_id, personal_id, combined_id, date)
        SELECT DISTINCT 
            p.project_id,
            p.student_id,
            p.personal_id,
            c.combined_id,
            p.date
        FROM project_data p
        INNER JOIN combined_data c ON (
            p.date = c.date 
            AND (p.student_id = c.combined_id OR p.personal_id = c.combined_id)
        )
        WHERE p.updated_at > (
            SELECT last_processed_timestamp 
            FROM incremental_tracking 
            WHERE table_name = 'project_data'
        )
        LIMIT batch_size
        ON DUPLICATE KEY UPDATE updated_at = NOW();
        
        SET total_processed = total_processed + ROW_COUNT();
        
        COMMIT;
        
        SET batch_count = batch_count + 1;
        
        -- Break if no more records to process
        IF ROW_COUNT() = 0 THEN
            LEAVE;
        END IF;
    END WHILE;
    
    SELECT CONCAT('Processed ', total_processed, ' records in ', batch_count, ' batches') as result;
END$$
DELIMITER ;

-- =====================================================
-- 5. MEMORY AND CONNECTION OPTIMIZATION
-- MySQL configuration recommendations
-- =====================================================

/*
Recommended MySQL configuration settings for large-scale processing:

# Memory settings
innodb_buffer_pool_size = 70% of available RAM
innodb_log_file_size = 256M
innodb_log_buffer_size = 64M
innodb_flush_log_at_trx_commit = 2  # For better performance, less durability

# Connection settings
max_connections = 200
thread_cache_size = 32
table_open_cache = 4096
table_definition_cache = 2048

# Query optimization
query_cache_size = 0  # Disable query cache for high write workloads
tmp_table_size = 64M
max_heap_table_size = 64M

# InnoDB specific
innodb_io_capacity = 2000  # Adjust based on storage type (SSD)
innodb_read_io_threads = 8
innodb_write_io_threads = 8
innodb_flush_method = O_DIRECT
*/

-- =====================================================
-- 6. MONITORING AND STATISTICS
-- Create tables and procedures for performance monitoring
-- =====================================================

-- Performance monitoring table
CREATE TABLE performance_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4),
    metric_date DATE,
    metric_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_metric_date (metric_date),
    INDEX idx_metric_name (metric_name)
);

-- Procedure to collect performance metrics
DELIMITER $$
CREATE PROCEDURE CollectPerformanceMetrics()
BEGIN
    DECLARE current_date DATE DEFAULT CURDATE();
    
    -- Record table sizes
    INSERT INTO performance_metrics (metric_name, metric_value, metric_date)
    SELECT 'project_data_count', COUNT(*), current_date FROM project_data;
    
    INSERT INTO performance_metrics (metric_name, metric_value, metric_date)
    SELECT 'combined_data_count', COUNT(*), current_date FROM combined_data;
    
    INSERT INTO performance_metrics (metric_name, metric_value, metric_date)
    SELECT 'joined_result_count', COUNT(*), current_date FROM joined_result;
    
    -- Record processing lag (time since last update)
    INSERT INTO performance_metrics (metric_name, metric_value, metric_date)
    SELECT 
        'processing_lag_minutes', 
        TIMESTAMPDIFF(MINUTE, MAX(last_processed_timestamp), NOW()),
        current_date
    FROM incremental_tracking;
    
    -- Record daily join success rate
    INSERT INTO performance_metrics (metric_name, metric_value, metric_date)
    SELECT 
        'daily_join_success_rate',
        (COUNT(DISTINCT CONCAT(project_id, '-', combined_id, '-', date)) * 100.0) / 
        (SELECT COUNT(*) FROM project_data WHERE date = current_date),
        current_date
    FROM joined_result 
    WHERE date = current_date;
END$$
DELIMITER ;

-- =====================================================
-- 7. AUTOMATED MAINTENANCE PROCEDURES
-- Keep the system running efficiently over time
-- =====================================================

-- Daily maintenance procedure
DELIMITER $$
CREATE PROCEDURE DailyMaintenance()
BEGIN
    -- Collect performance metrics
    CALL CollectPerformanceMetrics();
    
    -- Update table statistics
    ANALYZE TABLE project_data, combined_data, joined_result;
    
    -- Optimize tables (use sparingly, can be time-consuming)
    -- OPTIMIZE TABLE project_data, combined_data, joined_result;
    
    -- Clean up old error logs
    DELETE FROM error_log WHERE error_time < DATE_SUB(NOW(), INTERVAL 30 DAY);
    
    -- Archive old data if needed (uncomment if archiving is required)
    -- INSERT INTO joined_result_archive 
    -- SELECT * FROM joined_result 
    -- WHERE date < DATE_SUB(CURDATE(), INTERVAL 365 DAY);
    
    -- DELETE FROM joined_result 
    -- WHERE date < DATE_SUB(CURDATE(), INTERVAL 365 DAY);
END$$
DELIMITER ;

-- Create error log table
CREATE TABLE IF NOT EXISTS error_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    error_message TEXT,
    error_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_error_time (error_time)
);

-- =====================================================
-- 8. QUERY OPTIMIZATION TIPS
-- Best practices for query performance
-- =====================================================

/*
Query Optimization Tips:

1. Always use date ranges in WHERE clauses to leverage partitioning
2. Use LIMIT clauses when testing queries
3. Prefer INNER JOIN over WHERE EXISTS when possible
4. Use covering indexes to avoid table lookups
5. Consider using batch processing for large updates
6. Monitor slow query log and optimize accordingly
7. Use EXPLAIN to understand query execution plans
8. Avoid SELECT * - specify only needed columns
9. Use prepared statements for repeated queries
10. Consider read replicas for heavy reporting workloads
*/