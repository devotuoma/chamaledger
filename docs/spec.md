# Product specification

## Problem

Across East Africa, millions of people save and borrow through *chamas*: small
self-run savings groups. Most treasurers keep the books in a notebook or a
WhatsApp thread. That causes three recurring problems:

1. **Disputed balances.** Members cannot verify what they have paid in.
2. **Double entries.** A payment recorded twice, or never, is hard to detect.
3. **Invisible risk.** Nobody knows how much lending is overdue until the money
   is already gone.

## Users

| User | Goal |
| --- | --- |
| Treasurer | Record money in and out quickly, and trust the totals |
| Group member | See a fair and accurate position (read via the treasurer in v1) |

## Key user journey

> **A treasurer records a contribution, and the group's savings total reflects
> it.** This is the journey we instrument and alert on, because when it fails
> the group's trust in the ledger fails with it.

## Functional requirements

### FR-1 Members
- AC-1.1 A treasurer can add a member with a full name and phone number.
- AC-1.2 Phone numbers must be E.164 (`+256700000001`); others return 422.
- AC-1.3 A duplicate phone number returns 409.
- AC-1.4 A member can be deactivated. History is kept; nothing is deleted.

### FR-2 Contributions
- AC-2.1 A contribution has a member, a positive whole amount, a date and a
  unique reference, such as a mobile-money transaction ID.
- AC-2.2 Replaying the same reference with the same data returns the original
  record with 200 and creates nothing.
- AC-2.3 The same reference with different data returns 409.
- AC-2.4 Inactive or unknown members return 409 and 404 respectively.
- AC-2.5 Zero or negative amounts return 422.

### FR-3 Loans
- AC-3.1 A loan's principal cannot exceed 3x the member's total savings.
- AC-3.2 A member may have only one open loan at a time.
- AC-3.3 Interest is flat: `balance due = principal + principal * rate`.

### FR-4 Repayments
- AC-4.1 A repayment cannot exceed the outstanding balance (409).
- AC-4.2 A balance of zero closes the loan automatically.
- AC-4.3 Repayments are idempotent by reference, as in AC-2.2 and AC-2.3.

### FR-5 Dashboard
- AC-5.1 Shows member count, total savings, loans outstanding and PAR30.
- AC-5.2 **PAR30** = outstanding balance of open loans more than 30 days past
  their due date, divided by total outstanding balance.
- AC-5.3 A brand-new group shows zeros, not an error.

### FR-6 Reliability
- AC-6.1 The full system starts with one command.
- AC-6.2 Names, phone numbers and notes never reach telemetry.
- AC-6.3 A failing journey raises an alert within five minutes, and the on-call
  agent restores service or escalates without human input.

## Service level objectives

| Journey | SLI | Objective |
| --- | --- | --- |
| Record a contribution | Share of requests that do not end in a 5xx | 99% |
| Record a contribution | Share of requests under 1 second | 95% |

## Non-goals (v1)

- Authentication and multi-group tenancy. **Deployments hold demo data only.**
- Real mobile-money integration.
- Compound interest and penalty calculations.
