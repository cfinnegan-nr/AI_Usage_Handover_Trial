#!/usr/bin/env python3
"""
Cursor Data Loader Module

This module handles loading and filtering Cursor AI usage data from CSV files.
It filters data by allowed emails from useremails.csv and aggregates metrics per user.
"""

import csv
import os
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional


def load_allowed_emails_and_metadata() -> Tuple[Set[str], Dict[str, Dict[str, str]]]:
    """Load allowed emails and metadata (chapter, squad) from useremails.csv file.
    Also loads emails from User_Leaderboard file and creates an INTERSECTION of both sets.
    Only emails present in BOTH files will be included.
    
    Returns:
        Tuple of (set of allowed emails (intersection of both sources), dict mapping email to metadata)
    """
    useremails_set = set()
    useremails_metadata = {}
    leaderboard_emails_set = set()
    
    # Load from useremails.csv
    try:
        with open('useremails.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip().lower()
                if email:
                    useremails_set.add(email)
                    useremails_metadata[email] = {
                        'chapter': row.get('chapter', '').strip(),
                        'squad': row.get('Current Squad', '').strip()
                    }
        print(f"Loaded {len(useremails_set)} emails from useremails.csv")
    except FileNotFoundError:
        print("Warning: useremails.csv not found. No email filtering will be applied.")
        return set(), {}
    except Exception as e:
        print(f"Error loading useremails.csv: {e}")
        return set(), {}
    
    # Check if useremails.csv was empty
    if not useremails_set:
        print("Warning: useremails.csv is empty or contains no valid emails. No email filtering will be applied.")
        return set(), {}
    
    # Load emails from User_Leaderboard file
    try:
        # Find User_Leaderboard file
        leaderboard_path = None
        for root, dirs, files in os.walk('.'):
            for file in files:
                if 'User_Leaderboard' in file and file.endswith('.csv'):
                    leaderboard_path = os.path.join(root, file)
                    break
            if leaderboard_path:
                break
        
        if leaderboard_path and os.path.exists(leaderboard_path):
            with open(leaderboard_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get('Email', '').strip().lower()
                    if email:
                        leaderboard_emails_set.add(email)
            print(f"Loaded {len(leaderboard_emails_set)} emails from User_Leaderboard file")
        else:
            print("Warning: User_Leaderboard CSV file not found.")
    except Exception as e:
        print(f"Warning: Error loading User_Leaderboard file: {e}")
    
    # Check if User_Leaderboard was empty
    if not leaderboard_emails_set:
        print("Warning: User_Leaderboard file is empty or contains no valid emails. No email filtering will be applied.")
        return set(), {}
    
    # Create INTERSECTION - only emails present in BOTH sets
    allowed_emails = useremails_set & leaderboard_emails_set
    
    # Check if intersection is empty
    if not allowed_emails:
        print("Warning: No emails found in the intersection of useremails.csv and User_Leaderboard. No email filtering will be applied.")
        return set(), {}
    
    # Only keep metadata for emails in the intersection
    metadata = {email: useremails_metadata[email] for email in allowed_emails if email in useremails_metadata}
    
    print(f"Total allowed emails (intersection): {len(allowed_emails)}")
    return allowed_emails, metadata


def load_usage_events(csv_path: str, allowed_emails: Set[str], 
                      date_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Dict[str, Any]]:
    """Load cursor_team_usage_events.csv and aggregate per user.
    
    Args:
        csv_path: Path to cursor_team_usage_events.csv
        allowed_emails: Set of allowed email addresses (lowercase)
        date_range: Optional tuple of (start_date, end_date) to filter by
        
    Returns:
        Dictionary mapping email (lowercase) to aggregated user data
    """
    print(f"Loading usage events from {csv_path}...")
    
    user_data = defaultdict(lambda: {
        'total_requests': 0,
        'total_cost': 0.0,
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'cache_read_tokens': 0,
        'cache_write_tokens': 0,
        'active_days': set(),
        'models_used': defaultdict(int),  # model -> count
        'kinds': defaultdict(int),  # kind -> count
    })
    
    filtered_count = 0
    date_filtered_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                try:
                    # Get user email (case-insensitive)
                    user_email = row.get('User', '').strip().lower()
                    if not user_email or user_email not in allowed_emails:
                        filtered_count += 1
                        continue
                    
                    # Parse date
                    date_str = row.get('Date', '').strip()
                    if not date_str:
                        continue
                    
                    # Parse ISO date format: "2025-12-10T12:58:46.229Z"
                    try:
                        date_str_clean = date_str.replace('Z', '+00:00')
                        dt = datetime.fromisoformat(date_str_clean)
                        event_date = dt.date()
                    except (ValueError, AttributeError) as e:
                        print(f"Warning: Could not parse date '{date_str}' on line {row_num}: {e}")
                        continue
                    
                    # Filter by date range if provided
                    if date_range:
                        if not (date_range[0] <= event_date <= date_range[1]):
                            date_filtered_count += 1
                            continue
                    
                    # Track active days
                    user_data[user_email]['active_days'].add(event_date)
                    
                    # Aggregate metrics
                    try:
                        user_data[user_email]['total_requests'] += 1
                        user_data[user_email]['total_cost'] += float(row.get('Cost', 0) or 0)
                        
                        # Input tokens (use "Input (w/ Cache Write)" as primary, fallback to "Input (w/o Cache Write)")
                        input_with_cache = int(row.get('Input (w/ Cache Write)', 0) or 0)
                        input_without_cache = int(row.get('Input (w/o Cache Write)', 0) or 0)
                        # Use input_with_cache if available, otherwise fallback to input_without_cache
                        total_input = input_with_cache if input_with_cache > 0 else input_without_cache
                        user_data[user_email]['total_input_tokens'] += total_input
                        
                        # Output tokens
                        user_data[user_email]['total_output_tokens'] += int(row.get('Output Tokens', 0) or 0)
                        
                        # Cache tokens
                        user_data[user_email]['cache_read_tokens'] += int(row.get('Cache Read', 0) or 0)
                        if input_with_cache > 0:
                            user_data[user_email]['cache_write_tokens'] += input_with_cache
                        
                        # Track model usage
                        model = row.get('Model', '').strip()
                        if model:
                            user_data[user_email]['models_used'][model] += 1
                        
                        # Track kind
                        kind = row.get('Kind', '').strip()
                        if kind:
                            user_data[user_email]['kinds'][kind] += 1
                            
                    except (ValueError, TypeError) as e:
                        print(f"Warning: Could not parse numeric value on line {row_num}: {e}")
                        continue
                        
                except Exception as e:
                    print(f"Warning: Error processing line {row_num}: {e}")
                    continue
        
        # Convert sets to counts and defaultdicts to dicts
        result = {}
        for email, data in user_data.items():
            result[email] = {
                'total_requests': data['total_requests'],
                'total_cost': round(data['total_cost'], 2),
                'total_input_tokens': data['total_input_tokens'],
                'total_output_tokens': data['total_output_tokens'],
                'cache_read_tokens': data['cache_read_tokens'],
                'cache_write_tokens': data['cache_write_tokens'],
                'active_days': len(data['active_days']),
                'models_used': dict(data['models_used']),
                'kinds': dict(data['kinds']),
            }
        
        print(f"Loaded usage events for {len(result)} users")
        if filtered_count > 0:
            print(f"  Filtered out {filtered_count} rows (email not in allowed list)")
        if date_filtered_count > 0:
            print(f"  Filtered out {date_filtered_count} rows (outside date range)")
        
        return result
        
    except FileNotFoundError:
        print(f"Error: File '{csv_path}' not found.")
        return {}
    except Exception as e:
        print(f"Error loading usage events: {e}")
        import traceback
        traceback.print_exc()
        return {}


def load_user_leaderboard(csv_path: str, allowed_emails: Set[str]) -> Dict[str, Dict[str, Any]]:
    """Load cursor_User_Leaderboard.csv and filter by allowed emails.
    
    Args:
        csv_path: Path to cursor_User_Leaderboard.csv
        allowed_emails: Set of allowed email addresses (lowercase)
        
    Returns:
        Dictionary mapping email (lowercase) to leaderboard data
    """
    print(f"Loading user leaderboard from {csv_path}...")
    
    leaderboard_data = {}
    filtered_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                try:
                    email = row.get('Email', '').strip().lower()
                    if not email:
                        continue
                    
                    if email not in allowed_emails:
                        filtered_count += 1
                        continue
                    
                    leaderboard_data[email] = {
                        'name': row.get('Name', '').strip(),
                        'agent_completions': int(row.get('Agent Completions', 0) or 0),
                        'agent_lines': int(row.get('Agent Lines', 0) or 0),
                        'tab_completions': int(row.get('Tab Completions', 0) or 0),
                        'tab_lines': int(row.get('Tab Lines', 0) or 0),
                        'ai_lines': int(row.get('Ai Lines', 0) or 0),
                        'favorite_model': row.get('Favorite Model', '').strip(),
                    }
                    
                except (ValueError, TypeError) as e:
                    print(f"Warning: Could not parse leaderboard data on line {row_num}: {e}")
                    continue
                except Exception as e:
                    print(f"Warning: Error processing leaderboard line {row_num}: {e}")
                    continue
        
        print(f"Loaded leaderboard data for {len(leaderboard_data)} users")
        if filtered_count > 0:
            print(f"  Filtered out {filtered_count} rows (email not in allowed list)")
        
        return leaderboard_data
        
    except FileNotFoundError:
        print(f"Error: File '{csv_path}' not found.")
        return {}
    except Exception as e:
        print(f"Error loading user leaderboard: {e}")
        import traceback
        traceback.print_exc()
        return {}


def load_repository_analytics(csv_path: str) -> List[Dict[str, Any]]:
    """Load cursor_Team_Repository_Analytics.csv.
    
    Args:
        csv_path: Path to cursor_Team_Repository_Analytics.csv
        
    Returns:
        List of dictionaries containing repository analytics data
    """
    print(f"Loading repository analytics from {csv_path}...")
    
    repo_data = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                try:
                    repo_data.append({
                        'repo_name': row.get('Repo Name', '').strip(),
                        'total_commits': int(row.get('Total Commits', 0) or 0),
                        'total_lines_added': int(row.get('Total Lines Added', 0) or 0),
                        'total_lines_deleted': int(row.get('Total Lines Deleted', 0) or 0),
                        'ai_lines_added': int(row.get('Ai Lines Added', 0) or 0),
                        'ai_lines_deleted': int(row.get('Ai Lines Deleted', 0) or 0),
                        'ai_impact_percentage': float(row.get('Ai Impact Percentage', 0) or 0),
                        'tab_lines_added': int(row.get('Tab Lines Added', 0) or 0),
                        'tab_lines_deleted': int(row.get('Tab Lines Deleted', 0) or 0),
                        'composer_lines_added': int(row.get('Composer Lines Added', 0) or 0),
                        'composer_lines_deleted': int(row.get('Composer Lines Deleted', 0) or 0),
                        'non_ai_lines_added': int(row.get('Non Ai Lines Added', 0) or 0),
                        'non_ai_lines_deleted': int(row.get('Non Ai Lines Deleted', 0) or 0),
                    })
                except (ValueError, TypeError) as e:
                    print(f"Warning: Could not parse repository data on line {row_num}: {e}")
                    continue
                except Exception as e:
                    print(f"Warning: Error processing repository line {row_num}: {e}")
                    continue
        
        print(f"Loaded analytics for {len(repo_data)} repositories")
        return repo_data
        
    except FileNotFoundError:
        print(f"Error: File '{csv_path}' not found.")
        return []
    except Exception as e:
        print(f"Error loading repository analytics: {e}")
        import traceback
        traceback.print_exc()
        return []


def merge_cursor_user_data(usage_events: Dict[str, Dict[str, Any]], 
                          leaderboard: Dict[str, Dict[str, Any]], 
                          allowed_emails: Set[str], 
                          email_metadata: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    """Merge usage events and leaderboard data by email.
    
    Only includes users from useremails.csv. Users with no activity will have zero values.
    
    Args:
        usage_events: Dictionary from load_usage_events()
        leaderboard: Dictionary from load_user_leaderboard()
        allowed_emails: Set of allowed emails
        email_metadata: Dictionary mapping email to metadata (chapter, squad)
        
    Returns:
        List of merged user dictionaries, one per allowed email
    """
    print("Merging cursor user data...")
    
    merged_users = []
    
    for email in allowed_emails:
        events = usage_events.get(email, {})
        leader = leaderboard.get(email, {})
        metadata = email_metadata.get(email, {})
        
        # Format models breakdown
        models_used = events.get('models_used', {})
        models_breakdown = ', '.join(
            f"{model}: {count}" 
            for model, count in sorted(models_used.items(), key=lambda x: x[1], reverse=True)
        ) if models_used else ''
        
        merged_users.append({
            'email': email,
            'chapter': metadata.get('chapter', ''),
            'squad': metadata.get('squad', ''),
            'total_requests': events.get('total_requests', 0),
            'total_cost': events.get('total_cost', 0.0),
            'total_input_tokens': events.get('total_input_tokens', 0),
            'total_output_tokens': events.get('total_output_tokens', 0),
            'cache_read_tokens': events.get('cache_read_tokens', 0),
            'cache_write_tokens': events.get('cache_write_tokens', 0),
            'active_days': events.get('active_days', 0),
            'models_breakdown': models_breakdown,
            'agent_completions': leader.get('agent_completions', 0),
            'agent_lines': leader.get('agent_lines', 0),
            'tab_completions': leader.get('tab_completions', 0),
            'tab_lines': leader.get('tab_lines', 0),
            'ai_lines': leader.get('ai_lines', 0),
            'favorite_model': leader.get('favorite_model', ''),
            'name': leader.get('name', ''),
        })
    
    print(f"Merged data for {len(merged_users)} users")
    return merged_users

