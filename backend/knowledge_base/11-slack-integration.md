# Setting Up the Slack Integration

The TaskFlow Slack app lets your team create tasks from Slack messages, get notified about task updates in channels, and look up tasks without leaving Slack. It's available on Pro, Business, and Enterprise plans.

## Requirements

- A TaskFlow workspace **admin** or **owner** to install the app
- Permission to install apps in your Slack workspace (or approval from your Slack admin)

## Installing the Slack app

1. In TaskFlow, go to **Settings → Integrations → Slack**.
2. Click **Add to Slack**.
3. Choose the Slack workspace and review the requested permissions.
4. Click **Allow**.
5. Back in TaskFlow, each member can link their personal Slack account by clicking **Link my account**.

Linking personal accounts ensures that tasks created from Slack are attributed to the right person.

## Creating tasks from Slack

- **Message shortcut:** Hover over any message, click **⋯ → Create TaskFlow task**. The message text becomes the task description with a link back to Slack.
- **Slash command:** Type `/taskflow create Fix the login bug` in any channel.
- **Emoji reaction:** Admins can configure an emoji (default: ✅) that automatically turns a message into a task in a chosen project.

## Channel notifications

To post project updates to a Slack channel:

1. Open the project in TaskFlow.
2. Click **⋯ → Integrations → Slack notifications**.
3. Choose a channel and select which events to post: task created, completed, commented, due date changed, or assigned.

Private channels require that you first invite the TaskFlow bot with `/invite @TaskFlow`.

## Personal notifications

Members can receive direct messages from the TaskFlow bot when they're assigned a task, mentioned in a comment, or have tasks due soon. Configure these under **Settings → Notifications → Slack**.

## Troubleshooting

**"TaskFlow is not in this channel"** — Invite the bot to the channel with `/invite @TaskFlow`.

**Slash command returns "dispatch_failed"** — This usually means the Slack app authorization has expired. An admin should go to **Settings → Integrations → Slack** and click **Reconnect**.

**Tasks are created by the wrong person** — The member hasn't linked their personal Slack account. They should click **Link my account** in TaskFlow's Slack settings.

**Notifications stopped** — Check whether the admin who installed the Slack app has left the workspace. If so, another admin must reinstall the app. Also confirm your plan hasn't been downgraded to Free, which disables Slack.

## Uninstalling

Admins can remove the integration from **Settings → Integrations → Slack → Disconnect**, or from Slack's **Manage apps** page. Tasks previously created from Slack are not affected.
