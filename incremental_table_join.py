#!/usr/bin/env python3
"""
Incremental Data Processing Solution for Table Joins

This module provides an efficient way to join two tables with incremental processing,
handling only changes since the last execution to minimize redundant operations.

Tables:
- Table 1: project_id, student_id, personal_id, date
- Table 2: combined_id, used_id, date

Output: project_id, student_id, personal_id, combined_id, date
"""

import pandas as pd
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IncrementalTableJoiner:
    """
    A class to handle incremental joining of two tables with change tracking.
    """
    
    def __init__(self, db_path: str = "data_processing.db", metadata_file: str = "processing_metadata.json"):
        """
        Initialize the IncrementalTableJoiner.
        
        Args:
            db_path: Path to SQLite database for storing tables and results
            metadata_file: Path to JSON file for storing processing metadata
        """
        self.db_path = db_path
        self.metadata_file = metadata_file
        self.conn = sqlite3.connect(db_path)
        self.metadata = self._load_metadata()
        
        # Create tables if they don't exist
        self._create_tables()
    
    def _load_metadata(self) -> Dict:
        """Load processing metadata from file."""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {
            'last_execution': None,
            'table1_hash': None,
            'table2_hash': None,
            'processed_dates': []
        }
    
    def _save_metadata(self):
        """Save processing metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def _create_tables(self):
        """Create necessary tables in the database."""
        cursor = self.conn.cursor()
        
        # Table 1: Projects data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects_data (
                project_id TEXT,
                student_id TEXT,
                personal_id TEXT,
                date DATE,
                row_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project_id, student_id, personal_id, date)
            )
        """)
        
        # Table 2: Combined data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS combined_data (
                combined_id TEXT,
                used_id TEXT,
                date DATE,
                row_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (combined_id, used_id, date)
            )
        """)
        
        # Result table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS joined_results (
                project_id TEXT,
                student_id TEXT,
                personal_id TEXT,
                combined_id TEXT,
                date DATE,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project_id, student_id, personal_id, combined_id, date)
            )
        """)
        
        # Change tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS change_log (
                table_name TEXT,
                change_type TEXT,
                row_data TEXT,
                change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def _calculate_row_hash(self, row_data: Dict) -> str:
        """Calculate hash for a row to detect changes."""
        row_str = json.dumps(row_data, sort_keys=True)
        return hashlib.md5(row_str.encode()).hexdigest()
    
    def _detect_table_changes(self, table_name: str, new_data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Detect changes in a table since last execution.
        
        Returns:
            (new_rows, updated_rows, deleted_rows)
        """
        # Get existing data
        existing_data = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)
        
        if existing_data.empty:
            # First run - all data is new
            return new_data, pd.DataFrame(), pd.DataFrame()
        
        # Create comparison keys
        if table_name == 'projects_data':
            key_cols = ['project_id', 'student_id', 'personal_id', 'date']
        else:  # combined_data
            key_cols = ['combined_id', 'used_id', 'date']
        
        # Merge to find differences
        merged = new_data.merge(
            existing_data[key_cols + ['row_hash']], 
            on=key_cols, 
            how='outer', 
            suffixes=('_new', '_existing'),
            indicator=True
        )
        
        # Identify changes
        new_rows = merged[merged['_merge'] == 'left_only'].drop(['row_hash_existing', '_merge'], axis=1)
        deleted_rows = merged[merged['_merge'] == 'right_only'].drop(['row_hash_new', '_merge'], axis=1)
        
        # Updated rows (same key, different hash)
        potentially_updated = merged[merged['_merge'] == 'both']
        updated_rows = potentially_updated[
            potentially_updated['row_hash_new'] != potentially_updated['row_hash_existing']
        ].drop(['row_hash_existing', '_merge'], axis=1)
        
        return new_rows, updated_rows, deleted_rows
    
    def load_projects_data(self, data: pd.DataFrame, incremental: bool = True) -> int:
        """
        Load projects data with incremental processing.
        
        Args:
            data: DataFrame with columns [project_id, student_id, personal_id, date]
            incremental: Whether to use incremental processing
            
        Returns:
            Number of rows processed
        """
        logger.info("Loading projects data...")
        
        # Add row hash
        data['row_hash'] = data.apply(lambda row: self._calculate_row_hash(row.to_dict()), axis=1)
        
        if incremental:
            new_rows, updated_rows, deleted_rows = self._detect_table_changes('projects_data', data)
            
            # Log changes
            if not new_rows.empty:
                logger.info(f"Found {len(new_rows)} new project rows")
            if not updated_rows.empty:
                logger.info(f"Found {len(updated_rows)} updated project rows")
            if not deleted_rows.empty:
                logger.info(f"Found {len(deleted_rows)} deleted project rows")
            
            # Process only changed data
            rows_to_process = pd.concat([new_rows, updated_rows], ignore_index=True)
        else:
            # Full reload
            self.conn.execute("DELETE FROM projects_data")
            rows_to_process = data
        
        if not rows_to_process.empty:
            rows_to_process.to_sql('projects_data', self.conn, if_exists='append', index=False)
            self.conn.commit()
        
        return len(rows_to_process)
    
    def load_combined_data(self, data: pd.DataFrame, incremental: bool = True) -> int:
        """
        Load combined data with incremental processing.
        
        Args:
            data: DataFrame with columns [combined_id, used_id, date]
            incremental: Whether to use incremental processing
            
        Returns:
            Number of rows processed
        """
        logger.info("Loading combined data...")
        
        # Add row hash
        data['row_hash'] = data.apply(lambda row: self._calculate_row_hash(row.to_dict()), axis=1)
        
        if incremental:
            new_rows, updated_rows, deleted_rows = self._detect_table_changes('combined_data', data)
            
            # Log changes
            if not new_rows.empty:
                logger.info(f"Found {len(new_rows)} new combined rows")
            if not updated_rows.empty:
                logger.info(f"Found {len(updated_rows)} updated combined rows")
            if not deleted_rows.empty:
                logger.info(f"Found {len(deleted_rows)} deleted combined rows")
            
            # Process only changed data
            rows_to_process = pd.concat([new_rows, updated_rows], ignore_index=True)
        else:
            # Full reload
            self.conn.execute("DELETE FROM combined_data")
            rows_to_process = data
        
        if not rows_to_process.empty:
            rows_to_process.to_sql('combined_data', self.conn, if_exists='append', index=False)
            self.conn.commit()
        
        return len(rows_to_process)
    
    def perform_incremental_join(self, force_full_join: bool = False) -> pd.DataFrame:
        """
        Perform incremental join of the two tables.
        
        Args:
            force_full_join: Whether to force a full join regardless of changes
            
        Returns:
            DataFrame with joined results
        """
        logger.info("Performing incremental join...")
        
        # Determine date range to process
        if force_full_join or self.metadata.get('last_execution') is None:
            # Full join
            logger.info("Performing full join...")
            date_filter = ""
        else:
            # Incremental join - only process dates that might have changed
            last_execution = datetime.fromisoformat(self.metadata['last_execution'])
            date_filter = f"WHERE p.date >= '{last_execution.date()}' OR c.date >= '{last_execution.date()}'"
            logger.info(f"Performing incremental join since {last_execution.date()}...")
        
        # SQL query to join tables
        query = f"""
        SELECT DISTINCT
            p.project_id,
            p.student_id,
            p.personal_id,
            c.combined_id,
            p.date
        FROM projects_data p
        INNER JOIN combined_data c ON (
            (c.combined_id = p.student_id OR c.combined_id = p.personal_id)
            AND c.date = p.date
        )
        {date_filter}
        """
        
        # Execute join
        result = pd.read_sql_query(query, self.conn)
        
        if not result.empty:
            # Clear existing results for the processed dates if incremental
            if not force_full_join and date_filter:
                processed_dates = result['date'].unique()
                date_list = "', '".join(processed_dates)
                self.conn.execute(f"DELETE FROM joined_results WHERE date IN ('{date_list}')")
            elif force_full_join:
                self.conn.execute("DELETE FROM joined_results")
            
            # Insert new results
            result.to_sql('joined_results', self.conn, if_exists='append', index=False)
            self.conn.commit()
            
            logger.info(f"Successfully joined {len(result)} rows")
        else:
            logger.info("No new data to join")
        
        # Update metadata
        self.metadata['last_execution'] = datetime.now().isoformat()
        self._save_metadata()
        
        return result
    
    def get_results(self, date_filter: Optional[str] = None) -> pd.DataFrame:
        """
        Get joined results with optional date filtering.
        
        Args:
            date_filter: Optional date filter (e.g., '>= 2024-01-01')
            
        Returns:
            DataFrame with joined results
        """
        query = "SELECT * FROM joined_results"
        if date_filter:
            query += f" WHERE date {date_filter}"
        query += " ORDER BY date DESC, project_id, student_id"
        
        return pd.read_sql_query(query, self.conn)
    
    def get_processing_stats(self) -> Dict:
        """Get statistics about the data processing."""
        stats = {}
        
        # Count records in each table
        stats['projects_data_count'] = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM projects_data", self.conn
        ).iloc[0]['count']
        
        stats['combined_data_count'] = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM combined_data", self.conn
        ).iloc[0]['count']
        
        stats['joined_results_count'] = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM joined_results", self.conn
        ).iloc[0]['count']
        
        # Date ranges
        stats['projects_date_range'] = pd.read_sql_query(
            "SELECT MIN(date) as min_date, MAX(date) as max_date FROM projects_data", self.conn
        ).iloc[0].to_dict()
        
        stats['combined_date_range'] = pd.read_sql_query(
            "SELECT MIN(date) as min_date, MAX(date) as max_date FROM combined_data", self.conn
        ).iloc[0].to_dict()
        
        # Last execution info
        stats['last_execution'] = self.metadata.get('last_execution')
        
        return stats
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def create_sample_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create sample data for testing the incremental join functionality.
    
    Returns:
        Tuple of (projects_data, combined_data)
    """
    # Generate date range for last 360 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=360)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Sample projects data
    projects_data = []
    project_ids = ['PROJ001', 'PROJ002', 'PROJ003', 'PROJ004']
    student_ids = ['STU001', 'STU002', 'STU003', 'STU004', 'STU005']
    personal_ids = ['PER001', 'PER002', 'PER003', 'PER004', 'PER005']
    
    for date in date_range:
        for project_id in project_ids:
            # Each project has 2-3 student/personal combinations per day
            for i in range(2):
                projects_data.append({
                    'project_id': project_id,
                    'student_id': student_ids[i % len(student_ids)],
                    'personal_id': personal_ids[i % len(personal_ids)],
                    'date': date.strftime('%Y-%m-%d')
                })
    
    # Sample combined data
    combined_data = []
    all_ids = student_ids + personal_ids
    used_id_names = ['student_id', 'personal_id']
    
    for date in date_range:
        for combined_id in all_ids[:6]:  # Use subset of IDs
            combined_data.append({
                'combined_id': combined_id,
                'used_id': used_id_names[hash(combined_id) % 2],
                'date': date.strftime('%Y-%m-%d')
            })
    
    return pd.DataFrame(projects_data), pd.DataFrame(combined_data)


if __name__ == "__main__":
    # Example usage
    logger.info("Starting incremental table join processing...")
    
    # Initialize the joiner
    joiner = IncrementalTableJoiner()
    
    try:
        # Create sample data for demonstration
        projects_df, combined_df = create_sample_data()
        
        # Load data incrementally
        projects_processed = joiner.load_projects_data(projects_df, incremental=True)
        combined_processed = joiner.load_combined_data(combined_df, incremental=True)
        
        logger.info(f"Processed {projects_processed} project rows and {combined_processed} combined rows")
        
        # Perform incremental join
        results = joiner.perform_incremental_join()
        
        # Get statistics
        stats = joiner.get_processing_stats()
        logger.info(f"Processing complete. Statistics: {stats}")
        
        # Show sample results
        if not results.empty:
            logger.info(f"Sample of joined results:\n{results.head(10)}")
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        raise
    finally:
        joiner.close()