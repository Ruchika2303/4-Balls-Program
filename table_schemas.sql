-- Table 1: Project data with student and personal IDs
CREATE TABLE project_data (
    project_id VARCHAR(50) NOT NULL,
    student_id VARCHAR(50),
    personal_id VARCHAR(50),
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, student_id, personal_id, date),
    INDEX idx_date (date),
    INDEX idx_project_date (project_id, date),
    INDEX idx_student_id (student_id),
    INDEX idx_personal_id (personal_id),
    INDEX idx_updated_at (updated_at)
);

-- Table 2: Combined ID mapping data
CREATE TABLE combined_data (
    combined_id VARCHAR(50) NOT NULL,
    used_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (combined_id, used_id, date),
    INDEX idx_date (date),
    INDEX idx_combined_id (combined_id),
    INDEX idx_used_id (used_id),
    INDEX idx_updated_at (updated_at)
);

-- Result table for incremental processing
CREATE TABLE joined_result (
    project_id VARCHAR(50) NOT NULL,
    student_id VARCHAR(50),
    personal_id VARCHAR(50),
    combined_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, student_id, personal_id, combined_id, date),
    INDEX idx_date (date),
    INDEX idx_project_date (project_id, date),
    INDEX idx_updated_at (updated_at)
);

-- Tracking table for incremental processing
CREATE TABLE incremental_tracking (
    table_name VARCHAR(50) PRIMARY KEY,
    last_processed_timestamp TIMESTAMP NOT NULL,
    last_processed_date DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Initialize tracking table
INSERT INTO incremental_tracking (table_name, last_processed_timestamp, last_processed_date) 
VALUES 
    ('project_data', '1900-01-01 00:00:00', '1900-01-01'),
    ('combined_data', '1900-01-01 00:00:00', '1900-01-01'),
    ('joined_result', '1900-01-01 00:00:00', '1900-01-01')
ON DUPLICATE KEY UPDATE 
    table_name = VALUES(table_name);