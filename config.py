import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the incremental join processor"""
    
    # Database configuration
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'incremental_join_db'),
        'charset': 'utf8mb4',
        'autocommit': False,
        'use_unicode': True,
        'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'
    }
    
    # Processing configuration
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '1000'))
    MAX_BATCH_COUNT = int(os.getenv('MAX_BATCH_COUNT', '1000'))
    DATE_RANGE_DAYS = int(os.getenv('DATE_RANGE_DAYS', '360'))
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'incremental_processor.log')
    
    # Performance settings
    CONNECTION_POOL_SIZE = int(os.getenv('CONNECTION_POOL_SIZE', '5'))
    CONNECTION_TIMEOUT = int(os.getenv('CONNECTION_TIMEOUT', '30'))
    
    # Monitoring settings
    METRICS_ENABLED = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'
    ALERT_THRESHOLD_MINUTES = int(os.getenv('ALERT_THRESHOLD_MINUTES', '60'))
    
    # Maintenance settings
    AUTO_MAINTENANCE = os.getenv('AUTO_MAINTENANCE', 'true').lower() == 'true'
    ARCHIVE_OLD_DATA = os.getenv('ARCHIVE_OLD_DATA', 'false').lower() == 'true'
    ARCHIVE_DAYS = int(os.getenv('ARCHIVE_DAYS', '365'))
    
    # Retry settings
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY_SECONDS = int(os.getenv('RETRY_DELAY_SECONDS', '30'))
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate the configuration settings"""
        required_fields = ['DB_HOST', 'DB_USER', 'DB_NAME']
        
        for field in required_fields:
            if not cls.DB_CONFIG.get(field.lower().replace('db_', '')):
                print(f"Error: Required configuration field {field} is missing")
                return False
        
        if cls.BATCH_SIZE <= 0:
            print("Error: BATCH_SIZE must be greater than 0")
            return False
            
        if cls.DATE_RANGE_DAYS <= 0:
            print("Error: DATE_RANGE_DAYS must be greater than 0")
            return False
            
        return True
    
    @classmethod
    def get_db_config(cls) -> Dict[str, Any]:
        """Get database configuration dictionary"""
        return cls.DB_CONFIG.copy()
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        config_copy = cls.DB_CONFIG.copy()
        config_copy['password'] = '***' if config_copy['password'] else 'Not set'
        
        print("=== Incremental Join Processor Configuration ===")
        print(f"Database Host: {config_copy['host']}")
        print(f"Database Name: {config_copy['database']}")
        print(f"Database User: {config_copy['user']}")
        print(f"Batch Size: {cls.BATCH_SIZE}")
        print(f"Date Range Days: {cls.DATE_RANGE_DAYS}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"Metrics Enabled: {cls.METRICS_ENABLED}")
        print(f"Auto Maintenance: {cls.AUTO_MAINTENANCE}")
        print("=" * 50)