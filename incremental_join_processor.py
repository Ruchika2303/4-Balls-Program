import mysql.connector
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import pandas as pd

class IncrementalJoinProcessor:
    """
    Handles incremental data processing for joining project_data and combined_data tables.
    Only processes changes since the last execution to minimize redundant operations.
    """
    
    def __init__(self, db_config: Dict[str, str]):
        """
        Initialize the processor with database configuration.
        
        Args:
            db_config: Dictionary containing database connection parameters
                      (host, user, password, database)
        """
        self.db_config = db_config
        self.connection = None
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the processor."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def connect(self):
        """Establish database connection."""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            self.logger.info("Database connection established")
        except mysql.connector.Error as e:
            self.logger.error(f"Error connecting to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.info("Database connection closed")
    
    def get_last_processed_info(self, table_name: str) -> Tuple[datetime, Optional[str]]:
        """
        Get the last processed timestamp and date for a specific table.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            Tuple of (last_processed_timestamp, last_processed_date)
        """
        cursor = self.connection.cursor()
        query = """
            SELECT last_processed_timestamp, last_processed_date 
            FROM incremental_tracking 
            WHERE table_name = %s
        """
        cursor.execute(query, (table_name,))
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return result[0], result[1]
        else:
            # First time processing
            return datetime(1900, 1, 1), None
    
    def update_last_processed_info(self, table_name: str, timestamp: datetime, date: str):
        """
        Update the last processed timestamp and date for a table.
        
        Args:
            table_name: Name of the table
            timestamp: Last processed timestamp
            date: Last processed date
        """
        cursor = self.connection.cursor()
        query = """
            UPDATE incremental_tracking 
            SET last_processed_timestamp = %s, last_processed_date = %s, updated_at = NOW()
            WHERE table_name = %s
        """
        cursor.execute(query, (timestamp, date, table_name))
        self.connection.commit()
        cursor.close()
        self.logger.info(f"Updated tracking info for {table_name}: {timestamp}, {date}")
    
    def get_changed_data(self, table_name: str, last_timestamp: datetime) -> List[Tuple]:
        """
        Get data that has changed since the last processed timestamp.
        
        Args:
            table_name: Name of the table to check
            last_timestamp: Last processed timestamp
            
        Returns:
            List of tuples containing changed data
        """
        cursor = self.connection.cursor()
        
        if table_name == 'project_data':
            query = """
                SELECT project_id, student_id, personal_id, date, updated_at
                FROM project_data 
                WHERE updated_at > %s
                ORDER BY updated_at
            """
        elif table_name == 'combined_data':
            query = """
                SELECT combined_id, used_id, date, updated_at
                FROM combined_data 
                WHERE updated_at > %s
                ORDER BY updated_at
            """
        else:
            raise ValueError(f"Unknown table name: {table_name}")
        
        cursor.execute(query, (last_timestamp,))
        results = cursor.fetchall()
        cursor.close()
        
        return results
    
    def perform_incremental_join(self) -> int:
        """
        Perform incremental join operation, processing only changed data.
        
        Returns:
            Number of records processed
        """
        self.logger.info("Starting incremental join process")
        
        # Get last processed timestamps
        project_last_ts, _ = self.get_last_processed_info('project_data')
        combined_last_ts, _ = self.get_last_processed_info('combined_data')
        
        # Get changed data from both tables
        project_changes = self.get_changed_data('project_data', project_last_ts)
        combined_changes = self.get_changed_data('combined_data', combined_last_ts)
        
        self.logger.info(f"Found {len(project_changes)} changes in project_data")
        self.logger.info(f"Found {len(combined_changes)} changes in combined_data")
        
        if not project_changes and not combined_changes:
            self.logger.info("No changes detected, skipping processing")
            return 0
        
        # Process the joins
        processed_count = 0
        
        # If there are changes in project_data, we need to join with existing combined_data
        if project_changes:
            processed_count += self._process_project_changes(project_changes)
        
        # If there are changes in combined_data, we need to join with existing project_data
        if combined_changes:
            processed_count += self._process_combined_changes(combined_changes)
        
        # Update tracking information
        current_time = datetime.now()
        if project_changes:
            latest_project_ts = max(change[4] for change in project_changes)  # updated_at column
            self.update_last_processed_info('project_data', latest_project_ts, current_time.date())
        
        if combined_changes:
            latest_combined_ts = max(change[3] for change in combined_changes)  # updated_at column
            self.update_last_processed_info('combined_data', latest_combined_ts, current_time.date())
        
        self.logger.info(f"Incremental join completed. Processed {processed_count} records")
        return processed_count
    
    def _process_project_changes(self, project_changes: List[Tuple]) -> int:
        """
        Process changes in project_data table.
        
        Args:
            project_changes: List of changed project records
            
        Returns:
            Number of records processed
        """
        if not project_changes:
            return 0
        
        cursor = self.connection.cursor()
        processed_count = 0
        
        for project_record in project_changes:
            project_id, student_id, personal_id, date, _ = project_record
            
            # Find matching combined_data records where combined_id matches student_id or personal_id
            join_query = """
                SELECT DISTINCT c.combined_id, c.used_id, c.date
                FROM combined_data c
                WHERE c.date = %s 
                AND (c.combined_id = %s OR c.combined_id = %s)
            """
            
            cursor.execute(join_query, (date, student_id, personal_id))
            matching_combined = cursor.fetchall()
            
            # Insert/Update results
            for combined_record in matching_combined:
                combined_id, used_id, combined_date = combined_record
                
                # Use REPLACE to handle duplicates
                insert_query = """
                    REPLACE INTO joined_result 
                    (project_id, student_id, personal_id, combined_id, date)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                cursor.execute(insert_query, (
                    project_id, student_id, personal_id, combined_id, date
                ))
                processed_count += 1
        
        self.connection.commit()
        cursor.close()
        return processed_count
    
    def _process_combined_changes(self, combined_changes: List[Tuple]) -> int:
        """
        Process changes in combined_data table.
        
        Args:
            combined_changes: List of changed combined records
            
        Returns:
            Number of records processed
        """
        if not combined_changes:
            return 0
        
        cursor = self.connection.cursor()
        processed_count = 0
        
        for combined_record in combined_changes:
            combined_id, used_id, date, _ = combined_record
            
            # Find matching project_data records where student_id or personal_id matches combined_id
            join_query = """
                SELECT DISTINCT p.project_id, p.student_id, p.personal_id, p.date
                FROM project_data p
                WHERE p.date = %s 
                AND (p.student_id = %s OR p.personal_id = %s)
            """
            
            cursor.execute(join_query, (date, combined_id, combined_id))
            matching_projects = cursor.fetchall()
            
            # Insert/Update results
            for project_record in matching_projects:
                project_id, student_id, personal_id, project_date = project_record
                
                # Use REPLACE to handle duplicates
                insert_query = """
                    REPLACE INTO joined_result 
                    (project_id, student_id, personal_id, combined_id, date)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                cursor.execute(insert_query, (
                    project_id, student_id, personal_id, combined_id, date
                ))
                processed_count += 1
        
        self.connection.commit()
        cursor.close()
        return processed_count
    
    def full_refresh(self, date_range_days: int = 360) -> int:
        """
        Perform a full refresh of the joined data for the specified date range.
        Use this for initial load or when incremental processing is not possible.
        
        Args:
            date_range_days: Number of days to process (default: 360)
            
        Returns:
            Number of records processed
        """
        self.logger.info(f"Starting full refresh for last {date_range_days} days")
        
        cursor = self.connection.cursor()
        
        # Clear existing results for the date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=date_range_days)
        
        delete_query = """
            DELETE FROM joined_result 
            WHERE date >= %s AND date <= %s
        """
        cursor.execute(delete_query, (start_date, end_date))
        
        # Perform full join
        join_query = """
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
            WHERE p.date >= %s AND p.date <= %s
        """
        
        cursor.execute(join_query, (start_date, end_date))
        processed_count = cursor.rowcount
        
        self.connection.commit()
        cursor.close()
        
        # Update tracking information
        current_time = datetime.now()
        self.update_last_processed_info('project_data', current_time, current_time.date())
        self.update_last_processed_info('combined_data', current_time, current_time.date())
        
        self.logger.info(f"Full refresh completed. Processed {processed_count} records")
        return processed_count
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about the tables.
        
        Returns:
            Dictionary with table statistics
        """
        cursor = self.connection.cursor()
        stats = {}
        
        tables = ['project_data', 'combined_data', 'joined_result']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]
        
        cursor.close()
        return stats

# Example usage and configuration
def main():
    # Database configuration
    db_config = {
        'host': 'localhost',
        'user': 'your_username',
        'password': 'your_password',
        'database': 'your_database',
        'charset': 'utf8mb4'
    }
    
    # Initialize processor
    processor = IncrementalJoinProcessor(db_config)
    
    try:
        processor.connect()
        
        # Get current statistics
        stats = processor.get_statistics()
        print("Current statistics:", stats)
        
        # Perform incremental processing
        processed_count = processor.perform_incremental_join()
        print(f"Processed {processed_count} records incrementally")
        
        # Get updated statistics
        updated_stats = processor.get_statistics()
        print("Updated statistics:", updated_stats)
        
    except Exception as e:
        print(f"Error during processing: {e}")
    finally:
        processor.disconnect()

if __name__ == "__main__":
    main()