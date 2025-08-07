#!/usr/bin/env python3
"""
Example usage of the IncrementalTableJoiner

This script demonstrates how to use the incremental table joining functionality
with your specific data requirements.
"""

import pandas as pd
from datetime import datetime, timedelta
from incremental_table_join import IncrementalTableJoiner

def load_your_data():
    """
    Replace this function with your actual data loading logic.
    
    This should return two DataFrames:
    1. projects_data: DataFrame with columns [project_id, student_id, personal_id, date]
    2. combined_data: DataFrame with columns [combined_id, used_id, date]
    """
    
    # Example: Loading from CSV files
    # projects_df = pd.read_csv('projects_data.csv')
    # combined_df = pd.read_csv('combined_data.csv')
    
    # Example: Loading from database
    # import sqlite3
    # conn = sqlite3.connect('your_database.db')
    # projects_df = pd.read_sql_query("SELECT project_id, student_id, personal_id, date FROM projects_table", conn)
    # combined_df = pd.read_sql_query("SELECT combined_id, used_id, date FROM combined_table", conn)
    # conn.close()
    
    # For this example, we'll create sample data
    return create_sample_data()

def create_sample_data():
    """Create realistic sample data for demonstration."""
    
    # Generate date range for last 30 days (smaller for example)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Projects data
    projects_data = []
    project_ids = ['PROJ_ALPHA', 'PROJ_BETA', 'PROJ_GAMMA']
    student_ids = ['STU_001', 'STU_002', 'STU_003', 'STU_004']
    personal_ids = ['PER_001', 'PER_002', 'PER_003', 'PER_004']
    
    for date in date_range:
        for project_id in project_ids:
            for i in range(2):  # 2 combinations per project per day
                projects_data.append({
                    'project_id': project_id,
                    'student_id': student_ids[i % len(student_ids)],
                    'personal_id': personal_ids[i % len(personal_ids)],
                    'date': date.strftime('%Y-%m-%d')
                })
    
    # Combined data - some IDs match, some don't
    combined_data = []
    all_ids = student_ids + personal_ids
    used_id_names = ['student_id', 'personal_id']
    
    for date in date_range:
        for combined_id in all_ids[:5]:  # Use most IDs for matches
            combined_data.append({
                'combined_id': combined_id,
                'used_id': used_id_names[hash(combined_id) % 2],
                'date': date.strftime('%Y-%m-%d')
            })
    
    return pd.DataFrame(projects_data), pd.DataFrame(combined_data)

def main():
    """Main execution function."""
    print("🚀 Starting incremental table join processing...")
    
    # Initialize the joiner
    joiner = IncrementalTableJoiner(
        db_path="/workspace/my_data_processing.db",
        metadata_file="/workspace/my_processing_metadata.json"
    )
    
    try:
        # Load your data
        print("📊 Loading data...")
        projects_df, combined_df = load_your_data()
        
        print(f"Projects data shape: {projects_df.shape}")
        print(f"Combined data shape: {combined_df.shape}")
        
        # First run - load all data
        print("\n📥 Loading projects data...")
        projects_processed = joiner.load_projects_data(projects_df, incremental=True)
        
        print("📥 Loading combined data...")
        combined_processed = joiner.load_combined_data(combined_df, incremental=True)
        
        print(f"✅ Processed {projects_processed} project rows and {combined_processed} combined rows")
        
        # Perform the join
        print("\n🔗 Performing incremental join...")
        results = joiner.perform_incremental_join()
        
        # Display results
        print(f"\n📋 Join Results Summary:")
        print(f"Total joined rows: {len(results)}")
        
        if not results.empty:
            print(f"\nSample of joined results:")
            print(results.head(10).to_string(index=False))
            
            # Show unique counts
            print(f"\nUnique projects: {results['project_id'].nunique()}")
            print(f"Unique students: {results['student_id'].nunique()}")
            print(f"Unique personal IDs: {results['personal_id'].nunique()}")
            print(f"Unique combined IDs: {results['combined_id'].nunique()}")
            print(f"Date range: {results['date'].min()} to {results['date'].max()}")
        
        # Get processing statistics
        print(f"\n📊 Processing Statistics:")
        stats = joiner.get_processing_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Simulate incremental processing
        print(f"\n🔄 Simulating incremental update...")
        
        # Add some new data (simulate new day)
        new_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        new_projects = pd.DataFrame([
            {'project_id': 'PROJ_ALPHA', 'student_id': 'STU_001', 'personal_id': 'PER_001', 'date': new_date},
            {'project_id': 'PROJ_BETA', 'student_id': 'STU_002', 'personal_id': 'PER_002', 'date': new_date}
        ])
        new_combined = pd.DataFrame([
            {'combined_id': 'STU_001', 'used_id': 'student_id', 'date': new_date},
            {'combined_id': 'PER_002', 'used_id': 'personal_id', 'date': new_date}
        ])
        
        # Process incremental changes
        projects_inc = joiner.load_projects_data(new_projects, incremental=True)
        combined_inc = joiner.load_combined_data(new_combined, incremental=True)
        
        print(f"Added {projects_inc} new project rows and {combined_inc} new combined rows")
        
        # Perform incremental join
        incremental_results = joiner.perform_incremental_join()
        print(f"Incremental join produced {len(incremental_results)} new rows")
        
        # Final statistics
        final_stats = joiner.get_processing_stats()
        print(f"\n📊 Final Statistics:")
        print(f"  Total joined results: {final_stats['joined_results_count']}")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        raise
    finally:
        joiner.close()
        print("\n✅ Processing complete!")

if __name__ == "__main__":
    main()