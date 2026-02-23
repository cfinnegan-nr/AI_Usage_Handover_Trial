#!/usr/bin/env python3
"""
Combined AI Adoption Report (FS SPI Azure CSV)

This script combines GitHub Copilot usage stats and Azure API analysis (CSV)
to generate comprehensive adoption-focused reports with metrics like:
- Daily Active Users (DAU) and Monthly Active Users (MAU)
- User consistency rates (active days / business days)
- Daily adoption coverage
- Requests per active user-day
- Adoption distribution and percentiles

Usage:
  python combined_adoption_report_FS_SPI.py --github-json githubusage.json \
    --azureAPIanalysis azure_api.csv --month 2025-09
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from combined_adoption_report import (
    CombinedAdoptionAnalyzer as BaseAnalyzer,
    constrain_date_range,
    derive_date_range,
    extract_github_report_date_range,
)


class CombinedAdoptionAnalyzer(BaseAnalyzer):
    """Analyzes combined GitHub and Azure API usage for adoption metrics."""

    _EMAIL_PATTERN = re.compile(r'^[a-z0-9]+\.[a-z0-9]+@symphonyai\.com$')

    def _is_valid_generated_email(self, email: str) -> bool:
        """Validate generated email against expected SymphonyAI format."""
        return bool(self._EMAIL_PATTERN.match(email))

    def _generate_email_from_subscription(self, subscription: str, row_num: int) -> Optional[str]:
        """
        Generate a SymphonyAI email from the Subscription field.

        Rule:
        - Insert '.' before the second CAPITAL letter in the Subscription value
        - Append '@symphonyai.com'
        - Lowercase everything
        """
        if not subscription:
            print(f"Error: Missing Subscription value on row {row_num}. Skipping row.")
            return None

        subscription = subscription.strip()
        capitals = [idx for idx, ch in enumerate(subscription) if ch.isupper()]
        if len(capitals) < 2:
            print(
                f"Error: Subscription '{subscription}' on row {row_num} does not contain "
                "two capital letters. Cannot derive email. Skipping row."
            )
            return None

        insert_idx = capitals[1]
        email_local = f"{subscription[:insert_idx]}.{subscription[insert_idx:]}"
        email = f"{email_local}@symphonyai.com".lower()

        if not self._is_valid_generated_email(email):
            print(
                f"Error: Generated email '{email}' from Subscription '{subscription}' on row "
                f"{row_num} is invalid. Skipping row."
            )
            return None

        return email

    def _parse_request_count(self, raw_value: Any) -> int:
        """
        Parse request counts that may include commas or 'K' suffixes.

        Examples:
        - "1,001" -> 1001
        - "2.047 K" -> 2047
        """
        if raw_value is None:
            return 0

        text = str(raw_value).strip()
        if not text or text.lower() == 'none':
            return 0

        # Normalize thousands separators
        text = text.replace(',', '')
        multiplier = 1

        # Handle K suffix (case-insensitive)
        if text.lower().endswith('k'):
            multiplier = 1000
            text = text[:-1].strip()

        try:
            return int(round(float(text) * multiplier))
        except (ValueError, TypeError):
            return 0

    def load_workbench_data(
        self,
        file_path: str,
        date_range: Tuple[datetime, datetime],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Load Azure API analysis CSV data and aggregate by user email.

        The CSV is expected to include a header row with at least:
        - Subscription
        - Successful Requests
        - Failed Requests
        - Total Requests

        Activity date is set to the start of the report date_range (month start).
        """
        print(f"Loading Workbench data from {file_path}...")
        print(
            f"  Azure CSV mode: treating activity date as {date_range[0]} (month start)"
        )

        # Maintain identical data schema to the base analyzer
        user_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'active_days': set(),
            'api_requests_total': 0,
            'api_requests_normal': 0,
            'api_requests_embedding': 0,
            'spend_total': 0.0,
            'models_used': set(),
            'models_requests': defaultdict(int),
            'cache_read_tokens': 0,
            'cache_creation_tokens': 0,
        })

        activity_date = date_range[0]
        total_rows = 0
        processed_rows = 0
        skipped_invalid_email = 0
        skipped_missing_subscription = 0
        missing_total_requests = 0
        total_api_requests = 0
        sample_emails = set()

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    print(
                        "Error: Azure API analysis CSV is missing a header row. "
                        "Cannot map required columns."
                    )
                    return {}

                required_columns = [
                    'Subscription',
                    'Successful Requests',
                    'Failed Requests',
                    'Total Requests',
                ]
                missing_columns = [
                    col for col in required_columns if col not in reader.fieldnames
                ]
                if missing_columns:
                    print(
                        "WARNING: Azure CSV missing required columns: "
                        f"{missing_columns}. Output may be incomplete."
                    )

                for row_num, row in enumerate(reader, start=2):
                    total_rows += 1
                    try:
                        subscription = (row.get('Subscription') or '').strip()
                        if not subscription:
                            skipped_missing_subscription += 1
                            print(
                                f"Error: Empty Subscription on row {row_num}. Skipping row."
                            )
                            continue

                        email = self._generate_email_from_subscription(
                            subscription, row_num
                        )
                        if not email:
                            skipped_invalid_email += 1
                            continue

                        # Extend row with derived email as requested
                        row['email'] = email

                        # Map CSV columns to expected metrics
                        total_requests = self._parse_request_count(
                            row.get('Total Requests')
                        )
                        successful_requests = self._parse_request_count(
                            row.get('Successful Requests')
                        )
                        failed_requests = self._parse_request_count(
                            row.get('Failed Requests')
                        )

                        if row.get('Total Requests') is None:
                            missing_total_requests += 1

                        # Track sample emails for diagnostics
                        if len(sample_emails) < 5:
                            sample_emails.add(email)

                        # Add activity day only if there is activity
                        if total_requests > 0:
                            user_data[email]['active_days'].add(activity_date)

                        # Aggregate metrics (CSV does not have embedding/model breakdowns)
                        user_data[email]['api_requests_total'] += total_requests
                        user_data[email]['api_requests_normal'] += total_requests
                        total_api_requests += total_requests

                        # This mapping is intentionally retained for diagnostics only
                        # to ensure CSV columns exist as expected.
                        _ = successful_requests, failed_requests

                        processed_rows += 1
                    except Exception as e:
                        print(
                            f"Error processing Azure CSV row {row_num}: {e}. "
                            "Continuing with next row."
                        )
                        continue
        except FileNotFoundError:
            print(f"Error: Azure API analysis CSV '{file_path}' not found.")
            return {}
        except Exception as e:
            print(f"Error loading Azure API analysis CSV '{file_path}': {e}")
            return {}

        print(f"\n  === WORKBENCH DATA LOADING DIAGNOSTICS ===")
        print(f"  Total rows in CSV: {total_rows}")
        print(f"  Rows processed: {processed_rows}")
        print(f"  Rows skipped (missing Subscription): {skipped_missing_subscription}")
        print(f"  Rows skipped (invalid email): {skipped_invalid_email}")
        print(f"  Rows with missing Total Requests: {missing_total_requests}")
        print(f"  Total API requests aggregated: {total_api_requests}")
        print(f"  Unique users with data: {len(user_data)}")
        if sample_emails:
            print(f"  Sample emails found: {sorted(list(sample_emails))[:5]}")

        if total_api_requests == 0:
            print(
                "  *** WARNING: Total API requests aggregated is zero! "
                "Check that the 'Total Requests' column exists and is populated."
            )

        print(f"  ============================================\n")
        print(f"Loaded Workbench data for {len(user_data)} users")
        return dict(user_data)

    def merge_user_data(
        self,
        github_data: Dict[str, Dict],
        workbench_data: Dict[str, Dict],
        date_range: Tuple[datetime, datetime],
        workbench_questions: Optional[Dict[str, int]] = None,
    ) -> list[Dict[str, Any]]:
        """
        Merge GitHub and Workbench data, ensuring Azure CSV-only users are included.

        The base implementation iterates only over ALLOWED_EMAILS, which can drop
        Azure CSV users not present in useremails.csv. We include those users while
        preserving the base merge behavior and metadata for allowed users.
        """
        # Use base logic but include any emails present in Azure CSV data.
        # This preserves existing output format while preventing silent data loss.
        # ALLOWED_EMAILS is defined in the base module; fall back to empty if unavailable.
        try:
            from combined_adoption_report import ALLOWED_EMAILS as original_allowed  # type: ignore
        except Exception:
            original_allowed = None

        base_allowed_snapshot = set(original_allowed) if original_allowed else set()

        # Create a combined allow list: all allowed users + any Azure CSV emails.
        all_emails = base_allowed_snapshot | set(workbench_data.keys())

        # Reuse the base merge logic by temporarily replacing ALLOWED_EMAILS.
        # This avoids duplicating complex logic and keeps output formatting stable.
        try:
            if original_allowed is not None:
                # Update in-place to retain reference used by base logic.
                original_allowed.clear()
                original_allowed.update(all_emails)
            return super().merge_user_data(
                github_data,
                workbench_data,
                date_range,
                workbench_questions,
            )
        finally:
            # Restore original allowed list to avoid side effects elsewhere.
            if original_allowed is not None:
                original_allowed.clear()
                original_allowed.update(base_allowed_snapshot)


def _month_token(month: Optional[str]) -> Optional[str]:
    """Return month token like 'Feb26' from YYYY-MM, or None if invalid."""
    if not month:
        return None

    try:
        year, month_num = map(int, month.split('-'))
        month_abbrev = datetime(year, month_num, 1).strftime('%b')
        return f"{month_abbrev}{str(year)[-2:]}"
    except Exception:
        return None


def _resolve_workbench_questions_csv(
    input_dir: str,
    provided_name: Optional[str],
    month: Optional[str],
) -> Optional[str]:
    """
    Resolve the workbench questions CSV path.

    Priority:
    1) Direct path in AI_Usage_Input
    2) Exact filename match anywhere under AI_Usage_Input
    3) Month token match (e.g., Feb26) under AI_Usage_Input
    """
    if not provided_name:
        return None

    # 1) Direct path
    direct_path = os.path.join(input_dir, provided_name)
    if os.path.exists(direct_path):
        return direct_path

    # 2) Exact filename match anywhere under input_dir
    base_name = os.path.basename(provided_name)
    exact_matches = []
    try:
        for root, _, files in os.walk(input_dir):
            for filename in files:
                if filename == base_name:
                    exact_matches.append(os.path.join(root, filename))
    except Exception as e:
        print(f"Warning: Error searching for workbench questions CSV: {e}")

    if len(exact_matches) == 1:
        print(
            "Warning: Workbench questions CSV not found at the expected path. "
            f"Using '{exact_matches[0]}' instead."
        )
        return exact_matches[0]
    if len(exact_matches) > 1:
        exact_matches.sort()
        root_matches = [
            match for match in exact_matches
            if os.path.dirname(match) == os.path.abspath(input_dir)
        ]
        chosen = root_matches[0] if root_matches else exact_matches[0]
        print(
            "Warning: Multiple matching workbench questions CSV files found. "
            f"Using '{chosen}'."
        )
        for match in exact_matches:
            print(f"  - {match}")
        return chosen

    # 3) Month token match
    token = _month_token(month)
    if token:
        token_matches = []
        token_lower = token.lower()
        try:
            for root, _, files in os.walk(input_dir):
                for filename in files:
                    if (
                        filename.lower().startswith('workbench user details')
                        and token_lower in filename.lower()
                    ):
                        token_matches.append(os.path.join(root, filename))
        except Exception as e:
            print(
                f"Warning: Error searching for month-based workbench questions CSV: {e}"
            )

        if len(token_matches) == 1:
            print(
                "Warning: Workbench questions CSV not found at the expected path. "
                f"Using '{token_matches[0]}' based on --month {month}."
            )
            return token_matches[0]
        if len(token_matches) > 1:
            token_matches.sort()
            root_matches = [
                match for match in token_matches
                if os.path.dirname(match) == os.path.abspath(input_dir)
            ]
            chosen = root_matches[0] if root_matches else token_matches[0]
            print(
                "Warning: Multiple month-matching workbench questions CSV files found. "
                f"Using '{chosen}'."
            )
            for match in token_matches:
                print(f"  - {match}")
            return chosen

    return None


def main() -> int:
    """Main function to run the combined adoption analyzer."""
    parser = argparse.ArgumentParser(
        description='Generate combined AI adoption report from GitHub and Azure API data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze September 2025
  python combined_adoption_report_FS_SPI.py --github-json githubusage.json \
    --azureAPIanalysis api_usage.csv --month 2025-09
  
  # Explicit date range
  python combined_adoption_report_FS_SPI.py --github-json githubusage.json \
    --azureAPIanalysis api_usage.csv --start-date 2025-09-01 --end-date 2025-09-30
        """,
    )

    parser.add_argument(
        '--workbench-questions-csv',
        help='Path to CSV file with workbench questions count (optional)',
    )
    parser.add_argument(
        '--github-json',
        required=True,
        help='Path to GitHub Copilot usage JSON file',
    )
    parser.add_argument(
        '--azureAPIanalysis',
        required=True,
        help='Path to Azure API analysis CSV file',
    )
    parser.add_argument(
        '--month',
        help='Month in YYYY-MM format (alternative to start/end dates)',
    )
    parser.add_argument(
        '--start-date',
        help='Start date in YYYY-MM-DD format',
    )
    parser.add_argument(
        '--end-date',
        help='End date in YYYY-MM-DD format',
    )
    parser.add_argument(
        '--csv-output',
        default='combined_adoption_report.csv',
        help='Path for CSV output (default: combined_adoption_report.csv)',
    )
    parser.add_argument(
        '--html-output',
        default='combined_adoption_report.html',
        help='Path for HTML output (default: combined_adoption_report.html)',
    )

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
        azure_api_csv_path = os.path.join(input_dir, args.azureAPIanalysis)

        # Handle optional workbench questions CSV
        workbench_questions_csv_path = _resolve_workbench_questions_csv(
            input_dir, args.workbench_questions_csv, args.month
        )
    except Exception as e:
        print(f"Error constructing input file paths: {e}")
        return 1

    # Validate input files exist
    if not os.path.exists(github_json_path):
        print(f"Error: GitHub JSON file '{github_json_path}' not found.")
        print(f"  Expected location: {os.path.abspath(github_json_path)}")
        return 1

    if not os.path.exists(azure_api_csv_path):
        print(f"Error: Azure API analysis CSV file '{azure_api_csv_path}' not found.")
        print(f"  Expected location: {os.path.abspath(azure_api_csv_path)}")
        return 1

    # Warn if optional workbench questions CSV is provided but still unresolved
    if args.workbench_questions_csv and not workbench_questions_csv_path:
        print(
            f"Warning: Workbench questions CSV '{args.workbench_questions_csv}' not found."
        )
        print("  Continuing without workbench questions data...")

    try:
        # Derive requested date range
        requested_date_range = derive_date_range(
            args.month, args.start_date, args.end_date
        )
        print(
            f"\nRequested analysis period: {requested_date_range[0]} to {requested_date_range[1]}"
        )

        # Extract GitHub report's actual data availability range
        github_report_range = extract_github_report_date_range(github_json_path)

        # Constrain date range to GitHub report availability
        date_range = constrain_date_range(requested_date_range, github_report_range)

        if args.month and requested_date_range[0] != date_range[0]:
            print(
                "WARNING: Azure CSV activity date constrained to match GitHub report range. "
                f"Requested start: {requested_date_range[0]}, constrained start: {date_range[0]}"
            )

        # Initialize analyzer
        analyzer = CombinedAdoptionAnalyzer()

        # Load data from both sources (apply date_range filtering where supported)
        github_data = analyzer.load_github_data(github_json_path, date_range)
        workbench_data = analyzer.load_workbench_data(azure_api_csv_path, date_range)

        # Load workbench questions if CSV provided (CSV has no date column)
        workbench_questions = analyzer.load_workbench_questions(
            workbench_questions_csv_path
        )

        # Merge user data
        merged_users = analyzer.merge_user_data(
            github_data, workbench_data, date_range, workbench_questions
        )

        # Calculate adoption metrics
        adoption_metrics = analyzer.calculate_adoption_metrics(
            merged_users, date_range
        )

        # Construct output file paths with AI_Usage_Output prefix
        try:
            csv_output_path = os.path.join(output_dir, args.csv_output)
            html_output_path = os.path.join(output_dir, args.html_output)
            trends_csv_path = os.path.join(output_dir, 'fs-eng-ai-usage-trends.csv')
        except Exception as e:
            print(f"Error constructing output file paths: {e}")
            return 1

        # Determine month for trends CSV (use args.month or derive from date_range)
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
                merged_users, adoption_metrics, csv_output_path
            )
            analyzer.generate_html_report(
                merged_users, adoption_metrics, html_output_path
            )

            # Generate trends CSV report (per-user data only with Year/Month columns)
            analyzer.generate_trends_csv_report(
                merged_users, trends_month, trends_csv_path
            )
        except Exception as e:
            print(f"Error generating reports: {e}")
            import traceback

            traceback.print_exc()
            return 1

        print("\n" + "=" * 60)
        print("COMBINED ADOPTION REPORT SUMMARY")
        print("=" * 60)
        print(f"Report Period: {adoption_metrics['report_period']}")
        print(f"Business Days: {adoption_metrics['business_days']}")
        print("\nAdoption Overview:")
        print(f"  Total Users: {adoption_metrics['total_users']}")
        print(f"  Monthly Active Users (MAU): {adoption_metrics['mau']}")
        print(f"  Adoption Rate: {adoption_metrics['adoption_rate']}%")
        print("\nConsistency Metrics:")
        print(f"  Median Consistency: {adoption_metrics['median_consistency']}%")
        print(f"  Mean Consistency: {adoption_metrics['mean_consistency']}%")
        print(f"  75th Percentile: {adoption_metrics['p75_consistency']}%")
        print(
            f"  Users with 15+ active days: {adoption_metrics['users_15_plus_days']} "
            f"({adoption_metrics['pct_15_plus_days']}%)"
        )
        print("\nPlatform Usage:")
        print(f"  GitHub Copilot users: {adoption_metrics['github_users']}")
        print(f"  Workbench users: {adoption_metrics['workbench_users']}")
        print(f"  Both platforms: {adoption_metrics['both_platforms_users']}")
        print(f"  Agent mode users: {adoption_metrics['agent_users']}")
        print(
            f"  Embedding/Indexing users: {adoption_metrics['embedding_users']}"
        )
        print(
            "  Workbench questions users: "
            f"{adoption_metrics['users_with_workbench_questions']}"
        )
        print("\nIntensity:")
        print(
            f"  Total requests: {adoption_metrics['total_requests_non_embedding']:,}"
        )
        print(
            f"  Mean requests per user: {adoption_metrics['avg_requests_per_user']}"
        )
        print(
            f"  Median requests per user: {adoption_metrics['median_requests_per_user']}"
        )
        print(
            f"  P75 requests per user: {adoption_metrics['p75_requests_per_user']}"
        )
        print(
            f"  Total workbench questions: {adoption_metrics['total_workbench_questions']:,}"
        )
        print(
            "  Mean workbench questions per active user: "
            f"{adoption_metrics['avg_workbench_questions_per_user']}"
        )
        print(
            f"  GitHub acceptance rate: {adoption_metrics['github_acceptance_rate']}%"
        )
        print("\nReports generated:")
        print(f"  CSV: {csv_output_path}")
        print(f"  HTML: {html_output_path}")
        print(f"  Trends CSV: {trends_csv_path}")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
