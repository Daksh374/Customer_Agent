# Exporting Your Data

TaskFlow lets you export your workspace data at any time, on any plan. Your data belongs to you.

## Export formats

- **CSV:** Tasks, assignees, due dates, statuses, custom fields, and tags. Best for spreadsheets and reporting.
- **JSON:** A complete, structured export including comments, subtasks, dependencies, and activity history. Best for migrations or backups.
- **PDF:** A printable snapshot of a single project, available from the project menu.

## Exporting a single project

1. Open the project.
2. Click the **⋯** menu in the top-right corner.
3. Select **Export → CSV** or **Export → PDF**.

The file downloads directly to your browser. Project exports include only tasks you have permission to view.

## Exporting an entire workspace

Full workspace exports are available to **owners and admins** only.

1. Go to **Admin → Data → Export workspace**.
2. Choose **JSON** or **CSV (zipped)**.
3. Choose whether to include file attachments. Including attachments can make the export much larger.
4. Click **Start export**.

Large exports are processed in the background. You'll receive an email with a download link when it's ready — usually within a few minutes, but workspaces with more than 100,000 tasks or large attachments can take up to 24 hours. The download link is valid for **7 days**.

## What's included

A full JSON export includes: projects, sections, tasks, subtasks, comments, custom field values, tags, due dates, assignees, task dependencies, attachments (if selected), and the activity log for your plan's retention period.

**Not included:** passwords, API keys, integration tokens, and billing details.

## Exporting from the Free plan

Free workspaces can export everything, including archived projects that became read-only after a downgrade. Exports are never restricted by plan.

## Scheduled backups

Business and Enterprise workspaces can enable **scheduled exports** under **Admin → Data → Scheduled backups**. Exports can run daily or weekly and be delivered to Amazon S3, Google Cloud Storage, or an email link.

## Using the API for exports

Developers can export data programmatically with the TaskFlow REST API. See "API Access and Rate Limits" for authentication details. The `/v2/projects/{id}/tasks` endpoint supports pagination and returns up to 100 tasks per request.

## Troubleshooting exports

- **Export email never arrived:** Check spam and search for "Your TaskFlow export is ready." You can also download recent exports from **Admin → Data → Export history**.
- **CSV looks garbled in Excel:** Our CSVs use UTF-8 encoding. In Excel, use **Data → From Text/CSV** and choose UTF-8.
- **Export failed:** Retry once. If it fails again, try exporting without attachments and contact support with the export ID.
