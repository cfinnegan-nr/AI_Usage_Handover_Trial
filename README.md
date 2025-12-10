# Combined AI Adoption Report

## Overview

The `combined_adoption_report.py` script generates comprehensive adoption-focused reports by combining GitHub Copilot usage statistics with AI Workbench (API) usage statistics. This provides a unified view of AI tool adoption across your organization.

## Why Use This Report?

This report is specifically designed for tracking **adoption** rather than just usage intensity. It answers key questions like:

- **Are people using AI daily?** Track active days and consistency rates
- **What's our adoption coverage?** See Monthly Active Users (MAU) and adoption rates
- **How consistently are teams using AI?** View median, p75, and p90 consistency metrics
- **Are we meeting adoption targets?** Check threshold shares (15+ days, 20+ days, 80%+ consistency)
- **Which platforms are being used?** See GitHub Copilot vs Workbench usage patterns

## Key Adoption Metrics

### Core Adoption Metrics

- **Monthly Active Users (MAU)**: Users with at least 1 active day in the period
- **Adoption Rate**: Percentage of total users who are active
- **Days Active**: Number of unique days a user had AI activity
- **Consistency Rate**: (Days Active / Business Days) × 100
  - Measures how regularly users engage with AI tools
  - Target: 80%+ for daily adoptiono

### Consistency Distribution

- **Median Consistency**: 50th percentile of user consistency rates
- **P75 Consistency**: 75th percentile (upper quartile)
- **P90 Consistency**: 90th percentile (top performers)

### Adoption Thresholds

- **Users with 15+ Active Days**: Count and percentage
- **Users with 20+ Active Days**: Count and percentage  
- **Users with 80%+ Consistency**: Count and percentage

### Intensity Metrics (Secondary)

- **Total Requests**: Combined GitHub + Workbench requests
- **Requests per Active User-Day**: Average intensity when users are active
  - Kept separate from adoption to avoid conflating participation with intensity

### Platform-Specific Metrics

- **GitHub Copilot Users**: Users with GitHub activity
- **Workbench Users**: Users with API/Workbench activity
- **Both Platforms**: Users active on both
- **Agent Mode Users**: GitHub users who used agent mode
- **Roo Users**: Users with Roo (custom mode) activity
- **Embedding/Indexing Users**: Users who used embedding models

## Python Environment Setup

This project uses a dedicated Python virtual environment. The workspace is configured to automatically use the Python interpreter from the `venv` folder.

### Automatic Setup (VS Code/Cursor)

The workspace is pre-configured with `.vscode/settings.json` to:
- **Automatically use the Python interpreter** from `venv/Scripts/python.exe`
- **Activate the virtual environment** when opening a terminal
- **Load required Python libraries** into the project environment

When you open a new terminal in VS Code/Cursor, it will automatically activate the virtual environment.

### Manual Setup (if needed)

If you need to set up the environment manually:

```bash
# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# On Windows Command Prompt:
venv\Scripts\activate.bat

# Install dependencies (if any are added to requirements.txt)
pip install -r requirements.txt
```

### Verifying the Environment

To verify the Python interpreter is set correctly:
1. Open a terminal in VS Code/Cursor
2. You should see `(venv)` in your terminal prompt
3. Run `python --version` to confirm Python 3.11.9

## Usage

### Basic Usage

```bash
# Analyze a specific month (with workbench questions CSV)
python combined_adoption_report.py \
  --github-json github_copilot_metrics_october.ndjson \
  --workbench-json api_usage_permodel_stats_202510281639.json \
  --workbench-questions-csv "User Details - October.csv" \
  --month 2025-10
```

### Custom Date Range

```bash
# Analyze a specific date range
python combined_adoption_report.py \
  --github-json githubusage.json \
  --workbench-json api_usage_permodel_stats.json \
  --start-date 2025-09-01 \
  --end-date 2025-09-30
```

### Custom Output Paths

```bash
python combined_adoption_report.py \
  --github-json githubusage.json \
  --workbench-json api_usage_permodel_stats.json \
  --month 2025-09 \
  --csv-output september_adoption.csv \
  --html-output september_adoption.html
```

## Command-Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--github-json` | Yes | Path to GitHub Copilot usage JSON file |
| `--workbench-json` | Yes | Path to Workbench (API) usage JSON file exported from the database |
| `--workbench-questions-csv` | Yes | Path to Workbench questions CSV file exported from Graphana (e.g. "User Details - October.csv") |
| `--month` | No* | Month in YYYY-MM format |
| `--start-date` | No* | Start date in YYYY-MM-DD format |
| `--end-date` | No* | End date in YYYY-MM-DD format |
| `--csv-output` | No | CSV output path (default: combined_adoption_report.csv) |
| `--html-output` | No | HTML output path (default: combined_adoption_report.html) |

*Either `--month` OR both `--start-date` and `--end-date` must be provided.

## Input Data Requirements

### GitHub Copilot Data Format

The script expects newline-delimited JSON with records containing:

```json
{
  "user_login": "username",
  "day": "2025-09-15",
  "user_initiated_interaction_count": 25,
  "code_generation_activity_count": 18,
  "code_acceptance_activity_count": 12,
  "used_agent": true,
  "totals_by_model_feature": [...]
}
```

### Workbench (API) Data Format

The script expects JSON array or newline-delimited JSON with records containing:

```json
{
  "email": "user@example.com",
  "date": "2025-09-15T10:30:00Z",
  "model": "gpt-4",
  "api_requests": 5,
  "spend": 0.15,
  "manager_email": "manager@example.com"
}
```

### Email Mappings

The script uses `useremails.csv` to provide allowed emails and user metadata (chapter, squad). If present, `email_to_github_mappings.json` is used to map GitHub usernames to email addresses:

```json
{
  "github_username": "user@example.com"
}
```

If this file is not present, GitHub usernames will be used as identifiers.

## Output Reports

### CSV Report

The CSV report contains:

1. **Adoption Summary Statistics**
   - Report period and business days
   - Total users, MAU, adoption rate
   - Consistency metrics (median, p75, p90)
   - Threshold shares (15+ days, 20+ days, 80%+ consistency)
   - Intensity metrics
   - Platform usage breakdown

2. **Per-User Adoption Statistics**
   - Email and GitHub login
   - Days active and consistency rate
   - Total requests and requests per active day
   - GitHub metrics (requests, code gen/accept, agent, Roo)
   - Workbench metrics (requests by type, spend, models)

### HTML Report

The HTML report provides:

1. **Visual Summary Dashboard**
   - Color-coded stat cards for key metrics
   - Organized by category (adoption, consistency, thresholds, platforms, intensity)

2. **Interactive Per-User Table**
   - Sortable columns
   - Color-coded consistency rates:
     - 🟢 Green: 80%+ consistency (excellent)
     - 🟡 Yellow: 50-79% consistency (good)
     - 🔴 Red: <50% consistency (needs improvement)
   - Hover effects for easy reading

3. **Legend and Documentation**
   - Metric definitions
   - Color coding explanation
   - Platform abbreviations

## Understanding the Metrics

### Business Days Calculation

The script automatically calculates business days (weekdays only) in the reporting period:
- Excludes weekends (Saturday and Sunday)
- Does NOT currently exclude holidays (can be enhanced)

### Active Day Definition

A user has an "active day" if they have at least one qualifying request on that calendar day from either:
- GitHub Copilot (any user-initiated interaction)
- Workbench (any API request)

Days are deduplicated across both platforms.

### Consistency Rate Interpretation

| Consistency Rate | Interpretation | Action |
|-----------------|----------------|--------|
| 80-100% | Excellent daily adoption | Celebrate and maintain |
| 50-79% | Good regular usage | Encourage daily habits |
| 20-49% | Sporadic usage | Coaching opportunity |
| 0-19% | Minimal adoption | Investigate barriers |

### Setting Adoption Targets

Based on the goal of "everyone uses AI daily," recommended targets:

- **Near-term (3 months)**:
  - MAU: 85%+ of total users
  - Median consistency: 60%+
  - Users with 15+ days: 70%+

- **Medium-term (6 months)**:
  - MAU: 90%+ of total users
  - Median consistency: 70%+
  - Users with 20+ days: 60%+
  - Users with 80%+ consistency: 40%+

- **Long-term (12 months)**:
  - MAU: 95%+ of total users
  - Median consistency: 80%+
  - Users with 80%+ consistency: 60%+

## Comparison with Individual Reports

### vs. `github_stats_analyzer.py`

- **GitHub Stats**: Focuses on GitHub Copilot metrics only
- **Combined Report**: Merges GitHub + Workbench for complete adoption view
- **Use GitHub Stats when**: You only need GitHub Copilot analysis
- **Use Combined Report when**: You want full AI adoption picture

### vs. `ai_usage_from_json.py`

- **AI Usage**: Focuses on Workbench/API usage with hierarchy filtering
- **Combined Report**: Merges both platforms with adoption focus
- **Use AI Usage when**: You need detailed API cost/token analysis
- **Use Combined Report when**: You want adoption metrics across platforms

## Best Practices

### Regular Reporting Cadence

1. **Weekly**: Generate reports to track trends
2. **Monthly**: Deep dive into adoption patterns
3. **Quarterly**: Set and review adoption targets

### Segmentation Analysis

Run separate reports for:
- Different teams or departments
- New users vs. experienced users
- Different roles (developers, QA, etc.)

### Action Items from Reports

**Low Consistency (<50%)**:
- Schedule 1-on-1 coaching sessions
- Identify and remove adoption barriers
- Share success stories from high-consistency users

**Medium Consistency (50-79%)**:
- Encourage daily habit formation
- Share tips and best practices
- Set team adoption challenges

**High Consistency (80%+)**:
- Recognize and celebrate
- Ask to mentor others
- Gather feedback on what works

## Troubleshooting

### No Users Showing Up

- Check that date ranges match your data
- Verify email mappings file exists and is correct
- Ensure JSON files are properly formatted

### Inconsistent Numbers

- Verify both input files cover the same time period
- Check for duplicate records in source data
- Ensure email mappings are consistent

### Missing Metrics

- Some users may only appear in one platform (GitHub or Workbench)
- This is normal - the report shows combined and individual platform usage

## Future Enhancements

Potential additions:
- Holiday calendar support for accurate business day calculation
- Team/department hierarchy filtering
- Trend analysis across multiple months
- Adoption velocity metrics (week-over-week growth)
- Cohort analysis (adoption by join date)
- Daily Active Users (DAU) calculation with 7-day rolling average

## Support

For questions or issues:
1. Check this README for common scenarios
2. Review the example commands above
3. Examine the generated reports for data quality issues
4. Verify input file formats match the specifications

## License

Internal use only.