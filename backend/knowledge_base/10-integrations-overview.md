# Integrations Overview

TaskFlow connects with the tools your team already uses. Integrations are available on the **Pro, Business, and Enterprise** plans unless noted otherwise.

## Available integrations

| Integration | What it does | Plan |
|---|---|---|
| Slack | Create tasks from messages, get notifications in channels | Pro+ |
| Google Calendar | Sync task due dates to your calendar | Pro+ |
| Microsoft Teams | Notifications and task creation from Teams | Pro+ |
| GitHub | Link pull requests and commits to tasks | Pro+ |
| GitLab | Link merge requests to tasks | Business+ |
| Google Drive / Dropbox / OneDrive | Attach cloud files to tasks | Free+ |
| Zapier | Connect to 5,000+ apps with no-code automations | Pro+ |
| Email-to-task | Forward emails to create tasks | Free+ |

## Connecting an integration

1. Go to **Settings → Integrations**.
2. Find the integration and click **Connect**.
3. You'll be redirected to the other service to approve access.
4. Return to TaskFlow and configure options (such as which project new tasks go to).

Some integrations are connected **per user** (Google Calendar, cloud storage), while others are connected **per workspace** and require admin rights (Slack, GitHub, Microsoft Teams).

## Permissions and security

TaskFlow requests only the minimum permissions each integration needs. Integration tokens are encrypted at rest. Workspace admins can review all connected integrations and revoke them from **Admin → Integrations**. When a user leaves the workspace, their personal integrations are automatically disconnected.

## Disconnecting an integration

Go to **Settings → Integrations**, find the integration, and click **Disconnect**. Disconnecting stops syncing immediately. Data that was already created (for example, tasks created from Slack messages) remains in TaskFlow.

## Integration stopped working

The most common reasons an integration stops working:

- **Expired authorization:** Tokens for some services expire. Click **Reconnect** on the integration.
- **Plan change:** If you downgraded to Free, Pro-level integrations are disabled. Upgrade and reconnect.
- **The person who connected it left:** Workspace-level integrations are tied to the admin who installed them. If that person is removed, another admin must reconnect the integration.
- **Permissions changed on the other service:** For example, the TaskFlow Slack app was removed from a channel.

## Webhooks and API

For custom integrations, use the TaskFlow REST API and webhooks. See "API Access and Rate Limits." Detailed setup guides are available for Slack and GitHub in their own articles.

## Requesting a new integration

Have a tool you'd like us to support? Submit a request at taskflow.io/integrations/request. We review requests monthly and prioritize based on demand.
