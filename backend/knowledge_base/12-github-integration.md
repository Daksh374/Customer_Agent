# Connecting TaskFlow to GitHub

The GitHub integration links your code to your tasks. Pull requests, commits, and branches that mention a task ID appear directly on the task, and tasks can be completed automatically when a PR is merged. Available on Pro, Business, and Enterprise plans.

## Installing the GitHub app

1. Go to **Settings → Integrations → GitHub** in TaskFlow. You must be a workspace admin.
2. Click **Install GitHub App**.
3. Choose the GitHub organization or personal account.
4. Select **All repositories** or pick specific repositories.
5. Click **Install & Authorize**.

GitHub organization owners may need to approve the installation if your organization restricts third-party apps.

## Linking code to tasks

Every TaskFlow task has a short ID shown in the task header, such as `TF-1042`. Include this ID in:

- A **branch name**: `tf-1042-fix-login-redirect`
- A **commit message**: `Fix redirect loop (TF-1042)`
- A **pull request title or description**: `TF-1042: Fix login redirect`

TaskFlow detects the ID and adds a **Development** panel to the task showing linked branches, commits, and PR status (open, draft, merged, closed).

## Automations

Admins can configure automations under **Settings → Integrations → GitHub → Automations**:

- **When a PR is opened**, move the task to "In Review."
- **When a PR is merged**, mark the task complete.
- **When a PR is closed without merging**, move the task back to "In Progress."

Use the keyword `closes TF-1042` in a PR description to trigger completion only for that specific task.

## Privacy

TaskFlow stores only metadata: PR titles, branch names, commit messages, author, and status. We never store or read your source code.

## Troubleshooting

**PRs aren't showing up on tasks** — Confirm the repository is included in the GitHub app's repository access list. Go to GitHub → Settings → Applications → TaskFlow → Configure. Also check that the task ID is formatted correctly (e.g., `TF-1042`, not `TF 1042`).

**"Resource not accessible by integration" error** — The GitHub app is missing a permission, often after GitHub requires re-approval following an app update. An organization owner should accept the updated permissions in GitHub.

**Automations didn't run** — Automations only run on PRs created *after* they were enabled. Verify the automation is enabled for the correct project.

**Using GitHub Enterprise Server** — Self-hosted GitHub Enterprise Server is supported on TaskFlow's Enterprise plan only. Contact your account manager for setup.

## Disconnecting

Uninstall the TaskFlow app from GitHub, or click **Disconnect** in TaskFlow's integration settings. Existing links on tasks remain as plain text.
