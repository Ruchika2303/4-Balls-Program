-- =====================================================
-- INCREMENTAL JOIN QUERIES
-- These queries handle only changed data since last execution
-- =====================================================

-- Query 1: Main incremental join for new/updated project_data records
-- This joins changed project records with existing combined_data
CREATE OR REPLACE VIEW incremental_project_join AS
SELECT DISTINCT 
    p.project_id,
    p.student_id,
    p.personal_id,
    c.combined_id,
    p.date,
    NOW() as processed_at
FROM project_data p
INNER JOIN combined_data c ON (
    p.date = c.date 
    AND (p.student_id = c.combined_id OR p.personal_id = c.combined_id)
)
WHERE p.updated_at > (
    SELECT last_processed_timestamp 
    FROM incremental_tracking 
    WHERE table_name = 'project_data'
);

-- Query 2: Main incremental join for new/updated combined_data records
-- This joins changed combined records with existing project_data
CREATE OR REPLACE VIEW incremental_combined_join AS
SELECT DISTINCT 
    p.project_id,
    p.student_id,
    p.personal_id,
    c.combined_id,
    c.date,
    NOW() as processed_at
FROM combined_data c
INNER JOIN project_data p ON (
    c.date = p.date 
    AND (c.combined_id = p.student_id OR c.combined_id = p.personal_id)
)
WHERE c.updated_at > (
    SELECT last_processed_timestamp 
    FROM incremental_tracking 
    WHERE table_name = 'combined_data'
);

-- Query 3: Combined incremental processing
-- Process all incremental changes in one go
INSERT INTO joined_result (project_id, student_id, personal_id, combined_id, date)
SELECT * FROM (
    SELECT project_id, student_id, personal_id, combined_id, date
    FROM incremental_project_join
    UNION
    SELECT project_id, student_id, personal_id, combined_id, date
    FROM incremental_combined_join
) AS combined_incremental
ON DUPLICATE KEY UPDATE 
    updated_at = NOW();

-- =====================================================
-- FULL REFRESH QUERIES
-- These queries process all data for the specified date range
-- =====================================================

-- Query 4: Full join for specified date range (default: last 360 days)
-- This is used for initial load or full refresh
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
WHERE p.date >= CURDATE() - INTERVAL 360 DAY
    AND p.date <= CURDATE()
ON DUPLICATE KEY UPDATE 
    updated_at = NOW();

-- =====================================================
-- OPTIMIZATION QUERIES
-- These queries help identify performance bottlenecks
-- =====================================================

-- Query 5: Analyze data distribution for optimization
SELECT 
    'project_data' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT project_id) as unique_projects,
    COUNT(DISTINCT student_id) as unique_students,
    COUNT(DISTINCT personal_id) as unique_personal_ids,
    COUNT(DISTINCT date) as unique_dates,
    MIN(date) as earliest_date,
    MAX(date) as latest_date
FROM project_data
UNION ALL
SELECT 
    'combined_data' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT combined_id) as unique_combined_ids,
    COUNT(DISTINCT used_id) as unique_used_ids,
    0 as unique_personal_ids,
    COUNT(DISTINCT date) as unique_dates,
    MIN(date) as earliest_date,
    MAX(date) as latest_date
FROM combined_data;

-- Query 6: Check for potential performance issues
-- Identify dates with unusually high record counts
SELECT 
    date,
    COUNT(*) as record_count,
    CASE 
        WHEN COUNT(*) > 10000 THEN 'HIGH'
        WHEN COUNT(*) > 1000 THEN 'MEDIUM'
        ELSE 'LOW'
    END as volume_category
FROM (
    SELECT date FROM project_data
    UNION ALL
    SELECT date FROM combined_data
) AS all_dates
GROUP BY date
ORDER BY record_count DESC
LIMIT 20;

-- =====================================================
-- MAINTENANCE QUERIES
-- These queries help maintain data quality and performance
-- =====================================================

-- Query 7: Clean up old tracking data (optional)
DELETE FROM incremental_tracking 
WHERE updated_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
    AND table_name NOT IN ('project_data', 'combined_data', 'joined_result');

-- Query 8: Archive old joined results (optional)
-- Move data older than 1 year to archive table
CREATE TABLE IF NOT EXISTS joined_result_archive LIKE joined_result;

INSERT INTO joined_result_archive 
SELECT * FROM joined_result 
WHERE date < DATE_SUB(CURDATE(), INTERVAL 365 DAY);

-- Query 9: Validate data integrity
-- Check for orphaned records or missing joins
SELECT 
    'Missing combined_data matches' as issue_type,
    COUNT(*) as issue_count
FROM project_data p
LEFT JOIN combined_data c ON (
    p.date = c.date 
    AND (p.student_id = c.combined_id OR p.personal_id = c.combined_id)
)
WHERE c.combined_id IS NULL
    AND p.date >= CURDATE() - INTERVAL 7 DAY

UNION ALL

SELECT 
    'Missing project_data matches' as issue_type,
    COUNT(*) as issue_count
FROM combined_data c
LEFT JOIN project_data p ON (
    c.date = p.date 
    AND (c.combined_id = p.student_id OR c.combined_id = p.personal_id)
)
WHERE p.project_id IS NULL
    AND c.date >= CURDATE() - INTERVAL 7 DAY;

-- =====================================================
-- MONITORING QUERIES
-- These queries help monitor the incremental processing
-- =====================================================

-- Query 10: Check incremental processing status
SELECT 
    table_name,
    last_processed_timestamp,
    last_processed_date,
    TIMESTAMPDIFF(MINUTE, last_processed_timestamp, NOW()) as minutes_since_last_process,
    updated_at
FROM incremental_tracking
ORDER BY last_processed_timestamp DESC;

-- Query 11: Daily processing summary
SELECT 
    DATE(created_at) as processing_date,
    COUNT(*) as records_processed,
    COUNT(DISTINCT project_id) as unique_projects,
    COUNT(DISTINCT combined_id) as unique_combined_ids
FROM joined_result
WHERE created_at >= CURDATE() - INTERVAL 7 DAY
GROUP BY DATE(created_at)
ORDER BY processing_date DESC;