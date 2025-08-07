#!/usr/bin/env python3
"""
Simple test of the incremental table join logic without external dependencies.
This demonstrates the core concepts and SQL join logic.
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta

def create_test_tables(conn):
    """Create test tables with sample data."""
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects_data (
            project_id TEXT,
            student_id TEXT,
            personal_id TEXT,
            date DATE,
            row_hash TEXT,
            PRIMARY KEY (project_id, student_id, personal_id, date)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS combined_data (
            combined_id TEXT,
            used_id TEXT,
            date DATE,
            row_hash TEXT,
            PRIMARY KEY (combined_id, used_id, date)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS joined_results (
            project_id TEXT,
            student_id TEXT,
            personal_id TEXT,
            combined_id TEXT,
            date DATE,
            PRIMARY KEY (project_id, student_id, personal_id, combined_id, date)
        )
    """)
    
    # Insert sample data
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Projects data
    projects_data = [
        ('PROJ001', 'STU001', 'PER001', today),
        ('PROJ001', 'STU002', 'PER002', today),
        ('PROJ002', 'STU001', 'PER003', today),
        ('PROJ001', 'STU001', 'PER001', yesterday),
        ('PROJ002', 'STU003', 'PER004', yesterday),
    ]
    
    for project_id, student_id, personal_id, date in projects_data:
        row_data = f"{project_id}-{student_id}-{personal_id}-{date}"
        row_hash = hashlib.md5(row_data.encode()).hexdigest()
        cursor.execute(
            "INSERT OR REPLACE INTO projects_data VALUES (?, ?, ?, ?, ?)",
            (project_id, student_id, personal_id, date, row_hash)
        )
    
    # Combined data
    combined_data = [
        ('STU001', 'student_id', today),
        ('STU002', 'student_id', today),
        ('PER002', 'personal_id', today),
        ('PER003', 'personal_id', today),
        ('STU001', 'student_id', yesterday),
        ('PER004', 'personal_id', yesterday),
    ]
    
    for combined_id, used_id, date in combined_data:
        row_data = f"{combined_id}-{used_id}-{date}"
        row_hash = hashlib.md5(row_data.encode()).hexdigest()
        cursor.execute(
            "INSERT OR REPLACE INTO combined_data VALUES (?, ?, ?, ?)",
            (combined_id, used_id, date, row_hash)
        )
    
    conn.commit()

def perform_join(conn):
    """Perform the table join."""
    cursor = conn.cursor()
    
    # The key join logic: combined_id matches either student_id OR personal_id
    join_query = """
    INSERT OR REPLACE INTO joined_results (project_id, student_id, personal_id, combined_id, date)
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
    """
    
    cursor.execute(join_query)
    conn.commit()
    
    # Get results
    cursor.execute("SELECT * FROM joined_results ORDER BY date DESC, project_id")
    results = cursor.fetchall()
    
    return results

def main():
    """Main test function."""
    print("🚀 Testing incremental table join logic...")
    
    # Create in-memory database
    conn = sqlite3.connect(':memory:')
    
    try:
        # Create tables and insert test data
        print("📊 Creating test tables and data...")
        create_test_tables(conn)
        
        # Show initial data
        cursor = conn.cursor()
        
        print("\n📋 Projects Data:")
        cursor.execute("SELECT * FROM projects_data")
        for row in cursor.fetchall():
            print(f"  {row}")
        
        print("\n📋 Combined Data:")
        cursor.execute("SELECT * FROM combined_data")
        for row in cursor.fetchall():
            print(f"  {row}")
        
        # Perform join
        print("\n🔗 Performing table join...")
        results = perform_join(conn)
        
        print(f"\n📋 Join Results ({len(results)} rows):")
        print("  project_id | student_id | personal_id | combined_id | date")
        print("  " + "-" * 60)
        for row in results:
            print(f"  {row[0]:<10} | {row[1]:<10} | {row[2]:<11} | {row[3]:<11} | {row[4]}")
        
        # Show join logic explanation
        print(f"\n🔍 Join Logic Explanation:")
        print("  - Rows are joined when combined_id matches either student_id OR personal_id")
        print("  - AND the dates match between both tables")
        print("  - This creates the desired output: project_id, student_id, personal_id, combined_id, date")
        
        # Count statistics
        cursor.execute("SELECT COUNT(*) FROM projects_data")
        projects_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM combined_data")
        combined_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM joined_results")
        joined_count = cursor.fetchone()[0]
        
        print(f"\n📊 Statistics:")
        print(f"  Projects data rows: {projects_count}")
        print(f"  Combined data rows: {combined_count}")
        print(f"  Joined result rows: {joined_count}")
        print(f"  Join efficiency: {joined_count}/{projects_count} = {joined_count/projects_count:.1%}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        conn.close()
        print("\n✅ Test complete!")

if __name__ == "__main__":
    main()