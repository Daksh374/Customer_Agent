# Resetting Your Password

You can reset your TaskFlow password at any time from the login page. This article explains the process and how to fix common issues with reset emails.

## How to reset your password

1. Go to `app.taskflow.io/login` and click **Forgot password?**
2. Enter the email address associated with your TaskFlow account.
3. Click **Send reset link**.
4. Open the email titled "Reset your TaskFlow password" and click the button inside.
5. Choose a new password and confirm it.

The reset link is valid for **60 minutes** and can only be used once. If it expires, simply request a new one. Requesting a new link invalidates all previous links.

## Password requirements

For security, your new password must:

- Be at least 12 characters long
- Contain at least one number and one letter
- Not match any of your last five passwords
- Not appear in known data-breach lists (we check against a hashed breach database)

We recommend using a password manager to generate and store a unique password.

## I didn't receive the reset email

If the email does not arrive within five minutes:

- **Check your spam or junk folder.** Search for messages from `no-reply@taskflow.io`.
- **Confirm the address.** We only send reset emails to addresses with an existing account. For privacy reasons, the page shows the same confirmation message whether or not an account exists.
- **Ask IT to allowlist our domain.** Corporate email filters sometimes quarantine automated emails. Ask your IT team to allowlist `taskflow.io`.
- **SSO users:** If your workspace uses Single Sign-On, password reset is disabled. Your password is managed by your identity provider (Google, Microsoft, or Okta), so contact your IT administrator instead.

## After resetting

Resetting your password signs you out of all other sessions, including the desktop and mobile apps. You will need to sign in again on each device. Any API keys you created remain valid; they are not affected by password changes.

If you have two-factor authentication enabled, you will still be asked for your 2FA code after resetting your password. Resetting a password does not disable 2FA.

## Changing your password while signed in

If you know your current password and just want to change it, go to **Settings → Account → Security** and click **Change password**. You'll need to enter your current password first.

## Suspicious activity

If you received a password reset email you did not request, someone may have entered your email by mistake. Your password has not changed unless the link was clicked. If you believe your account has been compromised, reset your password immediately, enable two-factor authentication, and contact support.
