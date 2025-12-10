#!/usr/bin/env python3
"""
Cursor AI Adoption Report

Main entry point for generating Cursor AI adoption reports.
Combines data from multiple CSV sources to generate comprehensive adoption metrics.

Usage:
    python cursor_adoption_report.py
"""

import os
import sys
from datetime import datetime
from typing import Tuple, Optional

# Import our modules
from cursor_data_loader import (
    load_allowed_emails_and_metadata,
    load_usage_events,
    load_user_leaderboard,
    load_repository_analytics,
    merge_cursor_user_data
)
from cursor_metrics_calculator import calculate_master_metrics, calculate_chapter_breakdown
from cursor_csv_reporter import generate_individual_report, generate_master_report
from cursor_html_reporter import generate_html_report


def extract_date_range_from_events(csv_path: str) -> Optional[Tuple[datetime, datetime]]:
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


def main():
    """Main function to generate Cursor AI adoption reports."""
    print("="*60)
    print("Cursor AI Adoption Report Generator")
    print("="*60)
    print()
    
    # Define file paths
    cursor_data_dir = 'Cursor_Data'
    usage_events_path = os.path.join(cursor_data_dir, 'cursor_team_usage_events.csv')
    leaderboard_path = os.path.join(cursor_data_dir, 'cursor_User_Leaderboard.csv')
    repo_analytics_path = os.path.join(cursor_data_dir, 'cursor_Team_Repository_Analytics.csv')
    
    # Check if files exist
    missing_files = []
    for path, name in [
        (usage_events_path, 'cursor_team_usage_events.csv'),
        (leaderboard_path, 'cursor_User_Leaderboard.csv'),
        (repo_analytics_path, 'cursor_Team_Repository_Analytics.csv'),
        ('useremails.csv', 'useremails.csv'),
    ]:
        if not os.path.exists(path):
            missing_files.append(name)
    
    if missing_files:
        print("Error: The following required files are missing:")
        for f in missing_files:
            print(f"  - {f}")
        return 1
    
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
            # Use a default range if we can't extract it
            date_range = (datetime(2025, 1, 1).date(), datetime(2025, 12, 31).date())
        
        # Step 3: Load usage events
        print("\nStep 3: Loading usage events...")
        usage_events = load_usage_events(usage_events_path, allowed_emails, date_range)
        
        # Step 4: Load user leaderboard
        print("\nStep 4: Loading user leaderboard...")
        leaderboard = load_user_leaderboard(leaderboard_path, allowed_emails)
        
        # Step 5: Load repository analytics
        print("\nStep 5: Loading repository analytics...")
        repo_analytics = load_repository_analytics(repo_analytics_path)
        
        # Step 6: Merge user data
        print("\nStep 6: Merging user data...")
        merged_users = merge_cursor_user_data(
            usage_events, leaderboard, allowed_emails, email_metadata
        )
        
        # Step 7: Calculate master metrics
        print("\nStep 7: Calculating master metrics...")
        master_metrics = calculate_master_metrics(merged_users, date_range)
        
        # Step 8: Generate CSV reports
        print("\nStep 8: Generating CSV reports...")
        generate_individual_report(merged_users, 'cursor_individual_adoption_report.csv')
        generate_master_report(
            merged_users, repo_analytics, master_metrics, date_range,
            'cursor_master_adoption_report.csv'
        )
        
        # Step 9: Generate HTML report
        print("\nStep 9: Generating HTML report...")
        generate_html_report(
            merged_users, master_metrics, repo_analytics, date_range,
            'cursor_adoption_report.html'
        )
        
        # Summary
        print("\n" + "="*60)
        print("REPORT GENERATION COMPLETE")
        print("="*60)
        print(f"\nReport Period: {master_metrics['report_period']}")
        print(f"Total Users: {master_metrics['total_users']}")
        print(f"Active Users: {master_metrics['active_users']}")
        print(f"Adoption Rate: {master_metrics['adoption_rate']}%")
        print(f"\nGenerated Files:")
        print(f"  - cursor_individual_adoption_report.csv")
        print(f"  - cursor_master_adoption_report.csv")
        print(f"  - cursor_adoption_report.html")
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

