# App Is Slow or Not Syncing

TaskFlow syncs changes in real time across web, desktop, and mobile. If updates aren't appearing or the app feels slow, try the steps below.

## Check service status

Visit **status.taskflow.io** first. If there's an active incident, our team is already working on it, and you can subscribe to updates on that page.

## Changes aren't appearing for teammates

Real-time sync uses a WebSocket connection. If your teammates don't see your changes:

1. Look for the **sync indicator** in the bottom-left corner. A green dot means connected; yellow means reconnecting; red means offline.
2. If it's yellow or red, refresh the page.
3. If you're on a corporate network or VPN, ask IT to allow WebSocket connections to `realtime.taskflow.io` on port 443.

Changes made while offline are saved locally and sync automatically when your connection is restored.

## Mobile app not syncing

- Make sure the app is updated to the latest version.
- Pull down on any list to force a refresh.
- Check that **Background App Refresh** (iOS) or **Background data** (Android) is enabled for TaskFlow.
- As a last resort, sign out and sign back in. This clears the local cache but does not delete any data on the server.

## Desktop app is slow

- Update to the latest version from **Help → Check for updates**.
- Clear the local cache from **Help → Troubleshooting → Clear cache and restart**.
- Close unused tabs within the app. Each open project uses memory.

## Large projects load slowly

Projects with more than 5,000 tasks can take longer to load in board and timeline views. To improve performance:

- **Archive completed tasks** using **Project ⋯ → Archive completed tasks older than 30 days**.
- **Use filters** to show only the tasks you need.
- **Split large projects** into smaller projects linked by a portfolio (Business plan).
- Prefer **list view** for very large projects; it is the fastest view.

## Browser performance

- Use a supported browser (latest Chrome, Firefox, Safari, or Edge).
- Disable heavy browser extensions, which can slow down large pages.
- Enable hardware acceleration in your browser settings.

## Calendar sync delays

Google Calendar sync runs every 15 minutes, not in real time. If a due date change hasn't appeared after 30 minutes, disconnect and reconnect Google Calendar under **Settings → Integrations**.

## Still slow?

Contact support with your browser/app version, operating system, the project name, and a HAR file or performance recording if possible. You can generate a diagnostics report from **Help → Troubleshooting → Send diagnostics**, which shares technical logs (no task content) with our engineers.
