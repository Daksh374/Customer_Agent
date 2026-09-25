# Troubleshooting Login Issues

If you can't sign in to TaskFlow, work through the steps below. Most login problems are resolved in under five minutes.

## Check your email address

TaskFlow accounts are tied to a single email address. If your company uses multiple domains (for example `acme.com` and `acme.io`), make sure you are using the address you originally signed up with. Email addresses are not case-sensitive, but typos such as a missing letter or an extra period are a common cause of the "Account not found" message.

## Single Sign-On (SSO) accounts

If your workspace uses SSO through Google Workspace, Microsoft Entra ID, or Okta, you cannot sign in with a password. Click **Continue with SSO** on the login page and enter your work email. You will be redirected to your identity provider. If SSO fails, contact your internal IT administrator — TaskFlow support cannot reset SSO credentials because they are managed by your identity provider.

## "Invalid email or password"

This message appears when the password does not match. After five failed attempts, your account is temporarily locked for 15 minutes to protect against brute-force attacks. Wait for the lockout to expire, or use the **Forgot password?** link to set a new password immediately. See the "Resetting Your Password" article for details.

## Browser problems

Login issues are frequently caused by the browser rather than your account:

- **Clear cookies and cache** for `app.taskflow.io`, then reload the page.
- **Disable browser extensions** such as ad blockers or privacy tools, which can block the login script.
- **Try a private/incognito window** to rule out stored session data.
- Make sure you are using a supported browser: the latest two versions of Chrome, Firefox, Safari, or Edge.

## Desktop and mobile apps

If the TaskFlow desktop or mobile app is stuck on the login screen, sign out completely, force-quit the app, and reopen it. Make sure the app is updated to the latest version from the App Store, Google Play, or taskflow.io/download. Versions older than 12 months are no longer supported and may fail to authenticate.

## Account suspended or deactivated

If you see "Your account has been deactivated," a workspace admin has removed or suspended your seat. Contact your workspace owner to be re-added. If you are the owner and see a "Workspace suspended" message, your subscription payment may have failed — see "Managing Billing and Payment Methods."

## Still stuck?

If none of these steps help, contact support with your account email, the exact error message, your browser and operating system, and a screenshot if possible. Never share your password with anyone, including TaskFlow support staff.
