# Additional Context (PRD & Knowledge Base)

> **Instructions:**
> Paste any relevant background documentation here. This can include the original PRD, database
> schema definitions, API documentation, or a glossary of terms. This helps the Judge understand
> domain-specific nuances.

## Glossary

- **"Active User":** Someone who has logged in within the last 30 days.
- **"Churned":** No login for > 90 days.

## Database Schema (Reference)

- Table: `users` (id, email, signup_date, status)
- Table: `orders` (id, user_id, amount, created_at)

## Original Feature Request (PRD Snippet)

> "The goal of this feature is to reduce the dependency on the data team for ad-hoc requests. It
> must be robust enough to handle messy natural language inputs."