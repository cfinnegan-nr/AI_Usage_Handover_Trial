#!/usr/bin/env python3
"""
Cursor AI Adoption Report

Main entry point for generating Cursor AI adoption reports.
Combines data from multiple CSV sources to generate comprehensive adoption metrics.

Usage:
    python cursor_adoption_report.py
"""

import argparse
import os
import sys
from datetime import datetime, date
from typing import Tuple, Optional

# Import our modules
from cursor_data_loader import (
    load_allowed_emails_and_metadata,
    load_usage_events,
    load_user_leaderboard,
    load_repository_analytics,
    load_fs_repo_list,
    merge_cursor_user_data,
    find_newest_file_by_pattern
)
from cursor_metrics_calculator import calculate_master_metrics, calculate_chapter_breakdown
from cursor_csv_reporter import generate_individual_report, generate_master_report
from cursor_html_reporter import generate_html_report


def extract_date_range_from_events(csv_path: str) -> Optional[Tuple[date, date]]:
    """Extract date range from cursor_team_usage_events.csv.
    
    Args:
        csv_path: Path to cursor_team_usage_events.csv
        
    Returns:
        Tuple of (start_date, end_date) or None if file not found/empty
    """
    import csv
    
    try:
        min_date = None
        max_date = None
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get('Date', '').strip()
                if not date_str:
                    continue
                
                try:
                    date_str_clean = date_str.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(date_str_clean)
                    event_date = dt.date()
                    
                    if min_date is None or event_date < min_date:
                        min_date = event_date
                    if max_date is None or event_date > max_date:
                        max_date = event_date
                        
                except (ValueError, AttributeError):
                    continue
        
        if min_date and max_date:
            print(f"Date range detected: {min_date} to {max_date}")
            return min_date, max_date
        else:
            print("Warning: Could not extract date range from usage events file")
            return None
            
    except FileNotFoundError:
        print(f"Warning: File '{csv_path}' not found. Cannot extract date range.")
        return None
    except Exception as e:
        print(f"Warning: Error extracting date range: {e}")
        return None


def parse_month_suffix(month: str) -> str:
    """Parse YYYY-MM month string into filename suffix format _MMM_YY."""
    try:
        month_date = datetime.strptime(f'{month}-01', '%Y-%m-%d')
    except ValueError as exc:
        raise ValueError(
            f"Invalid --month '{month}'. Expected YYYY-MM format (e.g., 2026-01)."
        ) from exc

    month_abbrev = month_date.strftime('%b')
    year_two_digit = month_date.strftime('%y')
    return f'_{month_abbrev}_{year_two_digit}'


def main():
    """Main function to generate Cursor AI adoption reports."""
    parser = argparse.ArgumentParser(
        description='Generate Cursor AI adoption reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cursor_adoption_report.py --month 2026-01
        """,
    )
    parser.add_argument(
        '--month',
        required=True,
        help='Month in YYYY-MM format (e.g., 2026-01)',
    )
    args = parser.parse_args()

    print("="*60)
    print("Cursor AI Adoption Report Generator")
    print("="*60)
    print()
    
    # Define file paths using flexible pattern matching
    cursor_data_dir = 'Cursor_Data'
    
    # Find files by pattern (newest matching file)
    print("\nLocating input files...")
    usage_events_path = find_newest_file_by_pattern(cursor_data_dir, 'usage-event')
    leaderboard_path = find_newest_file_by_pattern(cursor_data_dir, 'User_Leaderboard')
    repo_analytics_path = find_newest_file_by_pattern(cursor_data_dir, 'Team_Repository_Analytics')
    
    # Check if files exist
    missing_files = []
    if not usage_events_path:
        missing_files.append('team_usage_event (CSV file)')
    else:
        print(f"  Found usage events file: {os.path.basename(usage_events_path)}")
    
    if not leaderboard_path:
        missing_files.append('User_Leaderboard (CSV file)')
    else:
        print(f"  Found leaderboard file: {os.path.basename(leaderboard_path)}")
    
    if not repo_analytics_path:
        missing_files.append('Team_Repository_Analytics (CSV file)')
    else:
        print(f"  Found repository analytics file: {os.path.basename(repo_analytics_path)}")
    
    if not os.path.exists('useremails.csv'):
        missing_files.append('useremails.csv')
    
    if missing_files:
        print("\nError: The following required files are missing:")
        for f in missing_files:
            print(f"  - {f}")
        return 1
    
    # Type assertions: at this point, files must exist (checked above)
    assert usage_events_path is not None, "usage_events_path should be set"
    assert leaderboard_path is not None, "leaderboard_path should be set"
    assert repo_analytics_path is not None, "repo_analytics_path should be set"
    
    try:
        # Step 1: Load allowed emails and metadata
        print("\nStep 1: Loading user emails and metadata...")
        allowed_emails, email_metadata = load_allowed_emails_and_metadata()
        
        if not allowed_emails:
            print("Error: No allowed emails found in useremails.csv")
            return 1
        
        # Step 2: Extract date range from usage events
        print("\nStep 2: Extracting date range from usage events...")
        date_range = extract_date_range_from_events(usage_events_path)
        
        if not date_range:
            print("Warning: Could not extract date range. Using all available data.")
            # Use a very wide range that won't filter out any data
            # This ensures all events are included regardless of when the code runs
            date_range = (date(2000, 1, 1), date(2099, 12, 31))
        
        # Step 3: Load usage events
        print("\nStep 3: Loading usage events...")
        usage_events = load_usage_events(usage_events_path, allowed_emails, date_range)
        
        # Step 4: Load user leaderboard
        print("\nStep 4: Loading user leaderboard...")
        leaderboard = load_user_leaderboard(leaderboard_path, allowed_emails, date_range)
        
        # Step 5: Load repository analytics
        print("\nStep 5: Loading repository analytics...")
        repo_analytics = load_repository_analytics(repo_analytics_path)
        
        # Step 5b: Load FS repository list
        print("\nStep 5b: Loading FS repository list...")
        fs_repo_list_path = os.path.join(cursor_data_dir, 'FS_Repo_List.csv')
        fs_repo_names = load_fs_repo_list(fs_repo_list_path)
        
        # Step 6: Merge user data
        print("\nStep 6: Merging user data...")
        merged_users = merge_cursor_user_data(
            usage_events, leaderboard, allowed_emails, email_metadata
        )
        
        # Step 7: Calculate master metrics
        print("\nStep 7: Calculating master metrics...")
        master_metrics = calculate_master_metrics(merged_users, date_range)
        
        # Step 8: Create output directory
        print("\nStep 8: Creating output directory...")
        output_dir = 'Cursor_Output'
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory: {output_dir}")

        report_suffix = parse_month_suffix(args.month)

        # Step 9: Generate CSV reports
        print("\nStep 9: Generating CSV reports...")
        generate_individual_report(
            merged_users,
            os.path.join(
                output_dir, f'cursor_individual_adoption_report{report_suffix}.csv'
            ),
        )
        generate_master_report(
            merged_users, repo_analytics, master_metrics, date_range,
            os.path.join(
                output_dir, f'cursor_master_adoption_report{report_suffix}.csv'
            ),
        )
        
        # Step 10: Generate HTML report
        print("\nStep 10: Generating HTML report...")
        generate_html_report(
            merged_users, master_metrics, repo_analytics, date_range,
            os.path.join(
                output_dir, f'cursor_adoption_report{report_suffix}.html'
            ),
            fs_repo_names,
        )
        
        # Summary
        print("\n" + "="*60)
        print("REPORT GENERATION COMPLETE")
        print("="*60)
        print(f"\nReport Period: {master_metrics['report_period']}")
        print(f"Total Users: {master_metrics['total_users']}")
        print(f"Active Users: {master_metrics['active_users']}")
        print(f"Adoption Rate: {master_metrics['adoption_rate']}%")
        print(f"\nGenerated Files (in {output_dir}/):")
        print(
            f"  - cursor_individual_adoption_report{report_suffix}.csv"
        )
        print(
            f"  - cursor_master_adoption_report{report_suffix}.csv"
        )
        print(
            f"  - cursor_adoption_report{report_suffix}.html"
        )
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

