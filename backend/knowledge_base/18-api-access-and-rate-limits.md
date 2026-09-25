# API Access and Rate Limits

The TaskFlow REST API lets developers build custom integrations, automate workflows, and sync data with other systems. The API is available on **Pro, Business, and Enterprise** plans.

## Creating an API key

1. Go to **Settings → Developer → API keys**.
2. Click **Create API key**.
3. Give it a descriptive name, such as "Reporting script."
4. Choose a scope: **Read only** or **Read and write**.
5. Copy the key immediately. For security, it's shown only once.

API keys act on behalf of the user who created them and inherit that user's permissions. If the user is removed from the workspace, their API keys are revoked automatically.

## Authentication

Include your key in the `Authorization` header of every request:

```
Authorization: Bearer tf_live_xxxxxxxxxxxxxxxx
```

The base URL is `https://api.taskflow.io/v2`. All requests must use HTTPS.

## Rate limits

| Plan | Requests per minute | Requests per day |
|---|---|---|
| Pro | 100 | 50,000 |
| Business | 300 | 200,000 |
| Enterprise | 1,000 | Custom |

Rate limits are applied **per API key**. Every response includes these headers:

- `X-RateLimit-Limit` — your per-minute limit
- `X-RateLimit-Remaining` — requests remaining in the current window
- `X-RateLimit-Reset` — Unix time when the window resets

If you exceed the limit, the API returns **HTTP 429 Too Many Requests** with a `Retry-After` header. Your code should wait the specified number of seconds before retrying. We recommend exponential backoff for repeated 429s.

## Pagination

List endpoints return up to 100 items per page. Use the `cursor` value from the response's `next_cursor` field to fetch the next page.

## Webhooks

Webhooks send real-time HTTP POST notifications to your server when events happen, such as `task.created`, `task.completed`, or `comment.added`. Create webhooks under **Settings → Developer → Webhooks**. Each request is signed with an `X-TaskFlow-Signature` HMAC-SHA256 header so you can verify it came from TaskFlow. Webhooks that fail repeatedly for 24 hours are automatically disabled, and the owner is notified by email.

## Common API errors

- **401 Unauthorized:** The API key is missing, invalid, or revoked.
- **403 Forbidden:** The key's user lacks permission for this resource, or the key is read-only.
- **404 Not Found:** The resource doesn't exist or isn't visible to this user.
- **422 Unprocessable Entity:** The request body failed validation; the response explains which field.

## Rotating and revoking keys

Rotate keys regularly. To revoke a key, go to **Settings → Developer → API keys** and click **Revoke**. Revocation is immediate. If you believe a key was leaked, revoke it right away and create a new one.
