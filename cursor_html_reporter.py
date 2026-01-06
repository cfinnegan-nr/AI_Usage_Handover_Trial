#!/usr/bin/env python3
"""
Cursor HTML Reporter Module

This module generates an interactive HTML report with Plotly visualizations
for Cursor AI adoption metrics.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Set
from collections import defaultdict
import plotly.graph_objects as go


def generate_html_report(merged_users: List[Dict[str, Any]], 
                       master_metrics: Dict[str, Any], 
                       repo_analytics: List[Dict[str, Any]], 
                       date_range: Tuple[Any, Any], 
                       output_path: str,
                       fs_repo_names: Optional[Set[str]] = None) -> None:
    """Generate comprehensive HTML report with Plotly visualizations.
    
    Args:
        merged_users: List of user dictionaries from merge_cursor_user_data()
        master_metrics: Dictionary from calculate_master_metrics()
        repo_analytics: List of repository analytics dictionaries
        date_range: Tuple of (start_date, end_date)
        output_path: Path for output HTML file
    """
    print(f"Generating HTML report: {output_path}")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_period = master_metrics['report_period']
    
    # Generate Plotly charts
    charts_html = generate_plotly_charts(merged_users, master_metrics, repo_analytics, fs_repo_names)
    
    # Generate table HTML
    table_html = generate_table_html(merged_users)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cursor AI Adoption Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            border-bottom: 4px solid #667eea;
            padding-bottom: 15px;
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .timestamp {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
            font-style: italic;
            font-size: 1.1em;
        }}
        .summary {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .summary h2 {{
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .stat-label {{
            font-size: 0.95em;
            color: #7f8c8d;
            margin-top: 8px;
            font-weight: 500;
        }}
        .section-title {{
            font-size: 1.4em;
            font-weight: bold;
            color: #2c3e50;
            margin: 30px 0 15px 0;
            padding-bottom: 8px;
            border-bottom: 3px solid #667eea;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .chart-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
            text-align: center;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background-color: white;
            font-size: 0.9em;
        }}
        th, td {{
            padding: 12px 10px;
            text-align: center;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: bold;
            position: sticky;
            top: 0;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{
            opacity: 0.9;
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
            margin: 15px 0;
            padding: 15px;
            background: linear-gradient(135deg, #e8f4fd 0%, #d1e7f0 100%);
            border-radius: 8px;
            font-size: 0.95em;
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
        .table-container {{
            overflow-x: auto;
            margin-top: 20px;
            max-height: 600px;
            overflow-y: auto;
            position: relative;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .table-container table {{
            position: relative;
        }}
        h2 {{
            color: #2c3e50;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 2em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Cursor AI Adoption Report</h1>
        <div class="timestamp">Generated on {timestamp}</div>
        <div class="timestamp">Report Period: {report_period}</div>
        
        <div class="summary">
            <h2>Summary Metrics</h2>
            
            <div class="section-title">Overall Adoption</div>
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{master_metrics['total_users']}</div>
                    <div class="stat-label">Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{master_metrics['active_users']}</div>
                    <div class="stat-label">Active Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{master_metrics['adoption_rate']}%</div>
                    <div class="stat-label">Adoption Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{master_metrics['total_requests']:,}</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${master_metrics['total_cost']:,.2f}</div>
                    <div class="stat-label">Total Cost</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{master_metrics['total_agent_completions']:,}</div>
                    <div class="stat-label">Agent Completions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{master_metrics['total_ai_lines']:,}</div>
                    <div class="stat-label">Total AI Lines</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{master_metrics['total_active_days']:,}</div>
                    <div class="stat-label">Total Active Days</div>
                </div>
            </div>
            
            <div class="section-title">
                <span style="font-size: 1.8em; margin-right: 10px;">📊</span>Chapter Breakdown
            </div>
            <div class="summary-stats">
"""
    
    # Add chapter breakdown cards
    chapter_breakdown = master_metrics['chapter_breakdown']
    for chapter in sorted(chapter_breakdown.keys()):
        data = chapter_breakdown[chapter]
        threshold_status = "✓" if data['meets_threshold'] else "✗"
        threshold_color = "#27ae60" if data['meets_threshold'] else "#e74c3c"
        
        html += f"""
                <div class="stat-card">
                    <div class="stat-number" style="color: {threshold_color};">{threshold_status}</div>
                    <div class="stat-label"><strong>{chapter}</strong></div>
                    <div class="stat-label">Users: {data['active_users']}/{data['total_users']}</div>
                    <div class="stat-label">Avg Requests: {data['avg_total_requests']:.2f}</div>
                    <div class="stat-label">Threshold: {data['threshold']} ({data['threshold_percentage']:.1f}%)</div>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <h2>Data Visualizations</h2>
"""
    
    # Add charts HTML
    html += charts_html
    
    # Add table section
    html += f"""
        <h2>Individual User Statistics</h2>
        <div class="sort-info">
            <strong>Filter by Chapter:</strong>
            <select id="chapterFilter" style="padding: 8px; margin: 0 10px; border-radius: 6px; border: 2px solid #667eea; min-width: 150px; font-size: 1em;">
                <option value="">All Chapters</option>
            </select>
            <span id="filterDisplay" style="margin-left: 10px; font-style: italic; color: #7f8c8d;"></span>
            <br><br>
            <strong>Sort Info:</strong> Click on column headers to sort. Hold Shift and click additional headers for multi-column sort. Current sort: <span id="sortDisplay">Default (by Active Days descending)</span>
        </div>
        <div class="table-container">
            {table_html}
        </div>
    </div>
    
    <script>
        class TableSorter {{
            constructor(tableId) {{
                this.table = document.getElementById(tableId);
                this.tbody = this.table.querySelector('tbody');
                this.headers = this.table.querySelectorAll('th');
                this.sortState = [];
                this.chapterFilter = '';
                this.init();
            }}
            
            init() {{
                this.headers.forEach((header, index) => {{
                    header.classList.add('sortable');
                    header.addEventListener('click', (e) => this.handleSort(e, index));
                }});
                
                this.populateChapterFilter();
                
                const chapterFilterSelect = document.getElementById('chapterFilter');
                chapterFilterSelect.addEventListener('change', (e) => this.applyChapterFilter(e.target.value));
                
                // Default sort by active days descending
                this.applyDefaultSort();
            }}
            
            populateChapterFilter() {{
                const rows = Array.from(this.tbody.querySelectorAll('tr'));
                const chapters = new Set();
                
                rows.forEach(row => {{
                    const chapterCell = row.cells[1];
                    const chapterText = chapterCell.textContent.trim();
                    if (chapterText) {{
                        chapters.add(chapterText);
                    }}
                }});
                
                const sortedChapters = Array.from(chapters).sort();
                const chapterFilterSelect = document.getElementById('chapterFilter');
                sortedChapters.forEach(chapter => {{
                    const option = document.createElement('option');
                    option.value = chapter;
                    option.textContent = chapter;
                    chapterFilterSelect.appendChild(option);
                }});
            }}
            
            applyChapterFilter(filterValue) {{
                this.chapterFilter = filterValue.trim();
                const rows = Array.from(this.tbody.querySelectorAll('tr'));
                let visibleCount = 0;
                
                rows.forEach(row => {{
                    const chapterCell = row.cells[1];
                    const chapterText = chapterCell.textContent.trim();
                    
                    if (this.chapterFilter === '' || chapterText === this.chapterFilter) {{
                        row.style.display = '';
                        visibleCount++;
                    }} else {{
                        row.style.display = 'none';
                    }}
                }});
                
                const filterDisplay = document.getElementById('filterDisplay');
                if (this.chapterFilter === '') {{
                    filterDisplay.textContent = '';
                }} else {{
                    filterDisplay.textContent = `Showing ${{visibleCount}} of ${{rows.length}} users`;
                }}
            }}
            
            applyDefaultSort() {{
                this.sortState = [];
                this.addSortColumn(5, 'desc'); // Active Days column
                this.updateHeaders();
                this.performSort();
                this.updateSortDisplay('Active Days (descending)');
            }}
            
            handleSort(e, columnIndex) {{
                if (e.shiftKey) {{
                    const existingSort = this.sortState.find(s => s.column === columnIndex);
                    if (existingSort) {{
                        existingSort.direction = existingSort.direction === 'asc' ? 'desc' : 'asc';
                    }} else {{
                        this.addSortColumn(columnIndex, 'asc');
                    }}
                }} else {{
                    const existingSort = this.sortState.find(s => s.column === columnIndex);
                    const newDirection = existingSort && existingSort.direction === 'asc' ? 'desc' : 'asc';
                    this.sortState = [];
                    this.addSortColumn(columnIndex, newDirection);
                }}
                
                this.updateHeaders();
                this.performSort();
                this.updateSortDisplay();
            }}
            
            addSortColumn(columnIndex, direction) {{
                const existing = this.sortState.findIndex(s => s.column === columnIndex);
                if (existing !== -1) {{
                    this.sortState[existing].direction = direction;
                }} else {{
                    this.sortState.push({{ column: columnIndex, direction: direction }});
                }}
            }}
            
            updateHeaders() {{
                this.headers.forEach((header, index) => {{
                    header.classList.remove('sort-asc', 'sort-desc');
                    const sort = this.sortState.find(s => s.column === index);
                    if (sort) {{
                        header.classList.add(sort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
                    }}
                }});
            }}
            
            performSort() {{
                const rows = Array.from(this.tbody.querySelectorAll('tr'));
                
                rows.sort((a, b) => {{
                    for (const sort of this.sortState) {{
                        const aCell = a.cells[sort.column].textContent.trim();
                        const bCell = b.cells[sort.column].textContent.trim();
                        
                        const aNum = parseFloat(aCell.replace(/[^0-9.-]/g, ''));
                        const bNum = parseFloat(bCell.replace(/[^0-9.-]/g, ''));
                        
                        let comparison = 0;
                        if (!isNaN(aNum) && !isNaN(bNum)) {{
                            comparison = aNum - bNum;
                        }} else {{
                            comparison = aCell.localeCompare(bCell);
                        }}
                        
                        if (comparison !== 0) {{
                            return sort.direction === 'asc' ? comparison : -comparison;
                        }}
                    }}
                    return 0;
                }});
                
                rows.forEach(row => this.tbody.appendChild(row));
            }}
            
            updateSortDisplay(customText) {{
                const sortDisplay = document.getElementById('sortDisplay');
                if (customText) {{
                    sortDisplay.textContent = customText;
                }} else if (this.sortState.length === 0) {{
                    sortDisplay.textContent = 'Default (by Active Days descending)';
                }} else {{
                    const displayParts = this.sortState.map(s => {{
                        const header = this.headers[s.column].textContent.trim();
                        const direction = s.direction === 'asc' ? '↑' : '↓';
                        return header + ' ' + direction;
                    }});
                    sortDisplay.textContent = displayParts.join(', ');
                }}
            }}
        }}
        
        document.addEventListener('DOMContentLoaded', () => {{
            new TableSorter('adoptionTable');
        }});
    </script>
</body>
</html>"""
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Generated HTML report: {output_path}")
    except Exception as e:
        print(f"Error writing HTML report: {e}")
        import traceback
        traceback.print_exc()
        raise


def generate_plotly_charts(merged_users: List[Dict[str, Any]], 
                          master_metrics: Dict[str, Any], 
                          repo_analytics: List[Dict[str, Any]],
                          fs_repo_names: Optional[Set[str]] = None) -> str:
    """Generate Plotly chart HTML code.
    
    Args:
        merged_users: List of user dictionaries
        master_metrics: Master metrics dictionary
        repo_analytics: Repository analytics list
        
    Returns:
        HTML string containing all chart divs and JavaScript
    """
    charts_html = ""
    
    # 1. Adoption Over Time (Daily Active Users)
    # Note: We don't have daily breakdown in the data, so we'll create a placeholder
    # or skip this chart if we can't derive daily data
    charts_html += """
        <div class="chart-container">
            <div class="chart-title">Note: Daily adoption data requires timestamp-level analysis</div>
        </div>
"""
    
    # 2. Model Usage Distribution
    model_counts = {}
    for user in merged_users:
        models_breakdown = user.get('models_breakdown', '')
        if models_breakdown:
            for part in models_breakdown.split(', '):
                if ':' in part:
                    model, count_str = part.rsplit(':', 1)
                    model = model.strip()
                    try:
                        count = int(count_str.strip())
                        model_counts[model] = model_counts.get(model, 0) + count
                    except ValueError:
                        pass
    
    if model_counts:
        models = list(model_counts.keys())
        counts = list(model_counts.values())
        fig3 = go.Figure(data=[go.Pie(labels=models, values=counts, 
                                     hovertemplate='<b>%{label}</b><br>Usage: %{value}<br>Percentage: %{percent}<extra></extra>')])
        fig3.update_layout(
            title='Model Usage Distribution',
            template='plotly_white',
            height=500
        )
        fig3_dict = fig3.to_dict()
        chart3_data = json.dumps(fig3_dict['data'])
        chart3_layout = json.dumps(fig3_dict['layout'])
        charts_html += f"""
            <div class="chart-container">
                <div class="chart-title">Model Usage Distribution</div>
                <div id="chart3"></div>
            </div>
            <script>
                Plotly.newPlot('chart3', {chart3_data}, {chart3_layout});
            </script>
"""
    
    # 3. Cost Analysis by Chapter
    # Define chapter breakdown and chapters (needed for multiple charts)
    chapter_breakdown = master_metrics['chapter_breakdown']
    chapters = sorted(chapter_breakdown.keys())
    chapter_data = {
        'requests': [chapter_breakdown[c]['total_requests'] for c in chapters],
        'cost': [chapter_breakdown[c]['total_cost'] for c in chapters],
        'ai_lines': [chapter_breakdown[c]['total_ai_lines'] for c in chapters],
    }
    
    fig4 = go.Figure(data=[go.Bar(x=chapters, y=chapter_data['cost'], 
                                  marker_color=['#27ae60' if chapter_breakdown[c]['total_cost'] > 100 else '#e74c3c' for c in chapters],
                                  hovertemplate='<b>%{x}</b><br>Cost: $%{y:,.2f}<extra></extra>')])
    fig4.update_layout(
        title='Cost Analysis by Chapter',
        xaxis_title='Chapter',
        yaxis_title='Total Cost ($)',
        template='plotly_white',
        height=500
    )
    fig4_dict = fig4.to_dict()
    chart4_data = json.dumps(fig4_dict['data'])
    chart4_layout = json.dumps(fig4_dict['layout'])
    charts_html += f"""
        <div class="chart-container">
            <div class="chart-title">Cost Analysis by Chapter</div>
            <div id="chart4"></div>
        </div>
        <script>
            Plotly.newPlot('chart4', {chart4_data}, {chart4_layout});
        </script>
"""
    
    # 4. AI Lines Generated by Chapter
    fig5 = go.Figure(data=[go.Bar(x=chapters, y=chapter_data['ai_lines'], 
                                  marker_color='#3498db',
                                  hovertemplate='<b>%{x}</b><br>AI Lines: %{y:,}<extra></extra>')])
    fig5.update_layout(
        title='AI Lines Generated by Chapter',
        xaxis_title='Chapter',
        yaxis_title='Total AI Lines',
        template='plotly_white',
        height=500
    )
    fig5_dict = fig5.to_dict()
    chart5_data = json.dumps(fig5_dict['data'])
    chart5_layout = json.dumps(fig5_dict['layout'])
    charts_html += f"""
        <div class="chart-container">
            <div class="chart-title">AI Lines Generated by Chapter</div>
            <div id="chart5"></div>
        </div>
        <script>
            Plotly.newPlot('chart5', {chart5_data}, {chart5_layout});
        </script>
"""
    
    # 5. Total Requests Threshold Analysis (using average requests)
    requests = [chapter_breakdown[c]['avg_total_requests'] for c in chapters]
    thresholds = [chapter_breakdown[c]['threshold'] for c in chapters]
    colors = ['#27ae60' if r >= t else '#e74c3c' for r, t in zip(requests, thresholds)]
    
    fig6 = go.Figure()
    fig6.add_trace(go.Bar(name='Avg Requests', x=chapters, y=requests, 
                         marker_color=colors,
                         hovertemplate='<b>%{x}</b><br>Avg Requests: %{y:.2f}<br>Threshold: %{{customdata}}<br>Gap: %{{text:.2f}}<extra></extra>',
                         customdata=thresholds,
                         text=[r - t for r, t in zip(requests, thresholds)]))
    fig6.add_trace(go.Scatter(name='Threshold', x=chapters, y=thresholds, 
                             mode='lines+markers', line=dict(color='orange', width=3, dash='dash'),
                             marker=dict(size=10),
                             hovertemplate='<b>%{x}</b><br>Threshold: %{y:,}<extra></extra>'))
    fig6.update_layout(
        title='Total Requests Threshold Analysis (Average per Chapter)',
        xaxis_title='Chapter',
        yaxis_title='Average Total Requests',
        template='plotly_white',
        height=500,
        hovermode='x unified'
    )
    fig6_dict = fig6.to_dict()
    chart6_data = json.dumps(fig6_dict['data'])
    chart6_layout = json.dumps(fig6_dict['layout'])
    charts_html += f"""
        <div class="chart-container">
            <div class="chart-title">Total Requests Threshold Analysis - Average per Chapter (Green = Above Threshold, Red = Below Threshold)</div>
            <div id="chart6"></div>
        </div>
        <script>
            Plotly.newPlot('chart6', {chart6_data}, {chart6_layout});
        </script>
"""
    
    # 6. Chapter Threshold Performance (Gauge/Bar Chart) - Using Average Total Requests
    # Note: chapter_breakdown and chapters are already defined above
    
    # Calculate threshold percentages based on Average Total Requests with fixed thresholds
    # The fixed thresholds (5000 for BE/FE, 2000 for others) are already calculated in chapter_breakdown
    threshold_percentages = []
    for c in chapters:
        chapter_data = chapter_breakdown[c]
        # Use the fixed threshold already calculated in chapter_breakdown
        threshold = chapter_data['threshold']
        avg_requests = chapter_data['avg_total_requests']
        # Use Average Total Requests as the metric for threshold calculation
        threshold_percentage = (avg_requests / threshold * 100) if threshold > 0 else 0
        threshold_percentages.append(threshold_percentage)
    
    # Prepare customdata as list of tuples: (status, avg_requests)
    customdata_list = [
        ('Meets Target' if p >= 100 else 'Needs Improvement', chapter_breakdown[c]['avg_total_requests'])
        for p, c in zip(threshold_percentages, chapters)
    ]
    
    fig7 = go.Figure(data=[go.Bar(x=chapters, y=threshold_percentages,
                                  marker_color=['#27ae60' if p >= 100 else '#e74c3c' if p >= 50 else '#f39c12' for p in threshold_percentages],
                                  hovertemplate='<b>%{x}</b><br>Achievement: %{y:.1f}%<br>Status: %{customdata[0]}<br>Avg Requests: %{customdata[1]:.2f}<extra></extra>',
                                  customdata=customdata_list)])
    fig7.add_hline(y=100, line_dash="dash", line_color="orange", 
                   annotation_text="100% Target", annotation_position="right")
    fig7.update_layout(
        title='Chapter Threshold Performance (% of Target Achieved) - Based on Average Total Requests',
        xaxis_title='Chapter',
        yaxis_title='Percentage of Threshold Achieved (%)',
        template='plotly_white',
        height=500
    )
    fig7_dict = fig7.to_dict()
    chart7_data = json.dumps(fig7_dict['data'])
    chart7_layout = json.dumps(fig7_dict['layout'])
    charts_html += f"""
        <div class="chart-container">
            <div class="chart-title">Chapter Threshold Performance (% of Target Achieved) - Based on Average Total Requests</div>
            <div id="chart7"></div>
        </div>
        <script>
            Plotly.newPlot('chart7', {chart7_data}, {chart7_layout});
        </script>
"""
    
    # 7. AI Impact Percentage for Hub Repos and FS Repos - Breakdown by Individual Repos
    # Get repos with 'hub' in name
    hub_repos = [repo for repo in repo_analytics if 'hub' in repo.get('repo_name', '').lower()]
    
    # Get repos from FS_Repo_List.csv
    fs_repos = []
    if fs_repo_names:
        for repo in repo_analytics:
            repo_name_lower = repo.get('repo_name', '').lower()
            if repo_name_lower in fs_repo_names:
                fs_repos.append(repo)
    
    # Combine both lists, avoiding duplicates
    combined_repos = {}
    for repo in hub_repos + fs_repos:
        repo_name = repo.get('repo_name', '')
        if repo_name not in combined_repos:
            combined_repos[repo_name] = repo
    
    # Filter out repos with 0% AI Impact Percentage
    filtered_repos = [
        repo for repo in combined_repos.values()
        if repo.get('ai_impact_percentage', 0) > 0
    ]
    
    if filtered_repos:
        # Sort repos by AI Impact Percentage (descending) for better visualization
        filtered_repos_sorted = sorted(filtered_repos, key=lambda r: r.get('ai_impact_percentage', 0), reverse=True)
        
        # Extract repo names and AI Impact Percentages
        repo_names = [repo.get('repo_name', 'Unknown') for repo in filtered_repos_sorted]
        repo_percentages = [repo.get('ai_impact_percentage', 0) for repo in filtered_repos_sorted]
        
        # Individual repo breakdown chart
        fig10 = go.Figure(data=[go.Bar(x=repo_percentages, y=repo_names, orientation='h',
                                       marker_color='#9b59b6',
                                       hovertemplate='<b>%{{y}}</b><br>AI Impact: %{{x:.2f}}%<extra></extra>',
                                       text=[f'{p:.2f}%' for p in repo_percentages],
                                       textposition='auto')])
        fig10.update_layout(
            title='AI Impact Percentage - Hub & FS Repositories (By Individual Repo)',
            xaxis_title='AI Impact Percentage (%)',
            yaxis_title='Repository',
            template='plotly_white',
            height=max(400, len(repo_names) * 30)  # Dynamic height based on number of repos
        )
        fig10_dict = fig10.to_dict()
        chart10_data = json.dumps(fig10_dict['data'])
        chart10_layout = json.dumps(fig10_dict['layout'])
        charts_html += f"""
            <div class="chart-container">
                <div class="chart-title">AI Impact Percentage - Hub & FS Repositories (By Individual Repo)</div>
                <div id="chart10"></div>
            </div>
            <script>
                Plotly.newPlot('chart10', {chart10_data}, {chart10_layout});
            </script>
"""
    
    # 8. Top Users - Reverse order (largest at top)
    sorted_users = sorted(merged_users, key=lambda x: x.get('total_requests', 0), reverse=True)[:10]
    # Reverse the lists so largest appears at top
    top_user_names = [u.get('name', u.get('email', ''))[:30] for u in sorted_users]
    top_user_requests = [u.get('total_requests', 0) for u in sorted_users]
    
    fig8 = go.Figure(data=[go.Bar(y=top_user_names[::-1], x=top_user_requests[::-1], orientation='h',
                                  marker_color='#667eea',
                                  hovertemplate='<b>%{y}</b><br>Total Requests: %{x:,}<extra></extra>')])
    fig8.update_layout(
        title='Top 10 Users by Total Requests',
        xaxis_title='Total Requests',
        yaxis_title='User',
        template='plotly_white',
        height=500
    )
    fig8_dict = fig8.to_dict()
    chart8_data = json.dumps(fig8_dict['data'])
    chart8_layout = json.dumps(fig8_dict['layout'])
    charts_html += f"""
        <div class="chart-container">
            <div class="chart-title">Top 10 Users by Total Activity</div>
            <div id="chart8"></div>
        </div>
        <script>
            Plotly.newPlot('chart8', {chart8_data}, {chart8_layout});
        </script>
"""
    
    return charts_html


def generate_table_html(merged_users: List[Dict[str, Any]]) -> str:
    """Generate HTML table for individual user statistics.
    
    Args:
        merged_users: List of user dictionaries
        
    Returns:
        HTML string containing the table
    """
    html = """
            <table id="adoptionTable">
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Chapter</th>
                        <th>Current Squad</th>
                        <th>Name</th>
                        <th>Total Requests</th>
                        <th>Active Days</th>
                        <th>Total Cost ($)</th>
                        <th>Agent Completions</th>
                        <th>Agent Lines</th>
                        <th>Tab Completions</th>
                        <th>Tab Lines</th>
                        <th>Total AI Lines</th>
                        <th>Favorite Model</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for user in merged_users:
        html += f"""
                    <tr>
                        <td>{user.get('email', '')}</td>
                        <td>{user.get('chapter', '')}</td>
                        <td>{user.get('squad', '')}</td>
                        <td>{user.get('name', '')}</td>
                        <td>{user.get('total_requests', 0):,}</td>
                        <td>{user.get('active_days', 0)}</td>
                        <td>${user.get('total_cost', 0.0):,.2f}</td>
                        <td>{user.get('agent_completions', 0):,}</td>
                        <td>{user.get('agent_lines', 0):,}</td>
                        <td>{user.get('tab_completions', 0):,}</td>
                        <td>{user.get('tab_lines', 0):,}</td>
                        <td>{user.get('ai_lines', 0):,}</td>
                        <td>{user.get('favorite_model', '')}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
"""
    
    return html

