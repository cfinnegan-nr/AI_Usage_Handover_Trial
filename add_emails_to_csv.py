import csv
import json
import re

# These emails are only for the members of engineering

def add_emails_to_csv():
    # Load the email mappings
    with open('email_to_github_mappings.json', 'r') as f:
        email_mappings = json.load(f)
    
    # Read the original CSV
    with open('github_stats_report.csv', 'r') as f:
        lines = f.readlines()
    
    # Process the CSV
    updated_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Handle the header section (lines 1-7)
        if i < 7:
            updated_lines.append(line)
        # Handle the column headers (line 8)
        elif i == 7:
            # Add Email column after User Login
            parts = line.split(',')
            new_header = parts[0] + ',' + parts[1] + ',Email,' + ','.join(parts[2:])
            updated_lines.append(new_header)
        # Handle data rows (lines 9+)
        else:
            parts = line.split(',')
            if len(parts) >= 2:
                user_login = parts[1]
                email = email_mappings.get(user_login, '')
                # Insert email after User Login
                new_line = parts[0] + ',' + parts[1] + ',' + email + ',' + ','.join(parts[2:])
                updated_lines.append(new_line)
            else:
                updated_lines.append(line)
    
    # Write the updated CSV
    with open('github_stats_report_with_emails.csv', 'w') as f:
        for line in updated_lines:
            f.write(line + '\n')
    
    print("Successfully created github_stats_report_with_emails.csv with email addresses added")

def add_emails_to_html():
    # Load the email mappings
    with open('email_to_github_mappings.json', 'r') as f:
        email_mappings = json.load(f)
    
    # Read the original HTML
    with open('github_stats_report.html', 'r') as f:
        html_content = f.read()
    
    # Add Email column to the table header
    header_pattern = r'(<th>User Login</th>)'
    header_replacement = r'\1\n                        <th>Email</th>'
    html_content = re.sub(header_pattern, header_replacement, html_content)
    
    # Add email data to each table row
    # Pattern to match table rows with user login
    row_pattern = r'<tr>\s*<td>([^<]+)</td>'
    
    def replace_row(match):
        user_login = match.group(1)
        email = email_mappings.get(user_login, '')
        return f'<tr>\n                        <td>{user_login}</td>\n                        <td>{email}</td>'
    
    html_content = re.sub(row_pattern, replace_row, html_content)
    
    # Write the updated HTML
    with open('github_stats_report_with_emails.html', 'w') as f:
        f.write(html_content)
    
    print("Successfully created github_stats_report_with_emails.html with email addresses added")

if __name__ == "__main__":
    add_emails_to_csv()
    add_emails_to_html()