# Harvest POS deployment plan

This plan separates a public preview from a production POS. The current app stores its working data in the browser, so a Vercel preview is not yet a shared 20-branch system.

## Prepared in this project

- [x] Vercel static-site configuration and `api/` serverless function structure.
- [x] Example environment-variable file and ignore rules for local secrets.
- [x] Supabase relational schema for organizations, branches, staff roles, products, branch-specific prices/costs, sale snapshots, payment sessions, and audit history.
- [x] Role-aware Row Level Security policies and an idempotent RPC foundation for offline cash-sale sync.
- [x] Owner and branch-manager authorization check for the server-side AI endpoint.
- [x] Paystack remains disabled in Vercel until persistent payment functions are connected.

## Required before staff can use it

- [ ] Create a Supabase project and a Vercel project connected to a private Git repository.
- [ ] Apply `supabase/schema.sql`; seed the branch list with `supabase/seed.sql` after confirming branch names.
- [ ] Add owner sign-in, staff invitation, and profile onboarding to the app. Remove the demo role switcher in production.
- [ ] Replace demo/localStorage catalog and reports with Supabase reads and writes, enforcing role and branch scope.
- [ ] Connect offline cash-sale queue to `record_offline_cash_sale`; show per-sale sync results and retain failed records for retry.
- [ ] Add server-side Paystack initialization, persistent payment-session storage, exact-amount verification, and callback reconciliation. Then enable `paystackEnabled`.
- [ ] Ensure assistant requests use the authenticated session and server-loaded role-scoped data.
- [ ] Replace sample products, prices, costs, and sales with approved business data.
- [ ] Configure HTTPS domain, environment variables, backups, logging, and production access controls.
- [ ] Review the preview on desktop/mobile and complete payment, permissions, offline retry, and report reconciliation checks before launch.

## Accounts and environment variables

Create projects in your own accounts at [Vercel](https://vercel.com/) and [Supabase](https://supabase.com/). In Vercel Project Settings → Environment Variables, add:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (server-only; never prefix with `NEXT_PUBLIC_` or put it in browser code)
- `PAYSTACK_SECRET_KEY` (only after payment endpoints are completed; start with a test key)
- `OPENAI_API_KEY` (optional)
- `OPENAI_MODEL` (optional; defaults in the function)

The secret keys belong in the providers' dashboards. Do not paste them into source files or chat. A Vercel preview can be deployed once the repository is connected, but production use should wait until the unfinished items above are complete.
