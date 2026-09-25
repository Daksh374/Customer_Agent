# Deleting Your Account or Workspace

Deletion in TaskFlow is **permanent and cannot be undone**. Before deleting anything, we strongly recommend exporting your data (see "Exporting Your Data").

## Leaving a workspace vs. deleting your account

- **Leaving a workspace** removes you from one workspace but keeps your TaskFlow login and other workspaces.
- **Deleting your personal account** removes your login, profile, and personal settings across all workspaces.
- **Deleting a workspace** permanently erases all projects, tasks, files, and comments in that workspace for every member.

## Leaving a workspace

Go to **Settings → Workspaces**, find the workspace, and click **Leave**. If you are the owner, you must transfer ownership to another admin first.

## Deleting your personal account

1. Go to **Settings → Account → Delete account**.
2. Review the list of workspaces you belong to. You cannot delete your account while you are the **owner** of a workspace with other members — transfer ownership or delete the workspace first.
3. Enter your password (or re-authenticate with SSO) and type `DELETE` to confirm.

Your comments and task history in shared workspaces remain but are attributed to "Deleted user."

## Deleting a workspace

Only the **workspace owner** can delete a workspace.

- **Free workspaces with no billing history:** Go to **Admin → Settings → Delete workspace**, type the workspace name, and confirm. Deletion happens immediately.
- **Workspaces with paid billing history:** For your protection, self-serve deletion is disabled. The owner must submit a deletion request to our support team. A support agent verifies ownership, confirms any outstanding balance is settled, and processes the deletion. This typically takes 2–3 business days.

## Grace period

After a workspace deletion is confirmed, data is kept in a **soft-deleted** state for **14 days**. During this window, the owner can contact support to restore it. After 14 days, data is permanently purged from our production systems. Backups are purged within 35 days.

## Active subscriptions

Deleting a workspace cancels its subscription. Deletion does **not** automatically trigger a refund; refunds follow the standard "Refund Policy." If you'd like to request a refund, do so before requesting deletion, because invoice history is removed once deletion is complete.

## Data privacy requests (GDPR / CCPA)

If you are exercising a legal right to erasure under GDPR, CCPA, or similar laws, contact our privacy team at privacy@taskflow.io. We respond to verified requests within 30 days. Please note that we may retain limited billing records where required by tax law.

## Accounts managed by your organization

If your account was created through your company's SSO or SCIM provisioning, you may not be able to delete it yourself. Contact your IT administrator, who controls your account lifecycle.
