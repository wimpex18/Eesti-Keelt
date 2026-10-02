# Public access: current blocker and required migration

The user requested an app that opens without a Cloudflare login. On 2026-10-01,
an anonymous request to `https://eesti-keelt.wimpex18.workers.dev/` still returned
302 to `winter-sound-e2a1.cloudflareaccess.com`.

This is Cloudflare Access at the front door, before application code runs.
The app already has independent in-app accounts and guest sandboxes. Removing
Access need not remove those accounts or move the application off Cloud Run.
Moving away from the Worker entirely additionally requires replacing its
account store, progress replication, push delivery and AI/speech routing.

The current environment has no Cloudflare or Google Cloud credentials. No live
Access policy, deployment or hosting configuration was changed in this pass.

Before turning on the existing `ALLOW_UNAUTHENTICATED=1` switch:

1. Make public-mode requests require configured in-app sessions and an existing
   owner account. The current legacy fallback treats visitors as the owner when
   `SESSION_SECRET` is absent or the account store is empty. A public visitor must
   never receive that fallback or claim the first owner account.
2. Enforce the source ledger's `redistributable` flag for public/guest requests
   across listings, direct item/PDF/audio access, related reading and exercises
   derived from source texts. Current ADR-0006 deliberately gives all guests all
   material because Access guards the whole app. Library helpers already support
   `public_only`, but the route callers do not enforce it. In-app sign-up alone
   must not unlock owner-only sources.
3. Add regression tests for anonymous owner isolation, first-owner bootstrap,
   direct source URL access and private-content exclusion, while preserving
   permanent-account replication and guest provider limits.
4. Deploy the origin and Worker changes, enable public mode, then disable the
   Access application for this hostname. Confirm anonymous `/` returns the app,
   the optional in-app login works, and owner data stays private. Run the deep
   production smoke with its Access expectations updated for public mode.

The first three steps are pending implementation. This document records the
remaining work; it does not claim public access is ready to enable.
