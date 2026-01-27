#!/usr/bin/env python3
import os
import sys
import requests
import datetime

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    print('GITHUB_TOKEN not set', file=sys.stderr)
    sys.exit(1)

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github+json'
}

OWNER = 'puck02'
SINCE = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat() + 'Z'

def list_repos(owner):
    repos = []
    page = 1
    while True:
        r = requests.get(f'https://api.github.com/users/{owner}/repos', headers=HEADERS,
                         params={'per_page': 100, 'page': page, 'type': 'owner', 'sort': 'updated'})
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos

def repo_has_commits(full_name, since):
    r = requests.get(f'https://api.github.com/repos/{full_name}/commits', headers=HEADERS,
                     params={'since': since, 'per_page': 100})
    r.raise_for_status()
    data = r.json()
    return data

def main():
    repos = list_repos(OWNER)
    activity_lines = []
    for repo in repos:
        full = repo.get('full_name')
        name = repo.get('name')
        html = repo.get('html_url')
        try:
            commits = repo_has_commits(full, SINCE)
        except requests.HTTPError as e:
            print(f'Failed to fetch commits for {full}: {e}', file=sys.stderr)
            continue
        if commits:
            count = len(commits)
            activity_lines.append(f'- [{name}]({html}) — {count} commit{'+'s' if count!=1 else ''} in last 30 days')

    if not activity_lines:
        body = 'No repositories with commits in the last 30 days.'
    else:
        body = '\n'.join(activity_lines)

    readme = 'README.md'
    start = '<!-- ACTIVITY:START -->'
    end = '<!-- ACTIVITY:END -->'
    if not os.path.exists(readme):
        print('README.md not found', file=sys.stderr)
        sys.exit(1)

    with open(readme, 'r', encoding='utf-8') as f:
        text = f.read()

    new_block = f"{start}\n\n{body}\n\n{end}"
    if start in text and end in text:
        import re
        text2 = re.sub(re.escape(start) + r'.*?' + re.escape(end), new_block, text, flags=re.S)
    else:
        # insert before the final footer (---) if markers not present
        if '\n---\n' in text:
            text2 = text.replace('\n---\n', f'\n---\n\n{new_block}\n\n')
        else:
            text2 = text + '\n\n' + new_block

    with open(readme, 'w', encoding='utf-8') as f:
        f.write(text2)
    print('README updated with activity')

if __name__ == '__main__':
    main()
