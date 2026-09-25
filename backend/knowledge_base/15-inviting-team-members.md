# Inviting and Managing Team Members

TaskFlow is built for teams. This article explains how to invite people to your workspace, manage pending invitations, and remove members.

## Who can invite members

By default, **owners and admins** can invite new members. Owners can allow regular Members to send invitations under **Admin → Settings → Member invitations**. Guests can never invite others.

## Inviting members by email

1. Click **Invite** in the left sidebar, or go to **Admin → Members → Invite members**.
2. Enter one or more email addresses, separated by commas.
3. Choose a role: **Admin**, **Member**, or **Guest**.
4. Optionally, select projects to add them to right away.
5. Click **Send invitations**.

Invitees receive an email with a link to join. Invitations expire after **14 days**.

## Invite links

Admins can create a shareable invite link from **Admin → Members → Invite link**. Anyone with the link can join as a Member. You can restrict the link to specific email domains (for example, only `@yourcompany.com`) and reset the link at any time to invalidate the old one.

## Domain auto-join

On Business and Enterprise plans, admins can let anyone with a verified company email join automatically. Go to **Admin → Security → Verified domains**, add your domain, and verify it with a DNS TXT record.

## Pending invitations

View pending invitations under **Admin → Members → Pending**. From here you can **resend** an invitation or **revoke** it. Pending invitations do not count toward your paid seats until they're accepted.

## Invitation not received

- Ask the invitee to check spam and search for emails from `no-reply@taskflow.io`.
- Confirm the email address is spelled correctly.
- Resend the invitation from the Pending tab.
- If the invitee's company blocks external emails, share an invite link instead.

## Removing a member

1. Go to **Admin → Members**.
2. Click the **⋯** next to the member's name and select **Remove from workspace**.
3. Choose who should receive their assigned tasks, or leave them unassigned.

Removed members immediately lose access. Their comments and task history remain in the workspace, attributed to their name. Their seat is freed and you'll receive a prorated credit on your next invoice.

## Deactivating vs. removing

**Deactivating** suspends access temporarily and keeps the user's seat reserved (and billed). Use this for extended leave. **Removing** frees the seat entirely.

## Transferring workspace ownership

Only the current owner can transfer ownership. Go to **Admin → Settings → Transfer ownership**, choose an existing admin, and confirm with your password. The previous owner becomes an admin. A workspace always has exactly one owner.

## Seat limits on Free

The Free plan allows up to 5 members. To invite more people, upgrade to Pro or Business.
