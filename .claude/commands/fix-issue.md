---
allowed-tools: Bash(git checkout -b:*),Bash(git add:*),Bash(git commit:*),Bash(git push:*),Bash(gh pr create:*),Bash(gh issue comment:*),Bash(ansible:*),Bash(python:*)
description: Analyze and fix a GitHub issue, creating a PR with the solution
---

You are helping fix an issue in this repository. Issues typically describe bugs, possible improvements to the documentation or feature requests.

Issue #${{ github.event.issue.number }}: ${{ github.event.issue.title }}

Issue body:
${{ github.event.issue.body }}

Instructions:
1. Analyze the issue and understand what needs to be fixed
2. Explore the codebase to find relevant files
3. Make the necessary changes to fix the issue
4. Create a new branch named 'fix/issue-${{ github.event.issue.number }}'
5. Commit your changes with a descriptive message
6. Push the branch and create a PR that references this issue
7. The PR description should explain what was changed and why

If you cannot fix the issue automatically, comment on the issue explaining why.

DO:
- Create a new branch for the fix
- Make code changes to fix the issue
- Create a PR with a clear description
- Comment on the issue if unable to fix

DON'T:
- Do NOT make changes directly to the main branch
- Do NOT create a PR without referencing the issue
- Do NOT resolve the issue if the requirement is unclear, ask first instead
