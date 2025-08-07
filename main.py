#!/usr/bin/env python3
"""
Incremental Join Processor - Main Application
============================================

This application provides incremental data processing for joining two tables:
1. project_data (project_id, student_id, personal_id, date)
2. combined_data (combined_id, used_id, date)

The join logic matches student_id or personal_id with combined_id on the same date.

Features:
- Incremental processing (only processes changes since last run)
- Full refresh capability
- Performance monitoring
- Automated scheduling
- Error handling and retry logic
- Comprehensive logging

Usage:
    python main.py [--mode {incremental|full|monitor|setup}] [--date-range DAYS]
"""

import argparse
import sys
import time
import schedule
from datetime import datetime, timedelta

from incremental_join_processor import IncrementalJoinProcessor
from config import Config


def setup_database():
    """Setup the database schema and initial configuration"""
    print("Setting up database schema...")
    
    processor = IncrementalJoinProcessor(Config.get_db_config())
    try:
        processor.connect()
        
        # Read and execute schema setup
        with open('/workspace/table_schemas.sql', 'r') as f:
            schema_sql = f.read()
        
        # Execute schema creation (split by statements)
        cursor = processor.connection.cursor()
        for statement in schema_sql.split(';'):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        
        processor.connection.commit()
        cursor.close()
        
        print("✓ Database schema created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error setting up database: {e}")
        return False
    finally:
        processor.disconnect()


def run_incremental_processing():
    """Run incremental data processing"""
    print(f"\n{'='*60}")
    print(f"Starting incremental processing - {datetime.now()}")
    print(f"{'='*60}")
    
    processor = IncrementalJoinProcessor(Config.get_db_config())
    
    try:
        processor.connect()
        
        # Get initial statistics
        initial_stats = processor.get_statistics()
        print("Initial statistics:")
        for key, value in initial_stats.items():
            print(f"  {key}: {value:,}")
        
        # Perform incremental processing
        start_time = time.time()
        processed_count = processor.perform_incremental_join()
        end_time = time.time()
        
        # Get final statistics
        final_stats = processor.get_statistics()
        
        # Calculate performance metrics
        processing_time = end_time - start_time
        records_per_second = processed_count / processing_time if processing_time > 0 else 0
        
        print(f"\n📊 Processing Results:")
        print(f"  Records processed: {processed_count:,}")
        print(f"  Processing time: {processing_time:.2f} seconds")
        print(f"  Records per second: {records_per_second:.2f}")
        
        print(f"\n📈 Final statistics:")
        for key, value in final_stats.items():
            change = value - initial_stats.get(key, 0)
            change_indicator = f" (+{change:,})" if change > 0 else ""
            print(f"  {key}: {value:,}{change_indicator}")
        
        if processed_count == 0:
            print("ℹ️  No changes detected - system is up to date")
        else:
            print(f"✅ Successfully processed {processed_count:,} records")
            
        return True
        
    except Exception as e:
        print(f"❌ Error during incremental processing: {e}")
        return False
    finally:
        processor.disconnect()


def run_full_refresh(date_range_days=None):
    """Run full refresh of the data"""
    days = date_range_days or Config.DATE_RANGE_DAYS
    
    print(f"\n{'='*60}")
    print(f"Starting full refresh for last {days} days - {datetime.now()}")
    print(f"{'='*60}")
    
    processor = IncrementalJoinProcessor(Config.get_db_config())
    
    try:
        processor.connect()
        
        # Get initial statistics
        initial_stats = processor.get_statistics()
        print("Initial statistics:")
        for key, value in initial_stats.items():
            print(f"  {key}: {value:,}")
        
        # Perform full refresh
        start_time = time.time()
        processed_count = processor.full_refresh(days)
        end_time = time.time()
        
        # Get final statistics
        final_stats = processor.get_statistics()
        
        # Calculate performance metrics
        processing_time = end_time - start_time
        records_per_second = processed_count / processing_time if processing_time > 0 else 0
        
        print(f"\n📊 Processing Results:")
        print(f"  Records processed: {processed_count:,}")
        print(f"  Processing time: {processing_time:.2f} seconds")
        print(f"  Records per second: {records_per_second:.2f}")
        
        print(f"\n📈 Final statistics:")
        for key, value in final_stats.items():
            change = value - initial_stats.get(key, 0)
            change_indicator = f" (+{change:,})" if change > 0 else ""
            print(f"  {key}: {value:,}{change_indicator}")
        
        print(f"✅ Successfully completed full refresh")
        return True
        
    except Exception as e:
        print(f"❌ Error during full refresh: {e}")
        return False
    finally:
        processor.disconnect()


def monitor_system():
    """Monitor the system status and performance"""
    print(f"\n{'='*60}")
    print(f"System Monitoring Report - {datetime.now()}")
    print(f"{'='*60}")
    
    processor = IncrementalJoinProcessor(Config.get_db_config())
    
    try:
        processor.connect()
        cursor = processor.connection.cursor()
        
        # Check incremental processing status
        print("\n🔍 Incremental Processing Status:")
        cursor.execute("""
            SELECT 
                table_name,
                last_processed_timestamp,
                last_processed_date,
                TIMESTAMPDIFF(MINUTE, last_processed_timestamp, NOW()) as minutes_since_last_process,
                updated_at
            FROM incremental_tracking
            ORDER BY last_processed_timestamp DESC
        """)
        
        for table_name, last_ts, last_date, minutes_ago, updated_at in cursor.fetchall():
            status = "🟢 CURRENT" if minutes_ago < Config.ALERT_THRESHOLD_MINUTES else "🔴 STALE"
            print(f"  {table_name}: {status}")
            print(f"    Last processed: {last_ts} ({minutes_ago} minutes ago)")
            print(f"    Last date: {last_date}")
        
        # Get table statistics
        print("\n📊 Table Statistics:")
        stats = processor.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value:,}")
        
        # Check for data quality issues
        print("\n🔍 Data Quality Check (last 7 days):")
        cursor.execute("""
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
                AND c.date >= CURDATE() - INTERVAL 7 DAY
        """)
        
        for issue_type, issue_count in cursor.fetchall():
            status = "✅ OK" if issue_count == 0 else f"⚠️  {issue_count} issues"
            print(f"  {issue_type}: {status}")
        
        # Performance metrics (if available)
        cursor.execute("""
            SELECT 
                DATE(created_at) as processing_date,
                COUNT(*) as records_processed,
                COUNT(DISTINCT project_id) as unique_projects,
                COUNT(DISTINCT combined_id) as unique_combined_ids
            FROM joined_result
            WHERE created_at >= CURDATE() - INTERVAL 7 DAY
            GROUP BY DATE(created_at)
            ORDER BY processing_date DESC
            LIMIT 7
        """)
        
        results = cursor.fetchall()
        if results:
            print(f"\n📈 Recent Processing Activity:")
            for proc_date, records, projects, combined_ids in results:
                print(f"  {proc_date}: {records:,} records, {projects} projects, {combined_ids} combined IDs")
        else:
            print(f"\n📈 No recent processing activity found")
        
        cursor.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")
        return False
    finally:
        processor.disconnect()


def schedule_incremental_processing():
    """Schedule incremental processing to run automatically"""
    print("🕐 Scheduling incremental processing...")
    
    # Schedule incremental processing every hour
    schedule.every().hour.do(run_incremental_processing)
    
    # Schedule monitoring every 4 hours
    schedule.every(4).hours.do(monitor_system)
    
    # Schedule daily maintenance at 2 AM
    schedule.every().day.at("02:00").do(run_daily_maintenance)
    
    print("📅 Scheduled jobs:")
    print("  - Incremental processing: Every hour")
    print("  - System monitoring: Every 4 hours")
    print("  - Daily maintenance: Daily at 2:00 AM")
    print("\n🔄 Starting scheduler... (Press Ctrl+C to stop)")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n🛑 Scheduler stopped by user")


def run_daily_maintenance():
    """Run daily maintenance tasks"""
    print(f"\n{'='*60}")
    print(f"Starting daily maintenance - {datetime.now()}")
    print(f"{'='*60}")
    
    processor = IncrementalJoinProcessor(Config.get_db_config())
    
    try:
        processor.connect()
        cursor = processor.connection.cursor()
        
        # Collect performance metrics
        if Config.METRICS_ENABLED:
            print("📊 Collecting performance metrics...")
            cursor.execute("CALL CollectPerformanceMetrics()")
            processor.connection.commit()
            print("✅ Performance metrics collected")
        
        # Update table statistics
        print("📈 Updating table statistics...")
        cursor.execute("ANALYZE TABLE project_data, combined_data, joined_result")
        print("✅ Table statistics updated")
        
        # Clean up old error logs
        print("🧹 Cleaning up old error logs...")
        cursor.execute("DELETE FROM error_log WHERE error_time < DATE_SUB(NOW(), INTERVAL 30 DAY)")
        deleted_count = cursor.rowcount
        processor.connection.commit()
        print(f"✅ Cleaned up {deleted_count} old error log entries")
        
        cursor.close()
        print("✅ Daily maintenance completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error during daily maintenance: {e}")
        return False
    finally:
        processor.disconnect()


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="Incremental Join Processor for project and combined data tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--mode', 
        choices=['incremental', 'full', 'monitor', 'setup', 'schedule'],
        default='incremental',
        help='Processing mode (default: incremental)'
    )
    
    parser.add_argument(
        '--date-range',
        type=int,
        help='Number of days to process for full refresh (default: from config)'
    )
    
    parser.add_argument(
        '--config',
        action='store_true',
        help='Show current configuration'
    )
    
    args = parser.parse_args()
    
    # Show configuration if requested
    if args.config:
        Config.print_config()
        return
    
    # Validate configuration
    if not Config.validate_config():
        print("❌ Configuration validation failed")
        sys.exit(1)
    
    # Show configuration summary
    Config.print_config()
    
    # Execute based on mode
    success = False
    
    if args.mode == 'setup':
        success = setup_database()
    elif args.mode == 'incremental':
        success = run_incremental_processing()
    elif args.mode == 'full':
        success = run_full_refresh(args.date_range)
    elif args.mode == 'monitor':
        success = monitor_system()
    elif args.mode == 'schedule':
        schedule_incremental_processing()
        success = True
    
    if success:
        print(f"\n✅ Operation completed successfully")
        sys.exit(0)
    else:
        print(f"\n❌ Operation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()