# Incremental Table Join Solution

This solution provides an efficient way to join two tables with incremental processing, handling only changes since the last execution to minimize redundant operations.

## Problem Statement

You have two tables:

1. **Table 1 (Projects Data)**: `project_id, student_id, personal_id, date`
   - Contains data for the last 360 days
   - Multiple project_ids are active
   - Each project has multiple student_ids and personal_ids linked

2. **Table 2 (Combined Data)**: `combined_id, used_id, date`
   - Contains data for the last 360 days
   - `combined_id` is either a `student_id` or `personal_id`
   - `used_id` indicates whether it's a student_id or personal_id

**Goal**: Join both tables to create a new table with `project_id, student_id, personal_id, combined_id, date` while implementing incremental processing.

## Solution Overview

The solution uses:
- **SQLite database** for data storage and efficient joins
- **Row-level change detection** using MD5 hashes
- **Incremental processing** to handle only changed data
- **Metadata tracking** to remember last execution state

## Key Features

✅ **Incremental Processing**: Only processes changes since last execution  
✅ **Change Detection**: Uses row hashes to detect new, updated, and deleted rows  
✅ **Efficient Joins**: Optimized SQL join logic (`combined_id = student_id OR combined_id = personal_id`)  
✅ **Metadata Tracking**: Tracks execution history and processing statistics  
✅ **Error Handling**: Comprehensive error handling and logging  
✅ **Scalable**: Handles large datasets efficiently  

## Files

- `incremental_table_join.py` - Main solution with the `IncrementalTableJoiner` class
- `example_usage.py` - Example usage with sample data (requires pandas)
- `simple_test.py` - Simple test without external dependencies
- `requirements.txt` - Required Python packages

## Quick Start

### 1. Basic Usage (No Dependencies)

```bash
python3 simple_test.py
```

This runs a simple test demonstrating the core join logic.

### 2. Full Solution (Requires Pandas)

```python
from incremental_table_join import IncrementalTableJoiner
import pandas as pd

# Initialize the joiner
joiner = IncrementalTableJoiner(
    db_path="my_data.db",
    metadata_file="my_metadata.json"
)

# Load your data (replace with your actual data loading)
projects_df = pd.read_csv('projects_data.csv')
combined_df = pd.read_csv('combined_data.csv')

# Process incrementally
joiner.load_projects_data(projects_df, incremental=True)
joiner.load_combined_data(combined_df, incremental=True)

# Perform join
results = joiner.perform_incremental_join()

# Get results
final_results = joiner.get_results()
print(final_results)

joiner.close()
```

## Join Logic

The core join logic is:

```sql
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
```

This joins rows where:
- `combined_id` matches either `student_id` OR `personal_id`
- AND the dates match between both tables

## Incremental Processing Logic

1. **Change Detection**: 
   - Calculate MD5 hash for each row
   - Compare with existing hashes to detect changes
   - Identify new, updated, and deleted rows

2. **Incremental Updates**:
   - Only process changed data
   - Update affected date ranges in results
   - Track processing metadata

3. **Optimization**:
   - Process only necessary date ranges
   - Avoid full table scans when possible
   - Maintain processing statistics

## Example Output

```
Join Results (7 rows):
project_id | student_id | personal_id | combined_id | date
------------------------------------------------------------
PROJ001    | STU001     | PER001      | STU001      | 2025-08-07
PROJ001    | STU002     | PER002      | PER002      | 2025-08-07
PROJ001    | STU002     | PER002      | STU002      | 2025-08-07
PROJ002    | STU001     | PER003      | PER003      | 2025-08-07
PROJ002    | STU001     | PER003      | STU001      | 2025-08-07
PROJ001    | STU001     | PER001      | STU001      | 2025-08-06
PROJ002    | STU003     | PER004      | PER004      | 2025-08-06
```

## Configuration Options

### IncrementalTableJoiner Parameters

- `db_path`: Path to SQLite database file (default: "data_processing.db")
- `metadata_file`: Path to JSON metadata file (default: "processing_metadata.json")

### Methods

- `load_projects_data(data, incremental=True)`: Load projects data
- `load_combined_data(data, incremental=True)`: Load combined data  
- `perform_incremental_join(force_full_join=False)`: Perform table join
- `get_results(date_filter=None)`: Get joined results
- `get_processing_stats()`: Get processing statistics

## Performance Benefits

### Incremental vs Full Processing

For a dataset with 360 days of data:

- **Full Processing**: Processes all ~131,400 rows every time
- **Incremental Processing**: Processes only changed rows (typically <1% of data)

**Example Performance Improvement:**
- Day 1 (Initial): Process 131,400 rows
- Day 2 (Incremental): Process ~365 new rows (99.7% reduction)
- Day 3 (Incremental): Process ~365 new rows (99.7% reduction)

## Error Handling

The solution includes comprehensive error handling:

- Database connection errors
- Data validation errors
- Processing failures with rollback
- Logging for debugging

## Extending the Solution

### Custom Data Sources

Replace the data loading functions to work with your data sources:

```python
def load_your_data():
    # Load from your database
    import mysql.connector
    conn = mysql.connector.connect(...)
    projects_df = pd.read_sql("SELECT ...", conn)
    combined_df = pd.read_sql("SELECT ...", conn)
    return projects_df, combined_df
```

### Custom Join Logic

Modify the join query in `perform_incremental_join()` for different join conditions.

### Additional Filters

Add date ranges, project filters, or other conditions as needed.

## Troubleshooting

### Common Issues

1. **"No module named 'pandas'"**: Install pandas or use `simple_test.py`
2. **Database locked errors**: Ensure proper connection management
3. **Memory issues**: Use chunked processing for very large datasets

### Debug Information

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

To extend this solution:

1. Fork the repository
2. Add your enhancements
3. Test with both `simple_test.py` and full solution
4. Submit a pull request

## License

This solution is provided as-is for educational and commercial use.