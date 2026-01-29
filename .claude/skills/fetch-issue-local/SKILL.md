---
name: fetch-issue-local
description: Fetch complete GitHub issue details when running locally via Claude Code CLI
allowed-tools: Bash
disable-model-invocation: true
argument-hint: <issue-number>
---

# Fetch Issue Details (Local)

Fetch complete GitHub issue information when running locally.

## Usage

```
/fetch-issue-local <issue-number>
```

## Process

### 1. Get Repository

Determine current repository from git remote:
```bash
git remote get-url origin
```

Parse the repository name:
- `https://github.com/org/repo.git` → `org/repo`
- `git@github.com:org/repo.git` → `org/repo`

### 2. Fetch Issue

Get complete issue details:
```bash
gh issue view $ARGUMENTS --json number,title,body,comments,labels,assignees,state,createdAt,updatedAt,author
```

### 3. Display Output

```
=== Issue #$ARGUMENTS ===
Repository: <org/repo>
Title: <title>
State: <state>
Author: @<author>
Created: <createdAt>
Updated: <updatedAt>
Labels: <labels>
Assignees: <assignees>

=== Description ===
<body>

=== Comments (<count>) ===
[For each comment:]
@<author> on <date>:
<comment-body>

=== End ===
```

## Error Handling

- **No issue number**: "Error: Issue number required. Usage: /fetch-issue-local <number>"
- **Not a git repo**: "Error: Not in a git repository"
- **Issue not found**: Show `gh` error message
- **Auth required**: "Error: GitHub authentication required. Run: gh auth login"
