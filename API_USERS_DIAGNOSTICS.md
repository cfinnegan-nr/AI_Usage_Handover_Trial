# API Users Zero - Diagnostic Guide

## Problem
The 'API Users' number and 'API number' column are showing zero in the output reports when running:
```
python combined_adoption_report.py --github-json github_copilot_metrics_jan_2026.json --workbench-json api_usage_permodel_stats_202601211142.json --workbench-questions-csv "Workbench User Details - Jan26.csv" --month 2026-01 --csv-output jan26_adoption_non_c.csv --html-output jan26_adoption_non_c.html
```

## Diagnostic Logging Added

Comprehensive diagnostic logging has been added to `combined_adoption_report.py` to help identify where API usage data is being filtered out or lost. The diagnostics will appear in the console output when you run the script.

### 1. Workbench Data Loading Diagnostics (`load_workbench_data` method)

**Location:** Lines 386-425

**What it checks:**
- Total records loaded from JSON file
- Records filtered due to missing email
- Records filtered due to missing date
- Records filtered due to date parsing errors
- Records filtered due to date being outside the requested range
- Records successfully processed
- Total API requests aggregated
- Unique users with data
- Record field names found in JSON
- Sample emails and dates
- Whether 'api_requests' field exists in records
- Users with non-zero api_requests_total

**What to look for:**
1. **If 'api_requests' field not found:**
   - The JSON file may use a different field name (e.g., 'requests', 'count', 'usage_count')
   - Check the "Available fields" list to find the correct field name
   - **Fix:** Update line 325 to use the correct field name: `api_requests = record.get('correct_field_name', 0)`

2. **If all records filtered by date:**
   - Dates in JSON may be in a different format than expected
   - Date range may not overlap with data in file
   - **Fix:** Check date format in JSON and adjust parsing logic (lines 296-308)

3. **If all records filtered by missing email:**
   - Email field may have a different name (e.g., 'user_email', 'email_address')
   - **Fix:** Update line 287 to use the correct field name

4. **If no users have api_requests_total > 0:**
   - The field name is wrong OR
   - All values are actually zero OR
   - The field contains strings instead of numbers
   - **Fix:** Check sample record values shown in diagnostics

### 2. Merge Diagnostics (`merge_user_data` method)

**Location:** Lines 468-485

**What it checks:**
- Number of users in GitHub data
- Number of users in Workbench data
- Workbench users with api_requests_total > 0
- Sample users with requests

**What to look for:**
- If workbench_data is empty, the issue is in the loading phase
- If workbench_data has users but none have requests > 0, check the field name or data values

### 3. Workbench Users Calculation Diagnostics (`calculate_adoption_metrics` method)

**Location:** Lines 625-645

**What it checks:**
- Total active users
- Users with workbench_requests_total > 0
- Sample workbench_requests_total values
- Sample users showing their workbench_requests_total values

**What to look for:**
- If all users have workbench_requests_total = 0, the data is not being properly merged
- Check if the field name in merged_users matches what's expected

## Common Issues and Fixes

### Issue 1: Wrong Field Name in JSON

**Symptom:** Diagnostic shows "'api_requests' field not found in record keys"

**Solution:**
1. Check the "Available fields" list in diagnostics
2. Look for fields containing "request", "count", or "usage"
3. Update line 325 in `load_workbench_data`:
   ```python
   # Change from:
   api_requests = record.get('api_requests', 0)
   # To:
   api_requests = record.get('actual_field_name', 0)
   ```

### Issue 2: Date Format Mismatch

**Symptom:** All records filtered by "date parse error" or "date out of range"

**Solution:**
1. Check sample dates shown in diagnostics
2. Verify date format matches expected ISO format
3. Adjust date parsing logic (lines 296-308) if needed
4. Check if date range (2026-01) matches dates in JSON file

### Issue 3: Email Field Name Mismatch

**Symptom:** All records filtered by "no email"

**Solution:**
1. Check sample record keys for email-related fields
2. Update line 287:
   ```python
   # Change from:
   email = record.get('email', '').lower()
   # To:
   email = record.get('user_email', '').lower()  # or whatever the field is named
   ```

### Issue 4: Date Range Doesn't Match Data

**Symptom:** All records filtered by "date out of range"

**Solution:**
1. Check sample dates in diagnostics
2. Verify the --month parameter matches the actual data dates
3. The JSON file may contain data for a different month than 2026-01

### Issue 5: Numeric vs String Values

**Symptom:** Field exists but values are always zero

**Solution:**
1. Check sample values shown in diagnostics
2. If values are strings, add conversion:
   ```python
   api_requests = record.get('api_requests', 0)
   try:
       api_requests = int(api_requests) if api_requests else 0
   except (ValueError, TypeError):
       api_requests = 0
   ```

## Running the Diagnostics

Simply run your command as normal:
```bash
python combined_adoption_report.py --github-json github_copilot_metrics_jan_2026.json --workbench-json api_usage_permodel_stats_202601211142.json --workbench-questions-csv "Workbench User Details - Jan26.csv" --month 2026-01 --csv-output jan26_adoption_non_c.csv --html-output jan26_adoption_non_c.html
```

The diagnostic output will appear in the console between the normal processing messages. Look for sections marked with:
- `=== WORKBENCH DATA LOADING DIAGNOSTICS ===`
- `=== MERGE DIAGNOSTICS ===`
- `=== WORKBENCH USERS CALCULATION DIAGNOSTICS ===`

## Next Steps

1. Run the script and capture the diagnostic output
2. Identify which filter is removing all records (or if the field name is wrong)
3. Apply the appropriate fix based on the diagnostic findings
4. Re-run to verify the fix

## Removing Diagnostics (After Fix)

Once the issue is resolved, you can remove the diagnostic code by:
1. Removing the diagnostic print statements (lines 386-425, 468-485, 625-645)
2. Or keeping them for future debugging

The diagnostic code does not change the core logic - it only adds logging to help identify the issue.
