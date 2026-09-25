# Troubleshooting Common Error Messages

This article explains the most frequent TaskFlow error messages and how to fix them.

## "Something went wrong. Please try again." (Error 500)

A temporary server-side problem occurred. Refresh the page and try again. If it keeps happening, check **status.taskflow.io** for ongoing incidents. If there's no reported incident, contact support and include the **request ID** shown under the error message.

## "You don't have permission to do that" (Error 403)

Your role doesn't allow this action. For example, Members can't delete projects they didn't create, and Guests can't create new projects. Ask a workspace admin to change your role or project permissions. See "Roles and Permissions."

## "This project has been archived"

Archived projects are read-only. A project admin can restore it from **Project ⋯ → Unarchive**. On the Free plan, projects beyond the 3-project limit are archived automatically and can only be restored by upgrading or archiving another project.

## "Storage limit reached"

Your workspace has used all its file storage. Delete old attachments from **Admin → Storage**, which lists the largest files, or upgrade your plan. Free workspaces have 100 MB; Pro and Business have 10 GB per user.

## "File too large"

Individual attachments are limited to 100 MB on Free and 2 GB on paid plans. For larger files, link them from Google Drive, Dropbox, or OneDrive instead.

## "Session expired. Please sign in again."

For security, sessions expire after 30 days of inactivity, or sooner if your admin has set a shorter session timeout. Sign in again. If this happens repeatedly within minutes, your browser may be blocking cookies — allow cookies for `taskflow.io`.

## "Too many requests" (Error 429)

You or an integration is making requests too quickly. Wait one minute and try again. If you're using the API, see "API Access and Rate Limits" for current limits and how to handle backoff.

## "Conflict: this task was updated by someone else" (Error 409)

Two people edited the same task field at the same time. Refresh the task to see the latest version and reapply your change. Comments are never lost in conflicts.

## "Unable to connect. Check your internet connection."

The app can't reach TaskFlow servers. Check your network, VPN, or firewall. Corporate firewalls must allow `*.taskflow.io` on port 443 and WebSocket connections to `realtime.taskflow.io`.

## "Workspace is read-only"

This usually means a payment has failed or the subscription has lapsed. The workspace owner should update the payment method under **Settings → Billing**. See "Managing Billing and Payment Methods."

## Reporting a new error

When contacting support about an error, include the exact error text, the request ID if shown, the time it happened, your browser or app version, and the steps to reproduce it.
