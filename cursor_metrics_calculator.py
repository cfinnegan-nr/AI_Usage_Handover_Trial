#!/usr/bin/env python3
"""
Cursor Metrics Calculator Module

This module calculates aggregated metrics for Cursor AI adoption reporting,
including master metrics, chapter breakdowns, and threshold analysis.
"""

from typing import Dict, List, Any, Tuple
from collections import defaultdict


def get_threshold_for_chapter(chapter: str) -> int:
    """Get the Agent Completions threshold for a given chapter.
    
    Args:
        chapter: Chapter name (e.g., 'BE', 'FE', 'QA', etc.)
        
    Returns:
        Threshold value: 1000 for BE/FE, 400 for others
    """
    chapter_upper = chapter.upper() if chapter else ''
    if chapter_upper in ('BE', 'FE'):
        return 1000
    return 400


def get_total_requests_threshold_for_chapter(chapter: str) -> int:
    """Get the Total Requests threshold for a given chapter.
    
    Since Total Requests are typically much higher than Agent Completions,
    we use a multiplier of the Agent Completions threshold.
    
    Args:
        chapter: Chapter name (e.g., 'BE', 'FE', 'QA, etc.)
        
    Returns:
        Threshold value: 5000 for BE/FE, 2000 for others
        (5x multiplier of Agent Completions thresholds)
    """
    chapter_upper = chapter.upper() if chapter else ''
    if chapter_upper in ('BE', 'FE'):
        return 5000  # 5x the 1000 Agent Completions threshold
    return 2000  # 5x the 400 Agent Completions threshold


def calculate_chapter_breakdown(merged_users: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Calculate aggregated metrics grouped by chapter.
    
    Args:
        merged_users: List of user dictionaries from merge_cursor_user_data()
        
    Returns:
        Dictionary mapping chapter name to aggregated metrics
    """
    chapter_data = defaultdict(lambda: {
        'total_users': 0,
        'active_users': 0,
        'total_requests': 0,
        'total_cost': 0.0,
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'total_agent_completions': 0,
        'total_agent_lines': 0,
        'total_tab_completions': 0,
        'total_tab_lines': 0,
        'total_ai_lines': 0,
        'total_active_days': 0,
        'cache_read_tokens': 0,
        'cache_write_tokens': 0,
    })
    
    for user in merged_users:
        chapter = user.get('chapter', '') or 'Unknown'
        chapter_data[chapter]['total_users'] += 1
        
        # Check if user is active (has any activity)
        is_active = (
            user.get('total_requests', 0) > 0 or
            user.get('agent_completions', 0) > 0 or
            user.get('tab_completions', 0) > 0
        )
        
        if is_active:
            chapter_data[chapter]['active_users'] += 1
        
        # Aggregate metrics
        chapter_data[chapter]['total_requests'] += user.get('total_requests', 0)
        chapter_data[chapter]['total_cost'] += user.get('total_cost', 0.0)
        chapter_data[chapter]['total_input_tokens'] += user.get('total_input_tokens', 0)
        chapter_data[chapter]['total_output_tokens'] += user.get('total_output_tokens', 0)
        chapter_data[chapter]['total_agent_completions'] += user.get('agent_completions', 0)
        chapter_data[chapter]['total_agent_lines'] += user.get('agent_lines', 0)
        chapter_data[chapter]['total_tab_completions'] += user.get('tab_completions', 0)
        chapter_data[chapter]['total_tab_lines'] += user.get('tab_lines', 0)
        chapter_data[chapter]['total_ai_lines'] += user.get('ai_lines', 0)
        chapter_data[chapter]['total_active_days'] += user.get('active_days', 0)
        chapter_data[chapter]['cache_read_tokens'] += user.get('cache_read_tokens', 0)
        chapter_data[chapter]['cache_write_tokens'] += user.get('cache_write_tokens', 0)
    
    # Calculate threshold metrics for each chapter
    result = {}
    for chapter, data in chapter_data.items():
        threshold = get_threshold_for_chapter(chapter)
        total_completions = data['total_agent_completions']
        threshold_percentage = (total_completions / threshold * 100) if threshold > 0 else 0
        
        result[chapter] = {
            **data,
            'threshold': threshold,
            'threshold_percentage': round(threshold_percentage, 1),
            'threshold_gap': total_completions - threshold,
            'meets_threshold': total_completions >= threshold,
        }
    
    return result


def calculate_master_metrics(merged_users: List[Dict[str, Any]], 
                           date_range: Tuple[Any, Any]) -> Dict[str, Any]:
    """Calculate overall master metrics across all users.
    
    Args:
        merged_users: List of user dictionaries from merge_cursor_user_data()
        date_range: Tuple of (start_date, end_date) for the reporting period
        
    Returns:
        Dictionary containing aggregated master metrics
    """
    total_users = len(merged_users)
    active_users = sum(
        1 for user in merged_users
        if (user.get('total_requests', 0) > 0 or
            user.get('agent_completions', 0) > 0 or
            user.get('tab_completions', 0) > 0)
    )
    
    adoption_rate = (active_users / total_users * 100) if total_users > 0 else 0
    
    # Aggregate totals
    total_requests = sum(user.get('total_requests', 0) for user in merged_users)
    total_cost = sum(user.get('total_cost', 0.0) for user in merged_users)
    total_input_tokens = sum(user.get('total_input_tokens', 0) for user in merged_users)
    total_output_tokens = sum(user.get('total_output_tokens', 0) for user in merged_users)
    total_agent_completions = sum(user.get('agent_completions', 0) for user in merged_users)
    total_agent_lines = sum(user.get('agent_lines', 0) for user in merged_users)
    total_tab_completions = sum(user.get('tab_completions', 0) for user in merged_users)
    total_tab_lines = sum(user.get('tab_lines', 0) for user in merged_users)
    total_ai_lines = sum(user.get('ai_lines', 0) for user in merged_users)
    total_active_days = sum(user.get('active_days', 0) for user in merged_users)
    total_cache_read_tokens = sum(user.get('cache_read_tokens', 0) for user in merged_users)
    total_cache_write_tokens = sum(user.get('cache_write_tokens', 0) for user in merged_users)
    
    # Calculate averages for active users
    avg_requests_per_active_user = (total_requests / active_users) if active_users > 0 else 0
    avg_cost_per_active_user = (total_cost / active_users) if active_users > 0 else 0
    avg_agent_completions_per_active_user = (total_agent_completions / active_users) if active_users > 0 else 0
    
    # Calculate chapter breakdown
    chapter_breakdown = calculate_chapter_breakdown(merged_users)
    
    return {
        'report_period': f"{date_range[0]} to {date_range[1]}",
        'total_users': total_users,
        'active_users': active_users,
        'adoption_rate': round(adoption_rate, 1),
        'total_requests': total_requests,
        'total_cost': round(total_cost, 2),
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'total_agent_completions': total_agent_completions,
        'total_agent_lines': total_agent_lines,
        'total_tab_completions': total_tab_completions,
        'total_tab_lines': total_tab_lines,
        'total_ai_lines': total_ai_lines,
        'total_active_days': total_active_days,
        'total_cache_read_tokens': total_cache_read_tokens,
        'total_cache_write_tokens': total_cache_write_tokens,
        'avg_requests_per_active_user': round(avg_requests_per_active_user, 2),
        'avg_cost_per_active_user': round(avg_cost_per_active_user, 2),
        'avg_agent_completions_per_active_user': round(avg_agent_completions_per_active_user, 2),
        'chapter_breakdown': chapter_breakdown,
    }

