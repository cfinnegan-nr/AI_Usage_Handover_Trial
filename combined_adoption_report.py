#!/usr/bin/env python3
"""
Combined AI Adoption Report

This script combines GitHub Copilot usage stats and AI Workbench (API) usage stats
to generate comprehensive adoption-focused reports with metrics like:
- Daily Active Users (DAU) and Monthly Active Users (MAU)
- User consistency rates (active days / business days)
- Daily adoption coverage
- Requests per active user-day
- Adoption distribution and percentiles

Usage:
  python combined_adoption_report.py --github-json githubusage.json --workbench-json api_usage.json --month 2025-09
"""

import json
import csv
import argparse
import math
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Set, Tuple, Optional
import os
import calendar


def load_allowed_emails_and_metadata() -> Tuple[Set[str], Dict[str, Dict[str, str]]]:
    """Load allowed emails and metadata (chapter, squad, manager, target_threshold) from useremails.csv file."""
    try:
        emails = set()
        metadata = {}
        with open('useremails.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip()
                if email:
                    emails.add(email)
                    metadata[email] = {
                        'chapter': row.get('chapter', '').strip(),
                        'squad': row.get('Current Squad', '').strip(),
                        'manager': row.get('Manager', '').strip(),
                        'target_threshold': row.get('Target_Threshold', '').strip()
                    }
        print(
            f"Loaded {len(emails)} allowed emails with metadata from useremails.csv")
        return emails, metadata
    except FileNotFoundError:
        print("Warning: useremails.csv not found. No email filtering will be applied.")
        return set(), {}
    except Exception as e:
        print(f"Error loading useremails.csv: {e}")
        return set(), {}


# Load allowed emails and metadata from CSV file
ALLOWED_EMAILS, EMAIL_METADATA = load_allowed_emails_and_metadata()


class CombinedAdoptionAnalyzer:
    """Analyzes combined GitHub and Workbench usage for adoption metrics."""

    def __init__(self):
        self.email_mappings = {}
        self.load_email_mappings()

    def load_email_mappings(self):
        """Load email mappings from JSON file if it exists."""
        try:
            with open('email_to_github_mappings.json', 'r') as f:
                self.email_mappings = json.load(f)
            print(
                f"Loaded email mappings for {len(self.email_mappings)} users")
        except FileNotFoundError:
            print(
                "No email mappings file found. GitHub usernames will be used as identifiers.")
        except json.JSONDecodeError as e:
            print(f"Error loading email mappings: {e}")

    def load_workbench_questions(self, csv_path: Optional[str]) -> Dict[str, int]:
        """Load workbench questions count from CSV file if provided."""
        if not csv_path:
            print("No workbench questions CSV provided. All users will have 0 questions.")
            return {}

        if not os.path.exists(csv_path):
            print(
                f"Warning: Workbench questions CSV '{csv_path}' not found. All users will have 0 questions.")
            return {}

        questions_data = {}
        filtered_users = []
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get('email', '').lower().strip()
                    # Try both column names: workbench_questions and workbench_prompts
                    questions = row.get('workbench_questions') or row.get(
                        'workbench_prompts', '0')
                    try:
                        questions = int(questions)
                    except (ValueError, TypeError):
                        questions = 0

                    if email:
                        # Check if email is in allowed list
                        if email in ALLOWED_EMAILS:
                            questions_data[email] = questions
                        else:
                            # Track filtered users (not in allowed list)
                            filtered_users.append(email)

            print(
                f"Loaded workbench questions for {len(questions_data)} users from CSV")

            if filtered_users:
                print(
                    f"\nWARNING: {len(filtered_users)} users from workbench questions CSV are NOT in useremails.csv:")
                print(
                    "These users will be excluded from the report. Consider adding them to useremails.csv if they are new hires:")
                for email in sorted(filtered_users):
                    print(f"  - {email}")
                print()
        except Exception as e:
            print(f"Error loading workbench questions CSV: {e}")
            return {}

        return questions_data

    def load_github_data(self, file_path: str, date_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Dict[str, Any]]:
        """Load GitHub Copilot usage data and aggregate by user email.
        If date_range is provided, only include records whose 'day' falls within the range.
        """
        print(f"Loading GitHub data from {file_path}...")

        user_data = defaultdict(lambda: {
            'github_login': '',
            'active_days': set(),
            'total_requests': 0,
            'code_generated': 0,  # Total events generating code
            'code_accepted': 0,  # Total events where code was accepted
            'loc_added': 0,  # Total lines of code added
            'loc_deleted': 0,  # Total lines of code deleted
            'used_agent': False,
            'roo_in_use': False,
            'models_requests': defaultdict(int),  # model -> request count
            'features_requests': defaultdict(int),  # feature -> request count
        })
        unmapped_github_users = set()

        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    user_login = data.get('user_login', '')
                    day = data.get('day', '')

                    if not user_login:
                        continue

                    # If date_range provided, filter by day
                    if date_range and day:
                        try:
                            day_date = datetime.strptime(
                                day, '%Y-%m-%d').date()
                            if not (date_range[0] <= day_date <= date_range[1]):
                                continue
                        except ValueError:
                            continue

                    # Get email from mapping
                    email = self.email_mappings.get(
                        user_login, user_login).lower()
                    # Warn if email is missing or not a valid email, but ignore if "NOT FS" in email (case-insensitive)
                    if not email or ('@' not in email and 'not fs' not in email.lower()):
                        unmapped_github_users.add(user_login)

                    user = user_data[email]
                    user['github_login'] = user_login

                    # Track active days
                    if day:
                        user['active_days'].add(day)

                    # Aggregate metrics
                    user['total_requests'] += data.get(
                        'user_initiated_interaction_count', 0)
                    user['code_generated'] += data.get(
                        'code_generation_activity_count', 0)
                    user['code_accepted'] += data.get(
                        'code_acceptance_activity_count', 0)

                    # Track actual lines of code added/deleted
                    user['loc_added'] += data.get('loc_added_sum', 0)
                    user['loc_deleted'] += data.get('loc_deleted_sum', 0)

                    if data.get('used_agent', False):
                        user['used_agent'] = True

                    # Track feature requests from totals_by_feature
                    features = data.get('totals_by_feature', [])
                    if isinstance(features, list):
                        for feature_data in features:
                            if isinstance(feature_data, dict):
                                feature_name = str(
                                    feature_data.get('feature', ''))
                                # Use user_initiated_interaction_count as the primary metric
                                feature_count = feature_data.get(
                                    'user_initiated_interaction_count', 0)

                                if feature_name:
                                    user['features_requests'][feature_name] += feature_count

                    # Check for Roo usage and track model requests from totals_by_model_feature
                    model_features = data.get('totals_by_model_feature', [])
                    if isinstance(model_features, list):
                        for mf in model_features:
                            if isinstance(mf, dict):
                                mf_feature = str(mf.get('feature', ''))
                                mf_model = str(mf.get('model', ''))
                                mf_count = mf.get('count', 0)

                                # Track model requests
                                if mf_model:
                                    user['models_requests'][mf_model] += mf_count

                                # Check for Roo usage
                                if 'chat_panel_unknown_mode' in mf_feature.lower() and mf_model and mf_model.lower() != 'unknown':
                                    user['roo_in_use'] = True

                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON on line {line_num}: {e}")
                    continue

        print(
            f"Loaded GitHub data for {len(user_data)} users (date filtered: {'yes' if date_range else 'no'})")
        if unmapped_github_users:
            print(
                f"\nWARNING: {len(unmapped_github_users)} GitHub users do not have a mapped non-empty email field:")
            for user_login in sorted(unmapped_github_users):
                print(f"  - {user_login}")
            print()
        return dict(user_data)

    def load_workbench_data(self, file_path: str, date_range: Tuple[datetime, datetime]) -> Dict[str, Dict[str, Any]]:
        """Load AI Workbench (API) usage data and aggregate by user email."""
        print(f"Loading Workbench data from {file_path}...")
        print(f"  Date range filter: {date_range[0]} to {date_range[1]}")

        user_data = defaultdict(lambda: {
            'active_days': set(),
            'api_requests_total': 0,
            'api_requests_normal': 0,
            'api_requests_embedding': 0,
            'spend_total': 0.0,
            'models_used': set(),
            'models_requests': defaultdict(int),  # model -> request count
            'cache_read_tokens': 0,
            'cache_creation_tokens': 0,
        })

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        # Try parsing as JSON array first
        try:
            parsed = json.loads(content)
            
            # Handle case where JSON is an object with SQL query as key containing array of records
            # Structure: {"SELECT ...": [record1, record2, ...]}
            if isinstance(parsed, dict) and len(parsed) == 1:
                # Get the first (and only) value
                first_value = next(iter(parsed.values()))
                if isinstance(first_value, list):
                    # This is the array of records we want
                    records = first_value
                    print(f"  Detected SQL query key structure, extracted {len(records)} records from nested array")
                else:
                    records = [parsed]
            elif isinstance(parsed, list):
                records = parsed
            else:
                records = [parsed]
        except json.JSONDecodeError:
            # Try newline-delimited JSON
            records = []
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    try:
                        line_parsed = json.loads(line)
                        # Handle nested structure in each line too
                        if isinstance(line_parsed, dict) and len(line_parsed) == 1:
                            first_value = next(iter(line_parsed.values()))
                            if isinstance(first_value, list):
                                records.extend(first_value)
                            else:
                                records.append(line_parsed)
                        elif isinstance(line_parsed, list):
                            records.extend(line_parsed)
                        else:
                            records.append(line_parsed)
                    except json.JSONDecodeError:
                        pass

        # DIAGNOSTIC: Track filtering statistics
        total_records = len(records)
        filtered_no_email = 0
        filtered_no_date = 0
        filtered_date_parse_error = 0
        filtered_date_out_of_range = 0
        processed_records = 0
        total_api_requests = 0
        sample_record_keys = set()
        sample_dates = []
        sample_emails = set()

        print(f"  Total records loaded from JSON: {total_records}")
        if total_records > 0:
            # Show sample record structure
            sample_record = records[0]
            sample_record_keys = set(sample_record.keys())
            print(f"  Sample record keys: {sorted(sample_record_keys)}")

        # Process records
        for record in records:
            # Track record keys for diagnostics
            sample_record_keys.update(record.keys())

            email = record.get('email', '').lower()
            if not email:
                filtered_no_email += 1
                continue

            # Track sample emails
            if len(sample_emails) < 5:
                sample_emails.add(email)

            # Parse and check date - MUST be within range to process record
            date_str = record.get('date', '')
            if not date_str:
                filtered_no_date += 1
                continue

            try:
                date_str = date_str.replace('Z', '+00:00')
                dt_utc = datetime.fromisoformat(date_str)

                # Convert from US Eastern time to UK time
                # US Eastern is UTC-5 (EST) or UTC-4 (EDT)
                # UK is UTC+0 (GMT) or UTC+1 (BST)
                # Net difference: add 5-6 hours to shift from US to UK
                # Using 5 hours as a reasonable offset
                dt_uk = dt_utc + timedelta(hours=5)
                date_parsed = dt_uk.date()
            except (ValueError, AttributeError) as e:
                filtered_date_parse_error += 1
                if filtered_date_parse_error <= 3:  # Show first 3 parse errors
                    print(f"  DIAGNOSTIC: Date parse error for record with email '{email}': date_str='{date_str}', error={e}")
                continue

            # Track sample dates
            if len(sample_dates) < 10:
                sample_dates.append((date_parsed, email))

            # Skip records outside date range
            if not (date_range[0] <= date_parsed <= date_range[1]):
                filtered_date_out_of_range += 1
                if filtered_date_out_of_range <= 3:  # Show first 3 out-of-range dates
                    print(f"  DIAGNOSTIC: Date out of range for '{email}': {date_parsed} (range: {date_range[0]} to {date_range[1]})")
                continue

            # Add this date to active days
            user_data[email]['active_days'].add(date_parsed)

            # Classify model
            model = record.get('model', '')
            is_embedding = self._is_embedding_model(model)

            if model:
                user_data[email]['models_used'].add(model)

            # Aggregate metrics
            api_requests = record.get('api_requests', 0)
            user_data[email]['api_requests_total'] += api_requests
            user_data[email]['spend_total'] += record.get('spend', 0.0)
            total_api_requests += api_requests

            # Track cache usage
            user_data[email]['cache_read_tokens'] += record.get(
                'cache_read_input_tokens', 0)
            user_data[email]['cache_creation_tokens'] += record.get(
                'cache_creation_input_tokens', 0)

            # Track model request counts
            if model:
                user_data[email]['models_requests'][model] += api_requests

            if is_embedding:
                user_data[email]['api_requests_embedding'] += api_requests
            else:
                user_data[email]['api_requests_normal'] += api_requests

            processed_records += 1

        # DIAGNOSTIC: Print filtering statistics
        print(f"\n  === WORKBENCH DATA LOADING DIAGNOSTICS ===")
        print(f"  Total records in file: {total_records}")
        print(f"  Records filtered - no email: {filtered_no_email}")
        print(f"  Records filtered - no date: {filtered_no_date}")
        print(f"  Records filtered - date parse error: {filtered_date_parse_error}")
        print(f"  Records filtered - date out of range: {filtered_date_out_of_range}")
        print(f"  Records successfully processed: {processed_records}")
        print(f"  Total API requests aggregated: {total_api_requests}")
        print(f"  Unique users with data: {len(user_data)}")
        
        if sample_record_keys:
            print(f"  Record field names found: {sorted(sample_record_keys)}")
        if sample_emails:
            print(f"  Sample emails found: {sorted(list(sample_emails))[:5]}")
        if sample_dates:
            print(f"  Sample dates found (first 10):")
            for d, e in sample_dates[:10]:
                print(f"    {d} ({e})")
        
        # Check if api_requests field exists
        if 'api_requests' not in sample_record_keys:
            print(f"  *** WARNING: 'api_requests' field not found in record keys!")
            print(f"  *** Available fields: {sorted(sample_record_keys)}")
            print(f"  *** This may explain why API Users count is zero!")
            # Check for alternative field names
            possible_request_fields = [k for k in sample_record_keys if 'request' in k.lower() or 'count' in k.lower() or 'usage' in k.lower()]
            if possible_request_fields:
                print(f"  *** Possible alternative request fields found: {possible_request_fields}")
                # Show sample values from first record
                if records:
                    sample = records[0]
                    print(f"  *** Sample values from first record:")
                    for field in possible_request_fields:
                        print(f"      {field}: {sample.get(field, 'N/A')}")
        
        # Show users with non-zero api_requests_total
        users_with_requests = {email: data['api_requests_total'] 
                               for email, data in user_data.items() 
                               if data['api_requests_total'] > 0}
        if users_with_requests:
            print(f"  Users with API requests > 0: {len(users_with_requests)}")
            print(f"  Sample users with requests (first 5):")
            for email, count in list(users_with_requests.items())[:5]:
                print(f"    {email}: {count} requests")
        else:
            print(f"  *** WARNING: No users have api_requests_total > 0!")
            print(f"  *** This explains why API Users count is zero!")
        
        print(f"  ============================================\n")

        print(f"Loaded Workbench data for {len(user_data)} users")
        return dict(user_data)

    def _is_embedding_model(self, model: str) -> bool:
        """Check if model is an embedding model."""
        if not model:
            return False

        model_lower = model.lower()
        if 'embed' in model_lower or 'embedding' in model_lower:
            return True

        embedding_prefixes = [
            'text-embedding-', 'amazon.titan-embed-', 'titan-embed-', 'cohere.embed-']
        return any(model_lower.startswith(prefix) for prefix in embedding_prefixes)

    def calculate_business_days(self, start_date: datetime, end_date: datetime) -> int:
        """Calculate number of business days (weekdays) in date range."""
        business_days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday=0, Sunday=6
                business_days += 1
            current += timedelta(days=1)
        return business_days

    def merge_user_data(self, github_data: Dict[str, Dict], workbench_data: Dict[str, Dict],
                        date_range: Tuple[datetime, datetime], workbench_questions: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
        """Merge GitHub and Workbench data by user email, including all ALLOWED_EMAILS even if no activity."""
        print("Merging user data...")

        # Default to empty dict if not provided
        if workbench_questions is None:
            workbench_questions = {}

        # Include ALL allowed emails, even those with no activity
        # This ensures users with zero usage still appear in the report
        all_emails = ALLOWED_EMAILS
        active_emails = set(github_data.keys()) | set(workbench_data.keys())
        print(
            f"Including all {len(all_emails)} allowed users ({len(active_emails & ALLOWED_EMAILS)} with activity)")
        
        # DIAGNOSTIC: Check workbench data
        print(f"\n  === MERGE DIAGNOSTICS ===")
        print(f"  GitHub data users: {len(github_data)}")
        print(f"  Workbench data users: {len(workbench_data)}")
        if workbench_data:
            wb_users_with_requests = {email: data.get('api_requests_total', 0) 
                                     for email, data in workbench_data.items() 
                                     if data.get('api_requests_total', 0) > 0}
            print(f"  Workbench users with api_requests_total > 0: {len(wb_users_with_requests)}")
            if wb_users_with_requests:
                print(f"  Sample workbench users with requests (first 5):")
                for email, count in list(wb_users_with_requests.items())[:5]:
                    print(f"    {email}: {count} requests")
            else:
                print(f"  *** WARNING: No workbench users have api_requests_total > 0!")
        else:
            print(f"  *** WARNING: workbench_data is empty!")
        print(f"  =========================\n")
        
        business_days = self.calculate_business_days(
            date_range[0], date_range[1])

        merged_users = []

        for email in all_emails:
            gh = github_data.get(email, {})
            wb = workbench_data.get(email, {})

            # Combine active days from both sources
            github_active_days = gh.get('active_days', set())
            workbench_active_days = wb.get('active_days', set())

            # Convert GitHub days (strings) to date objects for comparison
            github_dates = set()
            for day_str in github_active_days:
                try:
                    github_dates.add(datetime.strptime(
                        day_str, '%Y-%m-%d').date())
                except ValueError:
                    pass

            combined_active_days = github_dates | workbench_active_days
            days_active = len(combined_active_days)
            github_days_active = len(github_dates)

            # Debug: Print details for specific user (remove after debugging)
            # if 'divyaa.manimaran@symphonyai.com' in email.lower():  # Replace with your actual email
            #    print(f"\nDEBUG for {email}:")
            #    print(
            #        f"  GitHub days: {len(github_dates)} - {sorted(github_dates)}")
            #    print(
            #        f"  Workbench days: {len(workbench_active_days)} - {sorted(workbench_active_days)}")
            #    print(
            #        f"  Combined days: {len(combined_active_days)} - {sorted(combined_active_days)}")
            #    print(f"  Date range: {date_range[0]} to {date_range[1]}")

            # Calculate consistency rate (capped at 100%)
            consistency_rate = min(100.0, (days_active / business_days *
                                           100)) if business_days > 0 else 0

            # Apply same logic as github_stats_analyzer.py:
            # GitHub requests should be max(days_active, actual_requests)
            # This ensures users with low request counts still show meaningful activity
            github_requests_raw = gh.get('total_requests', 0)
            github_requests_adjusted = max(
                github_days_active, github_requests_raw)

            # Calculate total requests (non-embedding only)
            total_requests_non_embedding = github_requests_adjusted + \
                wb.get('api_requests_normal', 0)

            # Keep total requests for reference (including embedding)
            total_requests = github_requests_adjusted + \
                wb.get('api_requests_total', 0)

            # Determine if user is active (at least 1 day OR has workbench questions)
            has_workbench_questions = workbench_questions.get(email, 0) > 0
            is_active = days_active > 0 or has_workbench_questions

            # Apply additional Roo detection criteria:
            # Only mark as roo_in_use if github_requests < days_active
            # This filters out cases where the user has high GitHub activity
            roo_in_use = gh.get('roo_in_use', False) and (
                github_requests_raw < github_days_active)

            # Combine model request counts from both GitHub and Workbench
            combined_models = defaultdict(int)
            gh_models = gh.get('models_requests', {})
            wb_models = wb.get('models_requests', {})

            for model, count in gh_models.items():
                combined_models[model] += count
            for model, count in wb_models.items():
                combined_models[model] += count

            # Format model breakdown as "model1: count1, model2: count2"
            models_breakdown = ', '.join(
                f"{model}: {count}" for model, count in sorted(combined_models.items(), key=lambda x: x[1], reverse=True)
            ) if combined_models else ''

            # Get feature request counts from GitHub
            features_requests = gh.get('features_requests', {})
            features_breakdown = ', '.join(
                f"{feature}: {count}" for feature, count in sorted(features_requests.items(), key=lambda x: x[1], reverse=True)
            ) if features_requests else ''

            # Get chapter and squad metadata
            metadata = EMAIL_METADATA.get(email, {})
            chapter = metadata.get('chapter', '')
            squad = metadata.get('squad', '')

            merged_users.append({
                'email': email,
                'chapter': chapter,
                'squad': squad,
                'github_login': gh.get('github_login', ''),
                'days_active': days_active,
                'business_days': business_days,
                'consistency_rate': round(consistency_rate, 1),
                'is_active': is_active,

                # GitHub metrics (adjusted to match github_stats_analyzer.py logic)
                'github_requests': github_requests_adjusted,
                'code_generated': gh.get('code_generated', 0),
                'code_accepted': gh.get('code_accepted', 0),
                'github_acceptance_rate': round((gh.get('code_accepted', 0) / gh.get('code_generated', 0) * 100) if gh.get('code_generated', 0) > 0 else 0, 1),
                'loc_added': gh.get('loc_added', 0),
                'loc_deleted': gh.get('loc_deleted', 0),
                'used_agent': gh.get('used_agent', False),
                'roo_in_use': roo_in_use,

                # Workbench metrics
                'workbench_requests_total': wb.get('api_requests_total', 0),
                'workbench_requests_normal': wb.get('api_requests_normal', 0),
                'workbench_requests_embedding': wb.get('api_requests_embedding', 0),
                'workbench_spend': round(wb.get('spend_total', 0.0), 2),
                'workbench_models': ', '.join(sorted(wb.get('models_used', set()))),
                'cache_read_tokens': wb.get('cache_read_tokens', 0),
                'cache_creation_tokens': wb.get('cache_creation_tokens', 0),
                'uses_prompt_caching': (wb.get('cache_read_tokens', 0) > 0 or wb.get('cache_creation_tokens', 0) > 0),

                # Combined metrics (non-embedding only)
                'total_requests': total_requests_non_embedding,

                # Model and feature breakdowns
                'models_breakdown': models_breakdown,
                'features_breakdown': features_breakdown,

                # Workbench questions
                'workbench_questions': workbench_questions.get(email, 0),
            })

        # Sort by days active descending
        # Sort by days_active descending, then by total requests (wb + github + api + wb_normal) descending
        merged_users.sort(
            key=lambda x: (
                x['days_active'],
                x.get('workbench_questions', 0) +
                x.get('github_requests', 0) +
                x.get('workbench_requests_normal', 0)
            ),
            reverse=True
        )

        print(f"Merged data for {len(merged_users)} users")
        return merged_users

    def calculate_adoption_metrics(self, merged_users: List[Dict[str, Any]],
                                   date_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Calculate adoption-focused summary metrics."""

        # Filter to active users only
        active_users = [u for u in merged_users if u['is_active']]

        total_users = len(merged_users)
        mau = len(active_users)  # Monthly Active Users

        # Calculate consistency metrics (Agentic Consistency - based on days_active)
        consistency_rates = [u['consistency_rate'] for u in active_users]
        consistency_rates.sort()

        def percentile(data, p):
            if not data:
                return 0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f < len(data) - 1 else f
            return data[f] + (k - f) * (data[c] - data[f])

        median_consistency = percentile(
            consistency_rates, 50) if consistency_rates else 0
        mean_consistency = (sum(consistency_rates) /
                            len(consistency_rates)) if consistency_rates else 0
        p75_consistency = percentile(
            consistency_rates, 75) if consistency_rates else 0
        p90_consistency = percentile(
            consistency_rates, 90) if consistency_rates else 0

        business_days = self.calculate_business_days(
            date_range[0], date_range[1])

        # Calculate 15+ active days threshold (for Agentic consistency metrics)
        users_15_plus_days = sum(
            1 for u in active_users if u['days_active'] / business_days >= 0.65)

        # Calculate WB Consistency metrics (based on max of days_active and wb_days_active)
        # First, we need to calculate wb_days_active for each user (done later in the function)
        # So we'll calculate WB consistency after wb_days_active is set

        # Calculate intensity metrics (excluding embedding requests)
        # Embedding requests are for indexing/search, not actual AI assistance
        total_requests_non_embedding = sum(
            u['github_requests'] + u['workbench_requests_normal']
            for u in active_users
        )
        avg_requests_per_user = (
            total_requests_non_embedding / total_users) if total_users > 0 else 0

        # Calculate median and p75 of requests per user across users
        requests_per_user_list = [u['total_requests']
                                  for u in active_users if u['total_requests'] > 0]
        requests_per_user_list.sort()

        median_requests_per_user = percentile(
            requests_per_user_list, 50) if requests_per_user_list else 0
        p75_requests_per_user = percentile(
            requests_per_user_list, 75) if requests_per_user_list else 0

        # GitHub-specific metrics
        github_users = sum(1 for u in active_users if u['github_requests'] > 0)
        agent_users = sum(1 for u in active_users if u['used_agent'])
        roo_users = sum(1 for u in active_users if u['roo_in_use'])

        # Calculate GitHub acceptance rate (using request counts for rate calculation)
        total_code_generated = sum(u['code_generated'] for u in active_users)
        total_code_accepted = sum(u['code_accepted'] for u in active_users)
        github_acceptance_rate = (
            total_code_accepted / total_code_generated * 100) if total_code_generated > 0 else 0

        # Calculate total lines of code metrics
        total_loc_added = sum(u['loc_added'] for u in active_users)
        total_loc_deleted = sum(u['loc_deleted'] for u in active_users)
        total_loc_net = total_loc_added - total_loc_deleted

        # Workbench-specific metrics
        workbench_users = sum(
            1 for u in active_users if u['workbench_requests_total'] > 0)
        
        # DIAGNOSTIC: Check workbench_users calculation
        print(f"\n  === WORKBENCH USERS CALCULATION DIAGNOSTICS ===")
        print(f"  Total active_users: {len(active_users)}")
        print(f"  Users with workbench_requests_total > 0: {workbench_users}")
        
        # Check workbench_requests_total values
        wb_request_counts = [u['workbench_requests_total'] for u in active_users]
        non_zero_wb_requests = [count for count in wb_request_counts if count > 0]
        print(f"  Users with workbench_requests_total > 0: {len(non_zero_wb_requests)}")
        if non_zero_wb_requests:
            print(f"  Sample workbench_requests_total values: {sorted(non_zero_wb_requests, reverse=True)[:10]}")
        else:
            print(f"  *** WARNING: All users have workbench_requests_total = 0!")
            print(f"  *** This explains why API Users count is zero!")
            # Show sample users to verify data structure
            print(f"  Sample active users (first 5) workbench_requests_total values:")
            for u in active_users[:5]:
                print(f"    {u.get('email', 'unknown')}: workbench_requests_total={u.get('workbench_requests_total', 0)}")
        print(f"  ================================================\n")
        
        embedding_users = sum(
            1 for u in active_users if u['workbench_requests_embedding'] > 0)
        prompt_caching_users = sum(
            1 for u in active_users if u.get('uses_prompt_caching', False))

        # Workbench questions metrics
        total_workbench_questions = sum(
            u['workbench_questions'] for u in active_users)
        users_with_workbench_questions = sum(
            1 for u in active_users if u['workbench_questions'] > 0)
        avg_workbench_questions_per_user = (
            total_workbench_questions / total_users) if total_users > 0 else 0
        avg_workbench_questions_per_user_per_business_day = (
            total_workbench_questions /
            (total_users * business_days) if total_users * business_days > 0 else 0
        )

        # Calculate WB Days Active for each user (second pass after avg is known)
        for user in merged_users:
            wb_requests = user.get('workbench_questions', 0)
            if avg_workbench_questions_per_user_per_business_day > 0:
                wb_days_active = min(
                    wb_requests / avg_workbench_questions_per_user_per_business_day,
                    business_days
                )
            else:
                wb_days_active = 0
            user['wb_days_active'] = math.ceil(wb_days_active)

        # Calculate WB Consistency metrics (based on max of days_active and wb_days_active)
        wb_consistency_rates = []
        for user in active_users:
            max_days = max(user.get('days_active', 0),
                           user.get('wb_days_active', 0))
            wb_consistency_rate = min(
                100.0, (max_days / business_days * 100)) if business_days > 0 else 0
            wb_consistency_rates.append(wb_consistency_rate)

        wb_consistency_rates.sort()

        wb_median_consistency = percentile(
            wb_consistency_rates, 50) if wb_consistency_rates else 0
        wb_mean_consistency = (sum(wb_consistency_rates) /
                               len(wb_consistency_rates)) if wb_consistency_rates else 0
        wb_p75_consistency = percentile(
            wb_consistency_rates, 75) if wb_consistency_rates else 0

        # Calculate 15+ days threshold for WB consistency (using max of days_active and wb_days_active)
        wb_users_15_plus_days = sum(
            1 for u in active_users if max(u.get('days_active', 0), u.get('wb_days_active', 0)) / business_days >= 0.65
        )

        # Sort by days active descending, then by total requests (wb + github + api + wb_normal) descending
        merged_users.sort(
            key=lambda x: (
                max(x.get('days_active', 0), x.get('wb_days_active', 0)),
                x.get('days_active', 0),
                x.get('workbench_questions', 0) +
                x.get('github_requests', 0) +
                x.get('workbench_requests_normal', 0)
            ),
            reverse=True
        )

        # Users using both platforms
        both_platforms = sum(1 for u in active_users
                             if u['github_requests'] > 0 and u['workbench_requests_total'] > 0)

        return {
            'report_period': f"{date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')}",
            'business_days': business_days,
            'total_users': total_users,
            'mau': mau,
            'adoption_rate': round((mau / total_users * 100) if total_users > 0 else 0, 1),

            # Agentic Consistency metrics (based on days_active)
            'median_consistency': round(median_consistency, 1),
            'mean_consistency': round(mean_consistency, 1),
            'p75_consistency': round(p75_consistency, 1),
            'p90_consistency': round(p90_consistency, 1),
            'users_15_plus_days': users_15_plus_days,
            'pct_15_plus_days': round((users_15_plus_days / total_users * 100) if total_users > 0 else 0, 1),

            # WB Consistency metrics (based on max of days_active and wb_days_active)
            'wb_median_consistency': round(wb_median_consistency, 1),
            'wb_mean_consistency': round(wb_mean_consistency, 1),
            'wb_p75_consistency': round(wb_p75_consistency, 1),
            'wb_users_15_plus_days': wb_users_15_plus_days,
            'wb_pct_15_plus_days': round((wb_users_15_plus_days / total_users * 100) if total_users > 0 else 0, 1),

            # Intensity metrics (non-embedding only)
            'avg_requests_per_user': round(avg_requests_per_user, 2),
            'median_requests_per_user': round(median_requests_per_user, 2),
            'p75_requests_per_user': round(p75_requests_per_user, 2),
            'total_requests_non_embedding': total_requests_non_embedding,
            'total_workbench_questions': total_workbench_questions,
            'avg_workbench_questions_per_user': round(avg_workbench_questions_per_user, 2),
            'avg_workbench_questions_per_user_per_business_day': round(avg_workbench_questions_per_user_per_business_day, 2),
            'github_acceptance_rate': round(github_acceptance_rate, 1),
            'total_code_generated': total_code_generated,
            'total_code_accepted': total_code_accepted,
            'total_loc_added': total_loc_added,
            'total_loc_deleted': total_loc_deleted,
            'total_loc_net': total_loc_net,

            # Platform-specific
            'github_users': github_users,
            'workbench_users': workbench_users,
            'both_platforms_users': both_platforms,
            'agent_users': agent_users,
            'roo_users': roo_users,
            'embedding_users': embedding_users,
            'prompt_caching_users': prompt_caching_users,

            # Workbench questions metrics
            'users_with_workbench_questions': users_with_workbench_questions,

        }

    def generate_csv_report(self, merged_users: List[Dict[str, Any]],
                            adoption_metrics: Dict[str, Any], output_path: str):
        """Generate CSV report with adoption metrics."""
        print(f"Generating CSV report: {output_path}")

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write summary section
            writer.writerow(['ADOPTION SUMMARY STATISTICS'])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(
                ['Report Period', adoption_metrics['report_period']])
            writer.writerow(['Business Days in Period',
                            adoption_metrics['business_days']])
            writer.writerow(['Total Users', adoption_metrics['total_users']])
            writer.writerow(
                ['Monthly Active Users (MAU)', adoption_metrics['mau']])
            writer.writerow(
                ['Adoption Rate (%)', adoption_metrics['adoption_rate']])
            writer.writerow([])

            writer.writerow(
                ['AGENTIC CONSISTENCY METRICS (based on days_active)'])
            writer.writerow(['Median User Consistency (%)',
                            adoption_metrics['median_consistency']])
            writer.writerow(['Mean User Consistency (%)',
                            adoption_metrics['mean_consistency']])
            writer.writerow(['75th Percentile Consistency (%)',
                            adoption_metrics['p75_consistency']])
            writer.writerow(['Users with 65% Active Days',
                            f"{adoption_metrics['users_15_plus_days']} ({adoption_metrics['pct_15_plus_days']}%)"])
            writer.writerow([])

            writer.writerow(
                ['CONSISTENCY METRICS (based on max of days_active and wb_days_active)'])
            writer.writerow(['Median User Consistency (%)',
                            adoption_metrics['wb_median_consistency']])
            writer.writerow(['Mean User Consistency (%)',
                            adoption_metrics['wb_mean_consistency']])
            writer.writerow(['75th Percentile Consistency (%)',
                            adoption_metrics['wb_p75_consistency']])
            writer.writerow(['Users with 65% Active Days',
                            f"{adoption_metrics['wb_users_15_plus_days']} ({adoption_metrics['wb_pct_15_plus_days']}%)"])
            writer.writerow([])

            writer.writerow(['INTENSITY METRICS'])
            writer.writerow(['Total Requests',
                            adoption_metrics['total_requests_non_embedding']])
            writer.writerow(['Mean Requests per User',
                            adoption_metrics['avg_requests_per_user']])
            writer.writerow(['Median Requests per User',
                            adoption_metrics['median_requests_per_user']])
            writer.writerow(['75th Percentile Requests per User',
                            adoption_metrics['p75_requests_per_user']])
            writer.writerow(['Total Workbench Questions',
                            adoption_metrics['total_workbench_questions']])
            writer.writerow(['Mean Workbench Questions per Active User',
                            adoption_metrics['avg_workbench_questions_per_user']])
            writer.writerow(['GitHub Acceptance Rate (%)',
                            adoption_metrics['github_acceptance_rate']])
            writer.writerow(['GitHub Total Lines of Code Added',
                            adoption_metrics['total_loc_added']])
            writer.writerow(['GitHub Total Lines of Code Deleted',
                            adoption_metrics['total_loc_deleted']])
            writer.writerow(['GitHub Net Lines of Code',
                            adoption_metrics['total_loc_net']])
            writer.writerow([])

            writer.writerow(['PLATFORM USAGE'])
            writer.writerow(
                ['GitHub Copilot Users', adoption_metrics['github_users']])
            writer.writerow(['API Users', adoption_metrics['workbench_users']])
            writer.writerow(
                ['Both Platforms Users', adoption_metrics['both_platforms_users']])
            writer.writerow(
                ['GitHub Agent Users', adoption_metrics['agent_users']])
            writer.writerow(['Embedding/Indexing Users',
                            adoption_metrics['embedding_users']])
            writer.writerow(['Prompt Caching Users',
                            adoption_metrics['prompt_caching_users']])
            writer.writerow(['Workbench Questions Users',
                            adoption_metrics['users_with_workbench_questions']])
            writer.writerow([])
            writer.writerow([])

            # Write per-user statistics
            writer.writerow(['PER-USER ADOPTION STATISTICS'])
            writer.writerow([
                'Email', 'Chapter', 'Current Squad', 'GitHub Login', 'Days Active', 'WB Days Active', 'Workbench Questions', 'API Normal',
                'GitHub Requests', 'GH Acceptance Rate (%)', 'GH LOC Added', 'GH LOC Deleted', 'GitHub Agent', 'GitHub via Roo',
                'API Embedding', 'Prompt Caching', 'Total Spend',
                'Models Breakdown', 'GH Features Breakdown'
            ])

            for user in merged_users:
                writer.writerow([
                    user['email'],
                    user['chapter'],
                    user['squad'],
                    user['github_login'],
                    user['days_active'],
                    user.get('wb_days_active', 0),
                    user['workbench_questions'],
                    user['workbench_requests_normal'],
                    user['github_requests'],
                    user['github_acceptance_rate'],
                    user['loc_added'],
                    user['loc_deleted'],
                    'Yes' if user['used_agent'] else 'No',
                    'Yes' if user['roo_in_use'] else 'No',
                    user['workbench_requests_embedding'],
                    'Yes' if user.get('uses_prompt_caching', False) else 'No',
                    user['workbench_spend'],
                    user['models_breakdown'],
                    user['features_breakdown']
                ])

    def generate_trends_csv_report(self, merged_users: List[Dict[str, Any]],
                                   month: Optional[str], output_path: str):
        """Generate trends CSV report with per-user data only, including Year/Month columns.
        
        This method creates a CSV file containing only the per-user statistics rows,
        with Year and Month columns prepended. It does NOT include any summary
        statistics sections.
        
        If the output file already exists:
        - If no rows exist for the same Year/Month combination, new data is appended
        - If rows exist for the same Year/Month combination, those rows are replaced
          while preserving all other Year/Month rows
        
        Args:
            merged_users: List of user dictionaries with adoption statistics
            month: Month string in YYYY-MM format (e.g., '2025-11')
            output_path: Path for output CSV file
            
        Raises:
            ValueError: If month parameter is invalid or missing
            IOError: If file cannot be written
        """
        print(f"Generating trends CSV report: {output_path}")
        
        try:
            # Parse month to get year and month abbreviation
            year_str, month_abbrev = parse_month_to_year_and_abbrev(month)
            
            # Define the header row with updated column names
            header_row = [
                'Manager', 'Year', 'Month', 'Email', 'Chapter', 'Current Squad', 'GitHub Login', 
                'Target', 'Days Active', 'WB Days Active', 'Workbench Questions', 'API Normal (Non-Cursor)',
                'GitHub Requests', 'GH Acceptance Rate (%)', 'GH LOC Added', 'GH LOC Deleted', 
                'GitHub Agent', 'GitHub via Roo', 'API Embedding', 'Prompt Caching', 
                'Total Spend', 'Models Breakdown', 'GH Features Breakdown',
                'Cursor Total Requests', 'Cursor Agent Completions', 'Cursor LOC'
            ]
            
            # Prepare new data rows
            new_rows = []
            users_written = 0
            users_skipped = 0
            
            for user in merged_users:
                try:
                    # Look up Manager and Target from metadata
                    email = user['email']
                    user_metadata = EMAIL_METADATA.get(email, {})
                    manager = user_metadata.get('manager', '').strip() or 'Unknown'
                    target_threshold = user_metadata.get('target_threshold', '').strip()
                    # Convert target_threshold to int, default to 400 if missing or invalid
                    try:
                        target_value = int(target_threshold) if target_threshold else 400
                    except (ValueError, TypeError):
                        target_value = 400
                    
                    row = [
                        manager,  # Manager column (first column)
                        year_str,  # Year column
                        month_abbrev,  # Month column
                        email,
                        user['chapter'],
                        user['squad'],
                        user['github_login'],
                        target_value,  # Target column (8th column)
                        user['days_active'],
                        user.get('wb_days_active', 0),
                        user['workbench_questions'],
                        user['workbench_requests_normal'],
                        user['github_requests'],
                        user['github_acceptance_rate'],
                        user['loc_added'],
                        user['loc_deleted'],
                        'Yes' if user['used_agent'] else 'No',
                        'Yes' if user['roo_in_use'] else 'No',
                        user['workbench_requests_embedding'],
                        'Yes' if user.get('uses_prompt_caching', False) else 'No',
                        user['workbench_spend'],
                        user['models_breakdown'],
                        user['features_breakdown'],
                        0,  # Cursor Total Requests (default)
                        0,  # Cursor Agent Completions (default)
                        0   # Cursor LOC (default)
                    ]
                    new_rows.append(row)
                    users_written += 1
                except KeyError as e:
                    # Log warning for missing user data fields but continue processing
                    print(f"Warning: Missing field '{e}' for user {user.get('email', 'unknown')}. Skipping user.")
                    users_skipped += 1
                    continue
                except Exception as e:
                    # Log error for user row but continue processing other users
                    print(f"Error preparing row for user {user.get('email', 'unknown')}: {e}")
                    users_skipped += 1
                    continue
            
            # Check if file exists and handle accordingly
            file_exists = os.path.exists(output_path)
            
            if file_exists:
                # Read existing file
                existing_rows = []
                existing_header = None
                year_col_idx = None
                month_col_idx = None
                
                try:
                    with open(output_path, 'r', newline='', encoding='utf-8') as csvfile:
                        reader = csv.reader(csvfile)
                        existing_header = next(reader, None)
                        
                        if existing_header:
                            # Find Year and Month column indices
                            try:
                                year_col_idx = existing_header.index('Year')
                                month_col_idx = existing_header.index('Month')
                            except ValueError:
                                # If Year/Month columns don't exist, treat as new file
                                print(f"Warning: Existing file '{output_path}' does not have Year/Month columns. Creating new file.")
                                file_exists = False
                                existing_rows = []
                            else:
                                # Read all existing data rows
                                for row in reader:
                                    if len(row) > max(year_col_idx, month_col_idx):
                                        existing_rows.append(row)
                
                except Exception as e:
                    print(f"Warning: Error reading existing file '{output_path}': {e}")
                    print("  Creating new file instead.")
                    file_exists = False
                    existing_rows = []
                
                if file_exists and existing_rows:
                    # Check if any rows exist for this Year/Month combination
                    matching_rows_exist = any(
                        row[year_col_idx] == year_str and row[month_col_idx] == month_abbrev
                        for row in existing_rows
                    )
                    
                    if matching_rows_exist:
                        # Remove existing rows for this Year/Month combination
                        filtered_rows = [
                            row for row in existing_rows
                            if not (row[year_col_idx] == year_str and row[month_col_idx] == month_abbrev)
                        ]
                        print(f"Found existing rows for {year_str}/{month_abbrev}. Replacing {len(existing_rows) - len(filtered_rows)} rows.")
                        existing_rows = filtered_rows
                    else:
                        print(f"No existing rows found for {year_str}/{month_abbrev}. Appending new data.")
                
                # Merge existing rows with new rows
                all_rows = existing_rows + new_rows
                
                # Ensure header matches expected format (update if needed)
                if existing_header:
                    # CRITICAL: Normalize row lengths FIRST before any positional insertions
                    # This ensures all rows have the same length, preventing insertion errors
                    original_header_len = len(existing_header)
                    for row in existing_rows:
                        # Pad rows to match original header length
                        while len(row) < original_header_len:
                            row.append('')
                        # Truncate if too long (shouldn't happen, but be safe)
                        if len(row) > original_header_len:
                            row[:] = row[:original_header_len]
                    
                    # Update column names if needed
                    # Update 'API Normal' to 'API Normal (Non-Cursor)' if present
                    if 'API Normal' in existing_header:
                        api_normal_idx = existing_header.index('API Normal')
                        existing_header[api_normal_idx] = 'API Normal (Non-Cursor)'
                    
                    # Ensure Manager column exists at the beginning
                    manager_added = False
                    if 'Manager' not in existing_header:
                        existing_header.insert(0, 'Manager')
                        # Insert default 'Unknown' for Manager in existing rows
                        # Now safe because rows are normalized
                        for row in existing_rows:
                            row.insert(0, 'Unknown')
                        manager_added = True
                    
                    # Ensure Target column exists at position 7 (8th column, 0-indexed)
                    # After Manager, Year, Month, Email, Chapter, Current Squad, GitHub Login
                    if 'Target' not in existing_header:
                        # Find insertion point: after GitHub Login
                        # Expected order: Manager (0), Year (1), Month (2), Email (3), 
                        # Chapter (4), Current Squad (5), GitHub Login (6), Target (7)
                        # Try to find GitHub Login column to determine insertion point
                        try:
                            github_login_idx = existing_header.index('GitHub Login')
                            target_insert_idx = github_login_idx + 1
                        except ValueError:
                            # GitHub Login not found, try to find Days Active as fallback
                            try:
                                days_active_idx = existing_header.index('Days Active')
                                target_insert_idx = days_active_idx
                            except ValueError:
                                # Fallback: insert at position 7
                                target_insert_idx = 7
                        
                        existing_header.insert(target_insert_idx, 'Target')
                        # Insert default 400 for Target in existing rows
                        # Now safe because rows are normalized
                        for row in existing_rows:
                            row.insert(target_insert_idx, 400)
                    
                    # Ensure new Cursor columns exist
                    cursor_columns = ['Cursor Total Requests', 'Cursor Agent Completions', 'Cursor LOC']
                    missing_cursor_cols = [col for col in cursor_columns if col not in existing_header]
                    
                    if missing_cursor_cols:
                        existing_header.extend(missing_cursor_cols)
                        # Pad existing rows with default values for new columns
                        for row in existing_rows:
                            row.extend([''] * len(missing_cursor_cols))
                    
                    # Final normalization to match final header length
                    header_len = len(existing_header)
                    
                    # Pad existing rows if needed (shouldn't be needed after normalization, but be safe)
                    for row in existing_rows:
                        while len(row) < header_len:
                            row.append('')
                        # Truncate if too long (shouldn't happen, but be safe)
                        if len(row) > header_len:
                            row[:] = row[:header_len]
                    
                    # Pad new rows if needed
                    for row in new_rows:
                        while len(row) < header_len:
                            row.append('')
                        # Truncate if too long (shouldn't happen, but be safe)
                        if len(row) > header_len:
                            row[:] = row[:header_len]
                    
                    header_row = existing_header
                else:
                    # No existing header, use new header
                    header_row = header_row
            else:
                # File doesn't exist, use new header and rows
                all_rows = new_rows
            
            # Write the file
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(header_row)
                
                # Write all rows
                for row in all_rows:
                    writer.writerow(row)
            
            # Report actual count of users written (not total users processed)
            if users_skipped > 0:
                print(f"Generated trends CSV report with {users_written} users ({users_skipped} skipped due to errors)")
            else:
                print(f"Generated trends CSV report with {users_written} users")
            
            if file_exists:
                print(f"Preserved {len(existing_rows)} existing rows from other months")
            
        except ValueError as e:
            # Re-raise ValueError with context
            error_msg = f"Error generating trends CSV report: {e}"
            print(error_msg)
            raise ValueError(error_msg) from e
        except IOError as e:
            # Handle file I/O errors
            error_msg = f"Error writing trends CSV file '{output_path}': {e}"
            print(error_msg)
            raise IOError(error_msg) from e
        except Exception as e:
            # Catch-all for any other unexpected errors
            error_msg = f"Unexpected error generating trends CSV report: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            raise

    def generate_html_report(self, merged_users: List[Dict[str, Any]],
                             adoption_metrics: Dict[str, Any], output_path: str):
        """Generate HTML report with adoption metrics."""
        print(f"Generating HTML report: {output_path}")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Combined AI Adoption Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .timestamp {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
            font-style: italic;
        }}
        .summary {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .summary h2 {{
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 20px;
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .section-title {{
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
            margin: 20px 0 10px 0;
            padding-bottom: 5px;
            border-bottom: 2px solid #3498db;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background-color: white;
            font-size: 0.85em;
        }}
        th, td {{
            padding: 10px 8px;
            text-align: center;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
            position: sticky;
            top: 0;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{
            background-color: #2980b9;
        }}
        th.sortable::after {{
            content: ' ⇅';
            opacity: 0.5;
            font-size: 0.7em;
        }}
        th.sort-asc::after {{
            content: ' ▲';
            opacity: 1;
            font-size: 0.7em;
        }}
        th.sort-desc::after {{
            content: ' ▼';
            opacity: 1;
            font-size: 0.7em;
        }}
        .sort-info {{
            text-align: center;
            margin: 10px 0;
            padding: 10px;
            background-color: #e8f4fd;
            border-radius: 5px;
            font-size: 0.9em;
            color: #2c3e50;
        }}
        td:first-child {{
            text-align: left;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        tr:hover {{
            background-color: #e8f4fd;
        }}
        .yes {{
            color: #27ae60;
            font-weight: bold;
        }}
        .no {{
            color: #e74c3c;
        }}
        /* Consistency row colouring removed to keep table styling neutral */
        .table-container {{
            overflow-x: auto;
            margin-top: 20px;
            max-height: 600px;
            overflow-y: auto;
            position: relative;
        }}
        .table-container table {{
            position: relative;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Combined AI Adoption Report</h1>
        <div class="timestamp">Generated on {timestamp}</div>
        <div class="timestamp">Report Period: {adoption_metrics['report_period']}</div>
        
        <div class="summary">
            <h2>Summary</h2>
            
            <div class="section-title">Overall Adoption</div>
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['total_users']}</div>
                    <div class="stat-label">Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['mau']}</div>
                    <div class="stat-label">Monthly Active Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['adoption_rate']}%</div>
                    <div class="stat-label">Adoption Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['business_days']}</div>
                    <div class="stat-label">Business Days</div>
                </div>
            </div>
            <div class="section-title">Consistency Metrics (based on max of days_active and wb_days_active)</div>
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['wb_mean_consistency']}%</div>
                    <div class="stat-label">Mean Consistency</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['wb_median_consistency']}%</div>
                    <div class="stat-label">Median Consistency</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['wb_p75_consistency']}%</div>
                    <div class="stat-label">75th Percentile</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['wb_users_15_plus_days']}</div>
                    <div class="stat-label">65% Active Days ({adoption_metrics['wb_pct_15_plus_days']}%)</div>
                </div>
            </div>
            <div class="section-title">Agentic Consistency Metrics (based on days_active)</div>
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['mean_consistency']}%</div>
                    <div class="stat-label">Mean Consistency</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['median_consistency']}%</div>
                    <div class="stat-label">Median Consistency</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['p75_consistency']}%</div>
                    <div class="stat-label">75th Percentile</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['users_15_plus_days']}</div>
                    <div class="stat-label">65% Active Days ({adoption_metrics['pct_15_plus_days']}%)</div>
                </div>
            </div>
            
            <div class="section-title">Platform Usage</div>
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['github_users']}</div>
                    <div class="stat-label">GitHub Copilot Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['workbench_users']}</div>
                    <div class="stat-label">API Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['both_platforms_users']}</div>
                    <div class="stat-label">Both Platforms</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['agent_users']}</div>
                    <div class="stat-label">GitHub Agent Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['embedding_users']}</div>
                    <div class="stat-label">Code Indexing Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['prompt_caching_users']}</div>
                    <div class="stat-label">Prompt Caching Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['users_with_workbench_questions']}</div>
                    <div class="stat-label">WB Questions Users</div>
                </div>
            </div>
            
            <div class="section-title">Intensity Metrics</div>
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['total_requests_non_embedding']:,}</div>
                    <div class="stat-label">Total Agentic Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['avg_requests_per_user']}</div>
                    <div class="stat-label">Mean Req/User</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['median_requests_per_user']}</div>
                    <div class="stat-label">Median Req/User</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['p75_requests_per_user']}</div>
                    <div class="stat-label">P75 Req/User</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['total_workbench_questions']:,}</div>
                    <div class="stat-label">Total WB Questions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['avg_workbench_questions_per_user_per_business_day']:.2f}</div>
                    <div class="stat-label">Mean WB Questions/User/Day</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['github_acceptance_rate']}%</div>
                    <div class="stat-label">GH Acceptance Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['total_loc_added']:,}</div>
                    <div class="stat-label">GH LOC Added</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{adoption_metrics['total_loc_deleted']:,}</div>
                    <div class="stat-label">GH LOC Deleted</div>
                </div>
            </div>
        </div>
        
        <h2>Per-User Adoption Statistics</h2>
        <div class="sort-info">
            <strong>Default Sort:</strong>
            <select id="defaultSortSelect" style="padding: 5px; margin: 0 10px; border-radius: 4px; border: 1px solid #3498db;">
                <option value="days_active">By All Days Active (Default)</option>
                <option value="total_requests">By Total Requests</option>
            </select>
            <button id="resetSort" style="padding: 5px 15px; background-color: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;">Reset to Default</button>
            <br><br>
            <strong>Filter by Chapter:</strong>
            <select id="chapterFilter" style="padding: 5px; margin: 0 10px; border-radius: 4px; border: 1px solid #3498db; min-width: 150px;">
                <option value="">All Chapters</option>
            </select>
            <span id="filterDisplay" style="margin-left: 10px; font-style: italic; color: #7f8c8d;"></span>
            <br><br>
            <strong>Sort Info:</strong> Click on column headers to sort. Hold Shift and click additional headers for multi-column sort. Current sort: <span id="sortDisplay">All Days Active (descending)</span>
        </div>
        <div class="table-container">
            <table id="adoptionTable">
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Chapter</th>
                        <th>Current Squad</th>
                        <th>GitHub Login</th>
                        <th>API/GH Days Active</th>
                        <th>WB Days Active</th>
                        <th>WB Requests</th>
                        <th>API Requests</th>
                        <th>GitHub Requests</th>
                        <th>GH Accept Rate (%)</th>
                        <th>GH LOC Added</th>
                        <th>GH LOC Deleted</th>
                        <th>GH Agent Used</th>
                        <th>GH via Roo</th>
                        <th>API Embed Requests</th>
                        <th>API Prompt Caching</th>
                        <th>API Spend</th>
                        <th>Agentic Models Breakdown</th>
                        <th>GH Features Breakdown</th>
                    </tr>
                </thead>
                <tbody>"""

        # Calculate the 15-day threshold percentage based on actual business days
        business_days = adoption_metrics['business_days']

        for user in merged_users:
            # Determine consistency class
            # threshold_15_days = percentage equivalent of 15 days for this reporting period
            consistency_class = ''
            if max(user.get('days_active', 0), user.get('wb_days_active', 0)) / business_days >= 0.8:
                consistency_class = 'high-consistency'
            elif max(user.get('days_active', 0), user.get('wb_days_active', 0)) / business_days >= 0.65:
                consistency_class = 'medium-consistency'
            else:
                consistency_class = 'low-consistency'

            uses_caching = user.get('uses_prompt_caching', False)
            total_requests = user.get('workbench_questions', 0) + user.get(
                'github_requests', 0) + user.get('workbench_requests_normal', 0)
            max_days = max(user.get('days_active', 0),
                           user.get('wb_days_active', 0))
            html += f"""
                    <tr data-total-requests="{total_requests}" data-max-days="{max_days}" data-days-active="{user['days_active']}">
                        <td>{user['email']}</td>
                        <td>{user['chapter']}</td>
                        <td>{user['squad']}</td>
                        <td>{user['github_login']}</td>
                        <td>{user['days_active']}</td>
                        <td>{user.get('wb_days_active', 0)}</td>
                        <td>{user['workbench_questions']}</td>
                        <td>{user['workbench_requests_normal']:,}</td>
                        <td>{user['github_requests']:,}</td>
                        <td>{user['github_acceptance_rate']}%</td>
                        <td>{user['loc_added']:,}</td>
                        <td>{user['loc_deleted']:,}</td>
                        <td class="{'yes' if user['used_agent'] else 'no'}">{'Yes' if user['used_agent'] else 'No'}</td>
                        <td class="{'yes' if user['roo_in_use'] else 'no'}">{'Yes' if user['roo_in_use'] else 'No'}</td>
                        <td>{user['workbench_requests_embedding']:,}</td>
                        <td class="{'yes' if uses_caching else 'no'}">{'Yes' if uses_caching else 'No'}</td>
                        <td>${user['workbench_spend']:.2f}</td>
                        <td style="text-align: left; font-size: 0.8em;">{user['models_breakdown']}</td>
                        <td style="text-align: left; font-size: 0.8em;">{user['features_breakdown']}</td>
                    </tr>"""

        html += """
                </tbody>
            </table>
        </div>
        
        <script>
        class TableSorter {
            constructor(tableId) {
                this.table = document.getElementById(tableId);
                this.tbody = this.table.querySelector('tbody');
                this.headers = this.table.querySelectorAll('th');
                this.sortState = [];
                this.defaultSortMode = 'days_active';
                this.chapterFilter = '';
                this.init();
            }
            
            init() {
                this.headers.forEach((header, index) => {
                    header.classList.add('sortable');
                    header.addEventListener('click', (e) => this.handleSort(e, index));
                });
                
                // Setup default sort dropdown
                const sortSelect = document.getElementById('defaultSortSelect');
                sortSelect.addEventListener('change', (e) => this.applyDefaultSort(e.target.value));
                
                // Setup reset button
                const resetButton = document.getElementById('resetSort');
                resetButton.addEventListener('click', () => {
                    const sortSelect = document.getElementById('defaultSortSelect');
                    this.applyDefaultSort(sortSelect.value);
                });
                
                // Populate chapter filter dropdown
                this.populateChapterFilter();
                
                // Setup chapter filter dropdown
                const chapterFilterSelect = document.getElementById('chapterFilter');
                chapterFilterSelect.addEventListener('change', (e) => this.applyChapterFilter(e.target.value));
                
                // Initialize with default sort
                this.applyDefaultSort('days_active');
            }
            
            populateChapterFilter() {
                const rows = Array.from(this.tbody.querySelectorAll('tr'));
                const chapters = new Set();
                
                rows.forEach(row => {
                    const chapterCell = row.cells[1]; // Chapter is the second column (index 1)
                    const chapterText = chapterCell.textContent.trim();
                    if (chapterText) {
                        chapters.add(chapterText);
                    }
                });
                
                // Sort chapters alphabetically
                const sortedChapters = Array.from(chapters).sort();
                
                // Populate dropdown
                const chapterFilterSelect = document.getElementById('chapterFilter');
                sortedChapters.forEach(chapter => {
                    const option = document.createElement('option');
                    option.value = chapter;
                    option.textContent = chapter;
                    chapterFilterSelect.appendChild(option);
                });
            }
            
            applyChapterFilter(filterValue) {
                this.chapterFilter = filterValue.trim();
                const rows = Array.from(this.tbody.querySelectorAll('tr'));
                let visibleCount = 0;
                
                rows.forEach(row => {
                    const chapterCell = row.cells[1]; // Chapter is the second column (index 1)
                    const chapterText = chapterCell.textContent.trim();
                    
                    if (this.chapterFilter === '' || chapterText === this.chapterFilter) {
                        row.style.display = '';
                        visibleCount++;
                    } else {
                        row.style.display = 'none';
                    }
                });
                
                // Update filter display
                const filterDisplay = document.getElementById('filterDisplay');
                if (this.chapterFilter === '') {
                    filterDisplay.textContent = '';
                } else {
                    filterDisplay.textContent = `Showing ${visibleCount} of ${rows.length} users`;
                }
            }
            
            applyDefaultSort(mode) {
                this.defaultSortMode = mode;
                this.sortState = [];
                
                if (mode === 'total_requests') {
                    // Sort by total requests (data attribute)
                    this.sortByDataAttribute('total-requests', 'desc');
                    this.updateSortDisplay('Total Requests (descending)');
                } else {
                    // Default: Sort by max days, then days_active, then total requests
                    this.sortByComplexDefault();
                    this.updateSortDisplay('All Days Active (descending)');
                }
                
                this.updateHeaders();
            }
            
            sortByDataAttribute(attribute, direction) {
                const rows = Array.from(this.tbody.querySelectorAll('tr'));
                rows.sort((a, b) => {
                    const aVal = parseFloat(a.getAttribute('data-' + attribute)) || 0;
                    const bVal = parseFloat(b.getAttribute('data-' + attribute)) || 0;
                    return direction === 'desc' ? bVal - aVal : aVal - bVal;
                });
                rows.forEach(row => this.tbody.appendChild(row));
            }
            
            sortByComplexDefault() {
                const rows = Array.from(this.tbody.querySelectorAll('tr'));
                rows.sort((a, b) => {
                    // Sort by: max_days desc, days_active desc, total_requests desc
                    const aMaxDays = parseFloat(a.getAttribute('data-max-days')) || 0;
                    const bMaxDays = parseFloat(b.getAttribute('data-max-days')) || 0;
                    if (aMaxDays !== bMaxDays) return bMaxDays - aMaxDays;
                    
                    const aDaysActive = parseFloat(a.getAttribute('data-days-active')) || 0;
                    const bDaysActive = parseFloat(b.getAttribute('data-days-active')) || 0;
                    if (aDaysActive !== bDaysActive) return bDaysActive - aDaysActive;
                    
                    const aTotalReq = parseFloat(a.getAttribute('data-total-requests')) || 0;
                    const bTotalReq = parseFloat(b.getAttribute('data-total-requests')) || 0;
                    return bTotalReq - aTotalReq;
                });
                rows.forEach(row => this.tbody.appendChild(row));
            }
            
            handleSort(e, columnIndex) {
                if (e.shiftKey) {
                    // Multi-column sort with Shift
                    const existingSort = this.sortState.find(s => s.column === columnIndex);
                    if (existingSort) {
                        // Toggle direction if column already in sort
                        existingSort.direction = existingSort.direction === 'asc' ? 'desc' : 'asc';
                    } else {
                        // Add new column to sort
                        this.addSortColumn(columnIndex, 'asc');
                    }
                } else {
                    // Single column sort - determine direction based on current state
                    const existingSort = this.sortState.find(s => s.column === columnIndex);
                    const newDirection = existingSort && existingSort.direction === 'asc' ? 'desc' : 'asc';
                    this.sortState = [];
                    this.addSortColumn(columnIndex, newDirection);
                }
                
                this.updateHeaders();
                this.performSort();
                this.updateSortDisplay();
            }
            
            addSortColumn(columnIndex, direction) {
                const existing = this.sortState.findIndex(s => s.column === columnIndex);
                if (existing !== -1) {
                    this.sortState[existing].direction = direction;
                } else {
                    this.sortState.push({ column: columnIndex, direction: direction });
                }
            }
            
            updateHeaders() {
                this.headers.forEach((header, index) => {
                    header.classList.remove('sort-asc', 'sort-desc');
                    const sort = this.sortState.find(s => s.column === index);
                    if (sort) {
                        header.classList.add(sort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
                    }
                });
            }
            
            performSort() {
                const rows = Array.from(this.tbody.querySelectorAll('tr'));
                
                rows.sort((a, b) => {
                    for (const sort of this.sortState) {
                        const aCell = a.cells[sort.column].textContent.trim();
                        const bCell = b.cells[sort.column].textContent.trim();
                        
                        // Try numeric sort first
                        const aNum = parseFloat(aCell.replace(/[^0-9.-]/g, ''));
                        const bNum = parseFloat(bCell.replace(/[^0-9.-]/g, ''));
                        
                        let comparison = 0;
                        if (!isNaN(aNum) && !isNaN(bNum)) {
                            comparison = aNum - bNum;
                        } else {
                            comparison = aCell.localeCompare(bCell);
                        }
                        
                        if (comparison !== 0) {
                            return sort.direction === 'asc' ? comparison : -comparison;
                        }
                    }
                    return 0;
                });
                
                rows.forEach(row => this.tbody.appendChild(row));
            }
            
            updateSortDisplay(customText) {
                const sortDisplay = document.getElementById('sortDisplay');
                if (customText) {
                    sortDisplay.textContent = customText;
                } else if (this.sortState.length === 0) {
                    sortDisplay.textContent = 'All Days Active (descending)';
                } else {
                    const displayParts = this.sortState.map(s => {
                        const header = this.headers[s.column].textContent.trim();
                        const direction = s.direction === 'asc' ? '↑' : '↓';
                        return header + ' ' + direction;
                    });
                    sortDisplay.textContent = displayParts.join(', ');
                }
            }
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            new TableSorter('adoptionTable');
        });
        </script>
        
        <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
            <h3 style="margin-top: 0;">Legend</h3>
            <p><strong>Consistency Rate:</strong> (Days Active / Business Days) × 100</p>
            <p><strong>Platforms:</strong> Agentic = API/GH, GH = GitHub Copilot, WB = Workbench</p>
        </div>
    </div>
</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)


def extract_github_report_date_range(file_path: str) -> Optional[Tuple[datetime, datetime]]:
    """Extract report_start_day and report_end_day from GitHub JSON file.

    Returns the date range from the GitHub report metadata, or None if not found.
    """
    try:
        with open(file_path, 'r') as f:
            # Read first line to get report metadata
            first_line = f.readline().strip()
            if first_line:
                data = json.loads(first_line)
                report_start = data.get('report_start_day')
                report_end = data.get('report_end_day')

                if report_start and report_end:
                    start_date = datetime.strptime(
                        report_start, '%Y-%m-%d').date()
                    end_date = datetime.strptime(report_end, '%Y-%m-%d').date()
                    print(
                        f"GitHub report data available from {start_date} to {end_date}")
                    return start_date, end_date
    except (FileNotFoundError, ValueError, KeyError) as e:
        print(
            f"Warning: Could not extract report date range from GitHub file: {e}")

    return None


def derive_date_range(month: Optional[str], start_date: Optional[str],
                      end_date: Optional[str]) -> Tuple[datetime, datetime]:
    """Derive date range from month or explicit dates."""
    if month:
        year, month_num = map(int, month.split('-'))
        first_day = datetime(year, month_num, 1).date()
        last_day_num = calendar.monthrange(year, month_num)[1]
        last_day = datetime(year, month_num, last_day_num).date()
        return first_day, last_day
    elif start_date and end_date:
        return (datetime.strptime(start_date, '%Y-%m-%d').date(),
                datetime.strptime(end_date, '%Y-%m-%d').date())
    else:
        raise ValueError(
            "Must provide either --month or both --start-date and --end-date")


def constrain_date_range(requested_range: Tuple[datetime, datetime],
                         github_range: Optional[Tuple[datetime, datetime]]) -> Tuple[datetime, datetime]:
    """Constrain the requested date range to the GitHub report's available data range.

    This ensures we only compare data for periods where we have complete GitHub data.
    """
    if not github_range:
        return requested_range

    # Constrain to the intersection of requested and available ranges
    constrained_start = max(requested_range[0], github_range[0])
    constrained_end = min(requested_range[1], github_range[1])

    if constrained_start > constrained_end:
        raise ValueError(
            f"Requested date range {requested_range[0]} to {requested_range[1]} "
            f"does not overlap with GitHub report range {github_range[0]} to {github_range[1]}"
        )

    if constrained_start != requested_range[0] or constrained_end != requested_range[1]:
        print("WARNING: Date range constrained to GitHub report availability:")
        print(f"   Requested: {requested_range[0]} to {requested_range[1]}")
        print(f"   Constrained: {constrained_start} to {constrained_end}")

    return constrained_start, constrained_end


def parse_month_to_year_and_abbrev(month: Optional[str]) -> Tuple[str, str]:
    """Parse month parameter (YYYY-MM format) to extract year and month abbreviation.
    
    Args:
        month: Month string in YYYY-MM format (e.g., '2025-11')
        
    Returns:
        Tuple of (year_str, month_abbrev) where:
        - year_str: Year in YYYY format (e.g., '2025')
        - month_abbrev: Month abbreviation in MMM format (e.g., 'Nov')
        
    Raises:
        ValueError: If month format is invalid or month is None/empty
    """
    if not month:
        raise ValueError("Month parameter is required for trends CSV generation")
    
    try:
        # Parse YYYY-MM format
        year, month_num = map(int, month.split('-'))
        
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
        raise ValueError(f"Invalid month format '{month}'. Expected YYYY-MM format (e.g., '2025-11'). Error: {e}")
    except Exception as e:
        raise ValueError(f"Error parsing month '{month}': {e}")


def main():
    """Main function to run the combined adoption analyzer."""
    parser = argparse.ArgumentParser(
        description='Generate combined AI adoption report from GitHub and Workbench data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze September 2025
  python combined_adoption_report.py --github-json githubusage.json --workbench-json api_usage.json --month 2025-09
  
  # Explicit date range
  python combined_adoption_report.py --github-json githubusage.json --workbench-json api_usage.json --start-date 2025-09-01 --end-date 2025-09-30
        """
    )

    parser.add_argument('--workbench-questions-csv',
                        help='Path to CSV file with workbench questions count (optional)')
    parser.add_argument('--github-json', required=True,
                        help='Path to GitHub Copilot usage JSON file')
    parser.add_argument('--workbench-json', required=True,
                        help='Path to Workbench (API) usage JSON file')
    parser.add_argument('--month',
                        help='Month in YYYY-MM format (alternative to start/end dates)')
    parser.add_argument('--start-date',
                        help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end-date',
                        help='End date in YYYY-MM-DD format')
    parser.add_argument('--csv-output', default='combined_adoption_report.csv',
                        help='Path for CSV output (default: combined_adoption_report.csv)')
    parser.add_argument('--html-output', default='combined_adoption_report.html',
                        help='Path for HTML output (default: combined_adoption_report.html)')

    args = parser.parse_args()

    # Define input and output directories
    input_dir = 'AI_Usage_Input'
    output_dir = 'AI_Usage_Output'
    
    # Ensure output directory exists
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory '{output_dir}' ready")
    except Exception as e:
        print(f"Error: Could not create output directory '{output_dir}': {e}")
        return 1
    
    # Construct input file paths with AI_Usage_Input prefix
    try:
        github_json_path = os.path.join(input_dir, args.github_json)
        workbench_json_path = os.path.join(input_dir, args.workbench_json)
        
        # Handle optional workbench questions CSV
        workbench_questions_csv_path = None
        if args.workbench_questions_csv:
            workbench_questions_csv_path = os.path.join(input_dir, args.workbench_questions_csv)
    except Exception as e:
        print(f"Error constructing input file paths: {e}")
        return 1

    # Validate input files exist
    if not os.path.exists(github_json_path):
        print(f"Error: GitHub JSON file '{github_json_path}' not found.")
        print(f"  Expected location: {os.path.abspath(github_json_path)}")
        return 1

    if not os.path.exists(workbench_json_path):
        print(f"Error: Workbench JSON file '{workbench_json_path}' not found.")
        print(f"  Expected location: {os.path.abspath(workbench_json_path)}")
        return 1
    
    # Warn if optional workbench questions CSV is provided but doesn't exist
    if workbench_questions_csv_path and not os.path.exists(workbench_questions_csv_path):
        print(f"Warning: Workbench questions CSV '{workbench_questions_csv_path}' not found.")
        print(f"  Expected location: {os.path.abspath(workbench_questions_csv_path)}")
        print("  Continuing without workbench questions data...")
        workbench_questions_csv_path = None

    try:
        # Derive requested date range
        requested_date_range = derive_date_range(
            args.month, args.start_date, args.end_date)
        print(
            f"\nRequested analysis period: {requested_date_range[0]} to {requested_date_range[1]}")

        # Extract GitHub report's actual data availability range
        github_report_range = extract_github_report_date_range(
            github_json_path)

        # Constrain date range to GitHub report availability
        date_range = constrain_date_range(
            requested_date_range, github_report_range)

        # Initialize analyzer
        analyzer = CombinedAdoptionAnalyzer()

        # Load data from both sources (apply date_range filtering where supported)
        github_data = analyzer.load_github_data(github_json_path, date_range)
        workbench_data = analyzer.load_workbench_data(
            workbench_json_path, date_range)

        # Load workbench questions if CSV provided (no date filtering - CSV has no date column assume exported as such)
        workbench_questions = analyzer.load_workbench_questions(
            workbench_questions_csv_path)

        # Merge user data
        merged_users = analyzer.merge_user_data(
            github_data, workbench_data, date_range, workbench_questions)

        # Calculate adoption metrics
        adoption_metrics = analyzer.calculate_adoption_metrics(
            merged_users, date_range)

        # Construct output file paths with AI_Usage_Output prefix
        try:
            csv_output_path = os.path.join(output_dir, args.csv_output)
            html_output_path = os.path.join(output_dir, args.html_output)
            trends_csv_path = os.path.join(output_dir, 'fs-eng-ai-usage-trends.csv')
        except Exception as e:
            print(f"Error constructing output file paths: {e}")
            return 1

        # Determine month for trends CSV (use args.month if provided, otherwise derive from date_range)
        trends_month = args.month
        if not trends_month:
            # Derive month from date_range start date
            try:
                start_date = date_range[0]
                trends_month = f"{start_date.year}-{start_date.month:02d}"
                print(f"Derived month '{trends_month}' from date range for trends CSV")
            except Exception as e:
                print(f"Warning: Could not derive month from date range: {e}")
                print("  Trends CSV will use current month")
                # Fallback to current month
                now = datetime.now()
                trends_month = f"{now.year}-{now.month:02d}"

        # Generate reports
        try:
            analyzer.generate_csv_report(
                merged_users, adoption_metrics, csv_output_path)
            analyzer.generate_html_report(
                merged_users, adoption_metrics, html_output_path)
            
            # Generate trends CSV report (per-user data only with Year/Month columns)
            analyzer.generate_trends_csv_report(
                merged_users, trends_month, trends_csv_path)
        except Exception as e:
            print(f"Error generating reports: {e}")
            import traceback
            traceback.print_exc()
            return 1

        print("\n" + "="*60)
        print("COMBINED ADOPTION REPORT SUMMARY")
        print("="*60)
        print(f"Report Period: {adoption_metrics['report_period']}")
        print(f"Business Days: {adoption_metrics['business_days']}")
        print("\nAdoption Overview:")
        print(f"  Total Users: {adoption_metrics['total_users']}")
        print(f"  Monthly Active Users (MAU): {adoption_metrics['mau']}")
        print(f"  Adoption Rate: {adoption_metrics['adoption_rate']}%")
        print("\nConsistency Metrics:")
        print(
            f"  Median Consistency: {adoption_metrics['median_consistency']}%")
        print(f"  Mean Consistency: {adoption_metrics['mean_consistency']}%")
        print(f"  75th Percentile: {adoption_metrics['p75_consistency']}%")
        print(f"  90th Percentile: {adoption_metrics['p90_consistency']}%")
        print(
            f"  Users with 15+ active days: {adoption_metrics['users_15_plus_days']} ({adoption_metrics['pct_15_plus_days']}%)")
        print("\nPlatform Usage:")
        print(f"  GitHub Copilot users: {adoption_metrics['github_users']}")
        print(f"  Workbench users: {adoption_metrics['workbench_users']}")
        print(f"  Both platforms: {adoption_metrics['both_platforms_users']}")
        print(f"  Agent mode users: {adoption_metrics['agent_users']}")
        print(
            f"  Embedding/Indexing users: {adoption_metrics['embedding_users']}")
        print(
            f"  Workbench questions users: {adoption_metrics['users_with_workbench_questions']}")
        print("\nIntensity:")
        print(
            f"  Total requests: {adoption_metrics['total_requests_non_embedding']:,}")
        print(
            f"  Mean requests per user: {adoption_metrics['avg_requests_per_user']}")
        print(
            f"  Median requests per user: {adoption_metrics['median_requests_per_user']}")
        print(
            f"  P75 requests per user: {adoption_metrics['p75_requests_per_user']}")
        print(
            f"  Total workbench questions: {adoption_metrics['total_workbench_questions']:,}")
        print(
            f"  Mean workbench questions per active user: {adoption_metrics['avg_workbench_questions_per_user']}")
        print(
            f"  GitHub acceptance rate: {adoption_metrics['github_acceptance_rate']}%")
        print("\nReports generated:")
        print(f"  CSV: {csv_output_path}")
        print(f"  HTML: {html_output_path}")
        print(f"  Trends CSV: {trends_csv_path}")
        print("="*60)

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
