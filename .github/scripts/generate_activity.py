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
    cards = []
    for repo in repos:
        full = repo.get('full_name')
        name = repo.get('name')
        html = repo.get('html_url')
        desc = repo.get('description') or ''
        stars = repo.get('stargazers_count', 0)
        try:
            commits = repo_has_commits(full, SINCE)
        except requests.HTTPError as e:
            print(f'Failed to fetch commits for {full}: {e}', file=sys.stderr)
            continue
        if not commits:
            continue
        # take most recent commit date
        try:
            recent = commits[0]
            date_str = recent.get('commit', {}).get('author', {}).get('date')
            if date_str:
                last = date_str.split('T')[0]
            else:
                last = ''
        except Exception:
            last = ''

        card = f'''
<div style="border:1px solid #e1e4e8;border-radius:8px;padding:12px;width:260px;box-shadow:0 1px 3px rgba(0,0,0,0.04);margin:8px;">
  <a href="{html}" style="font-weight:600;color:#0366d6;text-decoration:none">{name}</a>
  <p style="margin:6px 0;color:#586069">{desc}</p>
  <p style="font-size:12px;color:#586069;margin-top:8px">⭐ {stars} • Last commit: {last}</p>
</div>
'''
        cards.append(card)

    if not cards:
        body = '<p>No repositories with commits in the last 30 days.</p>'
    else:
        # Use CSS grid to force two cards per row on wide layouts
        grid = (
            '<div style="display:grid;grid-template-columns:repeat(2, minmax(0,1fr));gap:12px;align-items:start">'
            + '\n'.join(cards) + '</div>'
        )
        body = grid

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
