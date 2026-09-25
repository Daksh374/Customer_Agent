# Setting Up Two-Factor Authentication (2FA)

Two-factor authentication adds a second layer of security to your TaskFlow account. Even if someone learns your password, they cannot sign in without the one-time code from your device.

## Enabling 2FA

1. Go to **Settings → Account → Security**.
2. Click **Enable two-factor authentication**.
3. Scan the QR code with an authenticator app such as Google Authenticator, Authy, 1Password, or Microsoft Authenticator.
4. Enter the six-digit code shown in the app to confirm.
5. Save your **recovery codes** in a safe place.

TaskFlow supports time-based one-time passwords (TOTP) and hardware security keys (WebAuthn/FIDO2, such as YubiKey). SMS codes are not supported because they are vulnerable to SIM-swap attacks.

## Recovery codes

When you enable 2FA, you receive ten single-use recovery codes. Each code can be used once in place of an authenticator code. Store them in a password manager or print them and keep them somewhere secure. You can generate a new set at any time from the Security page, which invalidates the old set.

## Lost access to your authenticator

If you lose your phone or authenticator app:

- **Use a recovery code** on the login screen by clicking **Use a recovery code instead**.
- **Ask a workspace admin.** Admins on Business and Enterprise plans can reset 2FA for members from **Admin → Members**. The member will be asked to set up 2FA again on their next login.
- **Contact support** if you are the only owner and have no recovery codes. For security reasons, we will need to verify your identity, which can take 3–5 business days. We may ask for billing details, account creation date, and the names of recent projects.

## Codes not working

If your authenticator codes are rejected, the most common cause is a clock mismatch on your phone. TOTP codes depend on accurate time. Enable automatic date and time in your phone's settings and try again. Also make sure you are using the TaskFlow entry in your authenticator, not a code for another service.

## Enforcing 2FA for a workspace

Owners and admins on Business and Enterprise plans can require 2FA for all members. Go to **Admin → Security → Require two-factor authentication**. Members without 2FA will be prompted to set it up the next time they sign in and cannot access workspace data until they do.

## Disabling 2FA

You can disable 2FA from **Settings → Account → Security** after entering a current code. If your workspace enforces 2FA, you cannot disable it.
