#!/usr/bin/env python3
"""
Cursor CSV Reporter Module

This module generates CSV reports for Cursor AI adoption metrics:
- Individual user adoption report
- Master aggregated adoption report
"""

import csv
from typing import Dict, List, Any


def generate_individual_report(merged_users: List[Dict[str, Any]], output_path: str) -> None:
    """Generate cursor_individual_adoption_report.csv with one row per user.
    
    Args:
        merged_users: List of user dictionaries from merge_cursor_user_data()
        output_path: Path for output CSV file
    """
    print(f"Generating individual adoption report: {output_path}")
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'Email', 'Chapter', 'Current Squad', 'Name',
                'Total Requests', 'Total Cost', 
                'Total Input Tokens', 'Total Output Tokens',
                'Cache Read Tokens', 'Cache Write Tokens',
                'Active Days',
                'Agent Completions', 'Agent Lines',
                'Tab Completions', 'Tab Lines',
                'Total AI Lines', 'Favorite Model',
                'Models Breakdown'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for user in merged_users:
                writer.writerow({
                    'Email': user.get('email', ''),
                    'Chapter': user.get('chapter', ''),
                    'Current Squad': user.get('squad', ''),
                    'Name': user.get('name', ''),
                    'Total Requests': user.get('total_requests', 0),
                    'Total Cost': f"{user.get('total_cost', 0.0):.2f}",
                    'Total Input Tokens': user.get('total_input_tokens', 0),
                    'Total Output Tokens': user.get('total_output_tokens', 0),
                    'Cache Read Tokens': user.get('cache_read_tokens', 0),
                    'Cache Write Tokens': user.get('cache_write_tokens', 0),
                    'Active Days': user.get('active_days', 0),
                    'Agent Completions': user.get('agent_completions', 0),
                    'Agent Lines': user.get('agent_lines', 0),
                    'Tab Completions': user.get('tab_completions', 0),
                    'Tab Lines': user.get('tab_lines', 0),
                    'Total AI Lines': user.get('ai_lines', 0),
                    'Favorite Model': user.get('favorite_model', ''),
                    'Models Breakdown': user.get('models_breakdown', ''),
                })
        
        print(f"Generated individual report with {len(merged_users)} users")
        
    except Exception as e:
        print(f"Error generating individual report: {e}")
        import traceback
        traceback.print_exc()
        raise


def generate_master_report(merged_users: List[Dict[str, Any]], 
                          repo_analytics: List[Dict[str, Any]], 
                          master_metrics: Dict[str, Any],
                          date_range: Any,
                          output_path: str) -> None:
    """Generate cursor_master_adoption_report.csv with aggregated metrics.
    
    Args:
        merged_users: List of user dictionaries from merge_cursor_user_data()
        repo_analytics: List of repository analytics dictionaries
        master_metrics: Dictionary from calculate_master_metrics()
        date_range: Tuple of (start_date, end_date)
        output_path: Path for output CSV file
    """
    print(f"Generating master adoption report: {output_path}")
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Overall Metrics Section
            writer.writerow(['MASTER ADOPTION REPORT'])
            writer.writerow(['Report Period', master_metrics['report_period']])
            writer.writerow([])
            
            writer.writerow(['OVERALL METRICS'])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Total Users', master_metrics['total_users']])
            writer.writerow(['Active Users', master_metrics['active_users']])
            writer.writerow(['Adoption Rate (%)', master_metrics['adoption_rate']])
            writer.writerow(['Total Requests', master_metrics['total_requests']])
            writer.writerow(['Total Cost ($)', f"{master_metrics['total_cost']:.2f}"])
            writer.writerow(['Total Input Tokens', master_metrics['total_input_tokens']])
            writer.writerow(['Total Output Tokens', master_metrics['total_output_tokens']])
            writer.writerow(['Total Agent Completions', master_metrics['total_agent_completions']])
            writer.writerow(['Total Agent Lines', master_metrics['total_agent_lines']])
            writer.writerow(['Total Tab Completions', master_metrics['total_tab_completions']])
            writer.writerow(['Total Tab Lines', master_metrics['total_tab_lines']])
            writer.writerow(['Total AI Lines', master_metrics['total_ai_lines']])
            writer.writerow(['Total Active Days', master_metrics['total_active_days']])
            writer.writerow(['Total Cache Read Tokens', master_metrics['total_cache_read_tokens']])
            writer.writerow(['Total Cache Write Tokens', master_metrics['total_cache_write_tokens']])
            writer.writerow(['Avg Requests per Active User', f"{master_metrics['avg_requests_per_active_user']:.2f}"])
            writer.writerow(['Avg Cost per Active User ($)', f"{master_metrics['avg_cost_per_active_user']:.2f}"])
            writer.writerow(['Avg Agent Completions per Active User', f"{master_metrics['avg_agent_completions_per_active_user']:.2f}"])
            writer.writerow([])
            
            # Chapter Breakdown Section
            writer.writerow(['CHAPTER BREAKDOWN'])
            writer.writerow([
                'Chapter', 'Total Users', 'Active Users', 'Total Requests', 
                'Total Cost ($)', 'Total Agent Completions', 'Threshold', 
                'Threshold %', 'Meets Threshold', 'Total AI Lines', 
                'Total Active Days'
            ])
            
            chapter_breakdown = master_metrics['chapter_breakdown']
            for chapter in sorted(chapter_breakdown.keys()):
                data = chapter_breakdown[chapter]
                writer.writerow([
                    chapter,
                    data['total_users'],
                    data['active_users'],
                    data['total_requests'],
                    f"{data['total_cost']:.2f}",
                    data['total_agent_completions'],
                    data['threshold'],
                    f"{data['threshold_percentage']:.1f}%",
                    'Yes' if data['meets_threshold'] else 'No',
                    data['total_ai_lines'],
                    data['total_active_days'],
                ])
            
            writer.writerow([])
            
            # Repository Summary Section
            writer.writerow(['REPOSITORY SUMMARY'])
            writer.writerow([
                'Repo Name', 'Total Commits', 'Total Lines Added', 
                'Total Lines Deleted', 'AI Lines Added', 'AI Lines Deleted',
                'AI Impact %', 'Composer Lines Added', 'Composer Lines Deleted'
            ])
            
            # Aggregate repository totals
            total_repos = len(repo_analytics)
            total_repo_commits = sum(r.get('total_commits', 0) for r in repo_analytics)
            total_repo_lines_added = sum(r.get('total_lines_added', 0) for r in repo_analytics)
            total_repo_lines_deleted = sum(r.get('total_lines_deleted', 0) for r in repo_analytics)
            total_repo_ai_lines_added = sum(r.get('ai_lines_added', 0) for r in repo_analytics)
            total_repo_ai_lines_deleted = sum(r.get('ai_lines_deleted', 0) for r in repo_analytics)
            total_repo_composer_lines_added = sum(r.get('composer_lines_added', 0) for r in repo_analytics)
            total_repo_composer_lines_deleted = sum(r.get('composer_lines_deleted', 0) for r in repo_analytics)
            
            overall_ai_impact = (
                (total_repo_ai_lines_added / total_repo_lines_added * 100) 
                if total_repo_lines_added > 0 else 0
            )
            
            writer.writerow([
                'TOTAL (All Repositories)',
                total_repo_commits,
                total_repo_lines_added,
                total_repo_lines_deleted,
                total_repo_ai_lines_added,
                total_repo_ai_lines_deleted,
                f"{overall_ai_impact:.2f}%",
                total_repo_composer_lines_added,
                total_repo_composer_lines_deleted,
            ])
            
            writer.writerow([])
            writer.writerow(['Top 10 Repositories by AI Impact'])
            writer.writerow([
                'Repo Name', 'Total Commits', 'Total Lines Added', 
                'AI Lines Added', 'AI Impact %'
            ])
            
            # Sort by AI impact percentage and take top 10
            sorted_repos = sorted(
                repo_analytics,
                key=lambda x: x.get('ai_impact_percentage', 0),
                reverse=True
            )[:10]
            
            for repo in sorted_repos:
                writer.writerow([
                    repo.get('repo_name', ''),
                    repo.get('total_commits', 0),
                    repo.get('total_lines_added', 0),
                    repo.get('ai_lines_added', 0),
                    f"{repo.get('ai_impact_percentage', 0):.2f}%",
                ])
        
        print(f"Generated master report with {len(chapter_breakdown)} chapters and {len(repo_analytics)} repositories")
        
    except Exception as e:
        print(f"Error generating master report: {e}")
        import traceback
        traceback.print_exc()
        raise

