# Managing Billing and Payment Methods

Only workspace **owners** and members with the **Billing admin** role can view or change billing details. This article covers payment methods, invoices, and what happens when a payment fails.

## Accessing billing settings

Go to **Settings → Billing**. Here you can see your current plan, number of paid seats, next billing date, payment method, and invoice history.

## Accepted payment methods

TaskFlow accepts:

- Visa, Mastercard, American Express, and Discover credit or debit cards
- Apple Pay and Google Pay (monthly plans only)
- ACH bank transfer (US customers on annual plans)
- Invoicing with bank wire transfer (annual plans with 25 or more seats)

We do not accept PayPal, cryptocurrency, or checks.

## Updating your card

1. Go to **Settings → Billing → Payment method**.
2. Click **Update card**.
3. Enter the new card details and billing address.
4. Click **Save**.

The new card will be used for your next charge. Updating the card does not trigger an immediate charge.

## Downloading invoices

All invoices and receipts are available under **Settings → Billing → Invoice history**. Click **Download PDF** next to any invoice. To add a company name, address, or VAT/tax ID to future invoices, edit **Billing details**. Invoices already issued cannot be changed retroactively, but support can reissue an invoice with corrected details within 30 days.

## How seat billing works

You are billed for every active member in your workspace. Guests (users invited to a single project with limited access) are free up to a limit of 5 guests per paid seat. When you add members mid-cycle, you are charged a prorated amount for the rest of the billing period. When you remove a member, you receive a prorated credit applied to your next invoice — not a cash refund.

## Failed payments

If a payment fails, we automatically retry the charge after 3, 5, and 7 days. The workspace owner receives an email after each failed attempt. If all retries fail:

- Day 14: The workspace becomes read-only. Members can view but not edit tasks.
- Day 30: The workspace is downgraded to the Free plan. Data above Free limits is preserved but locked.

Updating your payment method at any time during this period immediately retries the charge and restores full access.

## Unexpected charges

If you see a charge you don't recognize, check your invoice history for prorated seat charges, which are the most common cause. If you believe you were charged in error or want to dispute a charge, contact our billing team rather than filing a chargeback with your bank — disputes are usually resolved faster directly with us.
