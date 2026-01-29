---
name: fetch-issue-ci
description: Fetch complete GitHub issue details when running in GitHub Actions environment
allowed-tools: Bash
disable-model-invocation: true
---

# Fetch Issue Details (GitHub Actions)

Fetch complete GitHub issue information when running in GitHub Actions environment.

## Input

You receive from GitHub Actions context:
- `$ARGUMENTS[0]`: Issue number
- Environment variables with issue title, body, and repository

## Process

### 1. Validate Input

Ensure the issue number is provided:
```bash
if [ -z "$0" ]; then
  echo "Error: Issue number required"
  exit 1
fi
```

### 2. Fetch Complete Issue Data

Get all issue details including comments:
```bash
gh issue view $0 --json number,title,body,comments,labels,assignees,state,createdAt,updatedAt,author
```

### 3. Display Structured Output

```
=== Issue #$0 ===
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

If `gh issue view` fails:
- Log the error
- Use environment variables as fallback
- Note: "Using limited issue data from GitHub Actions context"
