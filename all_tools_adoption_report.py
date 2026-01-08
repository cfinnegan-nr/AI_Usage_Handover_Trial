#!/usr/bin/env python3
"""
All Tools Adoption Report

Merges Cursor AI usage data into combined AI usage trends CSV.
Updates Cursor columns (Total Requests, Agent Completions, LOC) 
for matching Year/Month/Email rows.

Usage:
    python all_tools_adoption_report.py YYYY-MM
    
Example:
    python all_tools_adoption_report.py 2025-12
"""

import csv
import argparse
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional


def parse_month_argument(month_str: str) -> Tuple[str, str]:
    """Parse YYYY-MM format to (year, month_abbrev).
    
    Args:
        month_str: Month string in YYYY-MM format (e.g., '2025-12')
        
    Returns:
        Tuple of (year_str, month_abbrev) where:
        - year_str: Year in YYYY format (e.g., '2025')
        - month_abbrev: Month abbreviation in MMM format (e.g., 'Dec')
        
    Raises:
        ValueError: If month format is invalid or month number is out of range
    """
    if not month_str:
        raise ValueError("Month parameter is required (format: YYYY-MM)")
    
    try:
        # Parse YYYY-MM format
        parts = month_str.split('-')
        if len(parts) != 2:
            raise ValueError(f"Invalid month format '{month_str}'. Expected YYYY-MM format (e.g., '2025-12')")
        
        year, month_num = map(int, parts)
        
        # Validate month number
        if month_num < 1 or month_num > 12:
            raise ValueError(f"Invalid month number: {month_num}. Must be between 1 and 12.")
        
        # Create datetime object for the first day of the month to get abbreviation
        month_date = datetime(year, month_num, 1)
        month_abbrev = month_date.strftime('%b')  # Returns 'Nov', 'Dec', etc.
        
        year_str = str(year)
        
        return year_str, month_abbrev
        
    except ValueError as e:
        # Re-raise ValueError with more context
        if "invalid literal" in str(e) or "month" in str(e).lower():
            raise ValueError(f"Invalid month format '{month_str}'. Expected YYYY-MM format (e.g., '2025-12'). Error: {e}")
        raise
    except Exception as e:
        raise ValueError(f"Error parsing month '{month_str}': {e}")


def load_cursor_trends_csv(file_path: str, year: str, month_abbrev: str) -> Dict[Tuple[str, str, str], Dict[str, int]]:
    """Load cursor trends CSV and create lookup dictionary by (year, month, email).
    
    Args:
        file_path: Path to fs-eng-cursor-ai-usage-trends.csv
        year: Year string to filter by (e.g., '2025')
        month_abbrev: Month abbreviation to filter by (e.g., 'Dec')
        
    Returns:
        Dictionary keyed by (year, month_abbrev, email_lowercase) with values:
        {
            'total_requests': int,
            'agent_completions': int,
            'total_ai_lines': int
        }
        
    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If required columns are missing
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cursor trends CSV file not found: {file_path}")
    
    cursor_data = {}
    required_columns = ['Year', 'Month', 'Email', 'Total Requests', 'Agent Completions', 'Total AI Lines']
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # Validate required columns exist
            missing_columns = [col for col in required_columns if col not in reader.fieldnames]
            if missing_columns:
                raise ValueError(
                    f"Missing required columns in cursor trends CSV: {', '.join(missing_columns)}. "
                    f"Found columns: {', '.join(reader.fieldnames)}"
                )
            
            rows_processed = 0
            rows_matched = 0
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    row_year = row.get('Year', '').strip()
                    row_month = row.get('Month', '').strip()
                    email = row.get('Email', '').strip().lower()
                    
                    # Skip rows that don't match the target Year/Month
                    if row_year != year or row_month != month_abbrev:
                        continue
                    
                    if not email:
                        print(f"Warning: Row {row_num} in cursor trends CSV has empty email. Skipping.")
                        continue
                    
                    # Extract numeric values, defaulting to 0 if empty or invalid
                    try:
                        total_requests = int(row.get('Total Requests', '0') or '0')
                    except (ValueError, TypeError):
                        total_requests = 0
                        print(f"Warning: Row {row_num} in cursor trends CSV has invalid 'Total Requests'. Using 0.")
                    
                    try:
                        agent_completions = int(row.get('Agent Completions', '0') or '0')
                    except (ValueError, TypeError):
                        agent_completions = 0
                        print(f"Warning: Row {row_num} in cursor trends CSV has invalid 'Agent Completions'. Using 0.")
                    
                    try:
                        total_ai_lines = int(row.get('Total AI Lines', '0') or '0')
                    except (ValueError, TypeError):
                        total_ai_lines = 0
                        print(f"Warning: Row {row_num} in cursor trends CSV has invalid 'Total AI Lines'. Using 0.")
                    
                    # Create lookup key
                    key = (row_year, row_month, email)
                    
                    # Store data (overwrite if duplicate key exists - should not happen)
                    if key in cursor_data:
                        print(f"Warning: Duplicate key found in cursor trends CSV: {key}. Using latest value.")
                    
                    cursor_data[key] = {
                        'total_requests': total_requests,
                        'agent_completions': agent_completions,
                        'total_ai_lines': total_ai_lines
                    }
                    
                    rows_matched += 1
                    
                except Exception as e:
                    print(f"Warning: Error processing row {row_num} in cursor trends CSV: {e}. Skipping row.")
                    continue
                
                rows_processed += 1
            
            print(f"Loaded {rows_matched} matching rows from cursor trends CSV (filtered by {year}/{month_abbrev})")
            
    except FileNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"Error reading cursor trends CSV '{file_path}': {e}")
    
    return cursor_data


def load_ai_trends_csv(file_path: str) -> Tuple[List[str], List[List[str]]]:
    """Load AI trends CSV and return header and all rows.
    
    Args:
        file_path: Path to fs-eng-ai-usage-trends.csv
        
    Returns:
        Tuple of (header_row, data_rows) where:
        - header_row: List of column names
        - data_rows: List of data rows (each row is a list of strings)
        
    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If required columns are missing
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"AI trends CSV file not found: {file_path}")
    
    required_columns = ['Year', 'Month', 'Email', 'Cursor Total Requests', 'Cursor Agent Completions', 'Cursor LOC']
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            
            # Read header
            header_row = next(reader, None)
            if not header_row:
                raise ValueError(f"AI trends CSV file '{file_path}' is empty (no header row)")
            
            # Validate required columns exist
            missing_columns = [col for col in required_columns if col not in header_row]
            if missing_columns:
                raise ValueError(
                    f"Missing required columns in AI trends CSV: {', '.join(missing_columns)}. "
                    f"Found columns: {', '.join(header_row)}"
                )
            
            # Read all data rows
            data_rows = []
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                # Pad row to match header length if needed
                while len(row) < len(header_row):
                    row.append('')
                # Truncate if too long
                if len(row) > len(header_row):
                    row = row[:len(header_row)]
                
                data_rows.append(row)
            
            print(f"Loaded {len(data_rows)} rows from AI trends CSV")
            
    except FileNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"Error reading AI trends CSV '{file_path}': {e}")
    
    return header_row, data_rows


def should_update_row(cursor_total_req: str, cursor_agent_comp: str, cursor_loc: str) -> bool:
    """Check if all three Cursor columns are zero/empty.
    
    Args:
        cursor_total_req: Value from 'Cursor Total Requests' column
        cursor_agent_comp: Value from 'Cursor Agent Completions' column
        cursor_loc: Value from 'Cursor LOC' column
        
    Returns:
        True if all three values are zero or empty, False otherwise
    """
    def is_zero_or_empty(value: str) -> bool:
        """Check if value is zero or empty."""
        if not value or not str(value).strip():
            return True
        try:
            return int(str(value).strip()) == 0
        except (ValueError, TypeError):
            # If we can't parse it as an integer, treat as non-zero (don't update)
            return False
    
    return (is_zero_or_empty(cursor_total_req) and 
            is_zero_or_empty(cursor_agent_comp) and 
            is_zero_or_empty(cursor_loc))


def update_ai_trends_with_cursor_data(
    ai_trends_file_path: str,
    cursor_data: Dict[Tuple[str, str, str], Dict[str, int]],
    year: str,
    month_abbrev: str
) -> Tuple[int, int, int]:
    """Update AI trends CSV with cursor data for matching rows.
    
    Args:
        ai_trends_file_path: Path to fs-eng-ai-usage-trends.csv (will be updated in place)
        cursor_data: Dictionary from load_cursor_trends_csv()
        year: Year string to filter by
        month_abbrev: Month abbreviation to filter by
        year: Year string to filter by
        
    Returns:
        Tuple of (updated_count, skipped_count, unmatched_count) where:
        - updated_count: Number of rows updated
        - skipped_count: Number of rows skipped (non-zero values already present)
        - unmatched_count: Number of cursor data entries with no matching AI trends row
    """
    # Load AI trends CSV
    header_row, data_rows = load_ai_trends_csv(ai_trends_file_path)
    
    # Find column indices
    try:
        year_idx = header_row.index('Year')
        month_idx = header_row.index('Month')
        email_idx = header_row.index('Email')
        cursor_total_req_idx = header_row.index('Cursor Total Requests')
        cursor_agent_comp_idx = header_row.index('Cursor Agent Completions')
        cursor_loc_idx = header_row.index('Cursor LOC')
    except ValueError as e:
        raise ValueError(f"Required column not found in AI trends CSV header: {e}")
    
    updated_count = 0
    skipped_count = 0
    unmatched_cursor_keys = set(cursor_data.keys())
    
    # Process each row
    for row_num, row in enumerate(data_rows, start=2):  # Start at 2 (header is row 1)
        try:
            # Check if row matches target Year/Month
            row_year = row[year_idx].strip() if year_idx < len(row) else ''
            row_month = row[month_idx].strip() if month_idx < len(row) else ''
            
            if row_year != year or row_month != month_abbrev:
                # Not matching Year/Month, skip (preserve as-is)
                continue
            
            # Get email for matching
            email = row[email_idx].strip().lower() if email_idx < len(row) else ''
            if not email:
                print(f"Warning: Row {row_num} in AI trends CSV has empty email for {year}/{month_abbrev}. Skipping.")
                continue
            
            # Create lookup key
            key = (row_year, row_month, email)
            
            # Check if cursor data exists for this key
            if key not in cursor_data:
                # No matching cursor data - this is expected for some users
                continue
            
            # Remove from unmatched set (we found a match)
            unmatched_cursor_keys.discard(key)
            
            # Get current Cursor column values
            cursor_total_req = row[cursor_total_req_idx].strip() if cursor_total_req_idx < len(row) else ''
            cursor_agent_comp = row[cursor_agent_comp_idx].strip() if cursor_agent_comp_idx < len(row) else ''
            cursor_loc = row[cursor_loc_idx].strip() if cursor_loc_idx < len(row) else ''
            
            # Check if we should update (all three columns must be zero/empty)
            if not should_update_row(cursor_total_req, cursor_agent_comp, cursor_loc):
                skipped_count += 1
                print(f"Row {row_num} ({email}): Skipping update - Cursor columns already have non-zero values")
                continue
            
            # Update the row with cursor data
            cursor_info = cursor_data[key]
            
            # Ensure row has enough columns
            while len(row) < len(header_row):
                row.append('')
            
            # Update the three Cursor columns
            row[cursor_total_req_idx] = str(cursor_info['total_requests'])
            row[cursor_agent_comp_idx] = str(cursor_info['agent_completions'])
            row[cursor_loc_idx] = str(cursor_info['total_ai_lines'])
            
            updated_count += 1
            print(f"Row {row_num} ({email}): Updated Cursor columns - "
                  f"Requests: {cursor_info['total_requests']}, "
                  f"Completions: {cursor_info['agent_completions']}, "
                  f"LOC: {cursor_info['total_ai_lines']}")
            
        except Exception as e:
            print(f"Warning: Error processing row {row_num} in AI trends CSV: {e}. Preserving row as-is.")
            continue
    
    # Write updated CSV back to file
    try:
        with open(ai_trends_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header_row)
            for row in data_rows:
                writer.writerow(row)
        
        print(f"Successfully wrote updated AI trends CSV to {ai_trends_file_path}")
        
    except Exception as e:
        raise IOError(f"Error writing updated AI trends CSV to '{ai_trends_file_path}': {e}")
    
    unmatched_count = len(unmatched_cursor_keys)
    
    return updated_count, skipped_count, unmatched_count


def main():
    """Main entry point with argument parsing and orchestration."""
    parser = argparse.ArgumentParser(
        description='Merge Cursor AI usage data into combined AI usage trends CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update December 2025 data
  python all_tools_adoption_report.py 2025-12
  
  # Update November 2025 data
  python all_tools_adoption_report.py 2025-11
        """
    )
    
    parser.add_argument(
        'month',
        type=str,
        help='Month in YYYY-MM format (e.g., 2025-12)'
    )
    
    args = parser.parse_args()
    
    try:
        # Parse month argument
        print("="*60)
        print("All Tools Adoption Report - Cursor Data Merger")
        print("="*60)
        print(f"\nParsing month argument: {args.month}")
        year, month_abbrev = parse_month_argument(args.month)
        print(f"Target period: {year}/{month_abbrev}")
        
        # Define file paths
        ai_trends_file = os.path.join('AI_Usage_Output', 'fs-eng-ai-usage-trends.csv')
        cursor_trends_file = os.path.join('Cursor_Output', 'fs-eng-cursor-ai-usage-trends.csv')
        
        # Validate files exist
        if not os.path.exists(ai_trends_file):
            print(f"\nError: AI trends CSV file not found: {ai_trends_file}")
            print(f"  Expected location: {os.path.abspath(ai_trends_file)}")
            return 1
        
        if not os.path.exists(cursor_trends_file):
            print(f"\nError: Cursor trends CSV file not found: {cursor_trends_file}")
            print(f"  Expected location: {os.path.abspath(cursor_trends_file)}")
            return 1
        
        # Load cursor trends data
        print(f"\nLoading cursor trends data from: {cursor_trends_file}")
        cursor_data = load_cursor_trends_csv(cursor_trends_file, year, month_abbrev)
        
        if not cursor_data:
            print(f"\nWarning: No cursor data found for {year}/{month_abbrev}")
            print("  No updates will be made.")
            return 0
        
        # Update AI trends CSV
        print(f"\nUpdating AI trends CSV: {ai_trends_file}")
        updated_count, skipped_count, unmatched_count = update_ai_trends_with_cursor_data(
            ai_trends_file,
            cursor_data,
            year,
            month_abbrev
        )
        
        # Print summary
        print("\n" + "="*60)
        print("UPDATE SUMMARY")
        print("="*60)
        print(f"Period: {year}/{month_abbrev}")
        print(f"Rows updated: {updated_count}")
        print(f"Rows skipped (non-zero values already present): {skipped_count}")
        print(f"Unmatched cursor rows (no matching AI trends row): {unmatched_count}")
        print(f"Total cursor data entries: {len(cursor_data)}")
        print("="*60)
        
        return 0
        
    except ValueError as e:
        print(f"\nError: {e}")
        return 1
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
