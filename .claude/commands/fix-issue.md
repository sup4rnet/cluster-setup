---
allowed-tools: Glob,Grep,Read,Edit,Write,Task,Bash(git checkout -b:*),Bash(git add:*),Bash(git commit:*),Bash(git push:*),Bash(gh pr create:*),Bash(gh issue comment:*)
description: Analyze and fix a GitHub issue, creating a PR with the solution
---

# GitHub Issue Fix Assistant

You are helping fix an issue in this repository. Issues typically describe bugs, possible improvements to the documentation or feature requests.

## STEP 1: Determine Execution Environment

Detect whether you're running in **GitHub Actions** or **locally** via Claude Code CLI.

**Detection method:**
- If the values below contain actual data (not template syntax like `${{}}`), you're in **GitHub Actions**
- If you see template syntax like `${{` or values are missing, you're running **locally**

**GitHub Actions Context (auto-populated if running in CI):**
- Issue #: ${{ github.event.issue.number }}
- Title: ${{ github.event.issue.title }}
- Repository: ${{ github.repository }}

Issue body:
```
${{ github.event.issue.body }}
```

## STEP 2: Fetch Complete Issue Information

Based on the environment detected in STEP 1, invoke the appropriate fetch skill:

### If Running Locally:

Parse the issue number from the command arguments (e.g., from `/fix-issue 42`, extract "42").

If no issue number provided, ask: "What issue number would you like me to fix?"

Then invoke the local fetch skill:
```
/fetch-issue-local <issue-number>
```

### If Running in GitHub Actions:

The basic issue information is already provided above. Invoke the CI fetch skill to get complete context including comments:
```
/fetch-issue-ci
```

Pass the following information to the skill:
- Issue number: ${{ github.event.issue.number }}
- Issue title: ${{ github.event.issue.title }}
- Issue body: ${{ github.event.issue.body }}
- Repository: ${{ github.repository }}

### Result

After invoking the appropriate fetch skill, you will have complete issue information including:
- Issue number, title, body
- All comments and discussion
- Labels and assignees
- Creation and update timestamps

## STEP 3: Analyze the Issue

Review the complete issue data from STEP 2:

1. **Understand the original problem or request** from the issue body
2. **Review all comments** for:
   - Clarifications or corrections to the original request
   - Attempted solutions or workarounds discussed
   - Additional context from maintainers or other users
   - Related issues or PRs mentioned
   - Scope changes or requirement updates
3. **Consider labels and assignees** for context about priority and ownership
4. **Formulate the complete requirement** based on the entire discussion thread

## STEP 4: Fix the Issue

Now that you have the complete context:

1. **Explore the codebase** to find relevant files
2. **Make the necessary changes** to fix the issue
3. **Create a feature branch** named `fix/issue-<number>`
4. **Commit** with a descriptive message that explains what was changed and why
5. **Push** the branch to remote
6. **Create a Pull Request** that:
   - References the issue with "Fixes #<number>" in the description
   - Explains what was changed and why
   - Mentions any important discussion points from the issue comments

## If Unable to Fix

If you cannot fix the issue automatically, post a comment explaining why:

```bash
gh issue comment <number> -b "Unable to fix automatically because: <reason>"
```

## Important Guidelines

**DO:**
- Always detect execution environment first
- Always fetch complete issue history including ALL comments
- Review the entire discussion thread before starting work
- Create a new feature branch for the fix
- Reference the issue in your PR (use "Fixes #<number>")
- Consider context from comments that may clarify or modify the original request
- Ask the user for clarification if requirements are still unclear after reading all comments

**DON'T:**
- Make changes directly to the main branch
- Create a PR without referencing the issue
- Skip reading the comments - they often contain critical context
- Proceed without understanding the issue clearly

## Examples

### Example 1: Local Execution

```bash
# User runs:
/fix-issue 42

# You detect: Template variables not substituted (still showing ${{}})
# You should:
# 1. Parse "42" from command arguments
# 2. Invoke: /fetch-issue-local 42
# 3. Review complete issue data (original + all comments)
# 4. Analyze requirements
# 5. Fix the issue
# 6. Create branch, commit, push, create PR
```

### Example 2: GitHub Actions Execution

```yaml
# GitHub Actions provides:
# Issue #: 42
# Title: "Fix typo in README"
# Body: "There's a typo in line 50..."
# Repository: "org/repo"

# You detect: Actual values present (not template syntax)
# You should:
# 1. Invoke: /fetch-issue-ci (with provided issue number, title, body, repo)
# 2. Review complete data including any comments (e.g., "actually line 52, not 50")
# 3. Analyze requirements from full discussion
# 4. Fix the issue
# 5. Create branch, commit, push, create PR
```
