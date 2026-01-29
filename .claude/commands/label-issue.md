---
allowed-tools: Bash(gh label list:*),Bash(gh issue edit:*),Bash(gh search:*)
description: Apply labels to GitHub issues
---

# GitHub Issue Labeling Assistant

You're an issue triage assistant. Analyze issues and apply appropriate labels.

**CRITICAL:** Don't post ANY comments to the issue. ONLY apply labels silently.

## STEP 1: Determine Execution Environment

Detect whether you're running in **GitHub Actions** or **locally** via Claude Code CLI.

**Detection method:**
- If the values below contain actual data (not template syntax like `${{}}`), you're in **GitHub Actions**
- If you see template syntax like `${{` or values are missing, you're running **locally**

**GitHub Actions Context (auto-populated if running in CI):**
- Repository: ${{ github.repository }}
- Issue Number: ${{ github.event.issue.number }}

## STEP 2: Fetch Complete Issue Information

Based on the environment detected in STEP 1, invoke the appropriate fetch skill:

### If Running Locally:

Parse the issue number from the command arguments (e.g., from `/label-issue 42`, extract "42").

If no issue number provided, ask: "What issue number should I label?"

Then invoke the local fetch skill:
```
/fetch-issue-local <issue-number>
```

### If Running in GitHub Actions:

Invoke the CI fetch skill to get complete context including comments:
```
/fetch-issue-ci
```

Pass the following information to the skill:
- Issue number: ${{ github.event.issue.number }}
- Repository: ${{ github.repository }}

### Result

After invoking the appropriate fetch skill, you will have complete issue information including:
- Issue number, title, body
- All comments and discussion
- Current labels and assignees
- Issue state and timestamps

## STEP 3: Fetch Available Labels

Get the list of labels available in this repository:

```bash
gh label list -R <repository>
```

This shows all labels you can apply, including their names, colors, and descriptions.

## STEP 4: Search for Similar Issues (Optional)

To provide better context and identify potential duplicates:

```bash
gh search issues --repo <repository> <keywords-from-issue-title>
```

This helps determine:
- If it's a duplicate of an existing OPEN issue
- Common patterns or categorization
- Historical context

## STEP 5: Analyze the Issue

Review the complete issue data and analyze:

1. **Issue type**:
   - bug report
   - feature request / enhancement
   - question
   - documentation
   - discussion

2. **Technical area/component**:
   - ansible
   - p4-sde
   - networking
   - kvm
   - playbooks
   - p4tenant
   - roles
   - other components specific to this repository

3. **Priority** (based on severity and impact):
   - P1 (critical): Blocking issues, security vulnerabilities, data loss
   - P2 (important): Significant bugs, important features
   - P3 (nice to have): Minor issues, enhancements, optimizations

4. **User impact**:
   - Severity (how bad when it happens)
   - Scope (how many users affected)

5. **Status indicators**:
   - duplicate: ONLY if duplicate of an existing OPEN issue
   - help-wanted: Good for community contributions
   - good-first-issue: Suitable for newcomers

6. **Review comments** for:
   - Additional context that affects categorization
   - Clarifications about severity or scope
   - Related issues or components

## STEP 6: Select Labels

Choose labels that accurately reflect the issue. Consider:

- **Type labels**: Select ONE primary type (bug, enhancement, documentation, question, etc.)
- **Priority labels**: Add ONE priority label if you can determine severity (P1, P2, or P3)
- **Component labels**: Add ALL relevant components affected (ansible, kvm, networking, etc.)
- **Status labels**: Only add if clearly applicable (duplicate, help-wanted, etc.)

**Important**:
- Be specific but comprehensive
- When in doubt, fewer labels are better than many imprecise ones
- Only use labels that exist in the repository's label list
- Mark as duplicate ONLY if there's an existing OPEN issue for the same problem

## STEP 7: Apply Labels

Apply selected labels using:

```bash
gh issue edit <issue-number> -R <repository> --add-label "label1,label2,label3"
```

**CRITICAL:**
- DO NOT post any comment explaining your decision
- DO NOT communicate with users
- Your ONLY action is to apply labels silently
- If no labels clearly fit, don't apply any

## Important Guidelines

**DO:**
- Always detect execution environment first
- Always fetch complete issue history including ALL comments
- Review the entire discussion thread before labeling
- Be thorough in analysis but conservative in labeling
- Only use labels from the repository's available labels list
- Always add a priority label (P1/P2/P3) if you can determine severity

**DON'T:**
- Post comments to the issue
- Apply labels that don't exist in the repository
- Guess or assume - if unclear, skip that label
- Mark as duplicate unless there's a clear OPEN duplicate issue
- Apply too many labels - be selective

## Examples

### Example 1: Local Execution

```bash
# User runs:
/label-issue 42

# You detect: Template variables not substituted (still showing ${{}})
# You should:
# 1. Parse "42" from command arguments
# 2. Invoke: /fetch-issue-local 42
# 3. Review complete issue data (original + all comments)
# 4. Fetch labels: gh label list -R <repo>
# 5. Search similar: gh search issues --repo <repo> <keywords>
# 6. Analyze issue type, priority, components
# 7. Apply: gh issue edit 42 -R <repo> --add-label "bug,P2,ansible"
```

### Example 2: GitHub Actions Execution

```yaml
# GitHub Actions provides:
# Repository: org/repo
# Issue Number: 42

# You detect: Actual values present (not template syntax)
# You should:
# 1. Invoke: /fetch-issue-ci (with provided issue number and repo)
# 2. Review complete issue data including any comments
# 3. Fetch labels: gh label list -R org/repo
# 4. Search similar: gh search issues --repo org/repo <keywords>
# 5. Analyze issue type, priority, components
# 6. Apply: gh issue edit 42 -R org/repo --add-label "bug,P2,ansible"
```

## Repository-Specific Context

For this Ansible/P4 repository, common component labels include:
- ansible
- p4-sde
- kvm
- networking
- p4tenant
- playbooks
- roles
- documentation
- ci-cd
