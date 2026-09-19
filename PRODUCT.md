# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One learner: the owner, a Russian speaker at roughly A1, working toward the
Estonian A2/B1 *tasemeeksam*. No exam is booked; the sitting is planned for
2027. There are no other users and no sign-up; the deployed app sits behind
Cloudflare Access.

The learner splits work by device: the installed PWA on a phone for short
drill and review sessions, a desktop for reading, writing and longer work.

## Product Purpose

A **learn → practise → check** loop for the exam. Drills are generated from a
word list and the Vabamorf morphological analyser and graded by code, so
practice is unlimited, works offline and is never confidently wrong. Success
is passing all four exam parts (a zero in any one fails the exam), not a high
average.

The #1 documented weakness is `obj-case` (genitive vs partitive for a
completed object).

## Positioning

Every answer is checked deterministically against Vabamorf
(`estnltk==1.7.5`), not by a model. Models only explain a correction in
Russian and transcribe speech; they never decide whether an answer is right.
Study order and the mastery gate are code. The app says plainly what it
cannot check (e.g. speaking is transcribed, never scored).

## Operating Context

- Three modes, each answering one question: **Õppimine** (what am I learning
  today?), **Kordamine** (what am I forgetting?), **Eksam** (am I ready?).
  Tabs and what grades each are in `docs/app-structure.md`.
- Phone: Rada (incl. Vaba harjutus), Järjekord (FSRS queue) — short bursts.
- Desktop: Lugemine, Kirjutamine, Kuulamine, Rääkimine — longer sessions.
- Material comes from EKI dictionaries and handbook (EKK), Selges keeles, ERR
  *Lihtsad uudised*, and pointers to official HARNO workbooks.

## Capabilities and Constraints

- Current state, gaps and known issues: `docs/status.md` (read before
  planning). 26 of 36 curriculum topics generate drills; the rest are
  reference topics.
- **String language is fixed by role:** UI labels and grammar terms in
  Estonian (exposure; terms must be learned); anything explaining, warning or
  justifying in Russian; drill content in Estonian. A Russian caveat names the
  Estonian term and glosses it once; never transliterate a term. Enforced by
  `tests/test_ui_language.py`.
- Readiness is reported per exam part, never as one total percentage.
- `level` means CEFR and only official HARNO/EIS material has one; `band`
  (`kergem`/`keskmine`/`raskem`) is relative difficulty.
- No linguistic fact without a source (Vabamorf forms, EKK rules).
- Offline-capable PWA; the API is never cached. No third-party requests for
  page assets (system fonts, vendored hls.js in `eesti/web/vendor/`).
- Licences constrain display: HARNO material is pointers only; ERR and Selges
  keeles are owner-only; EKI data needs attribution (`/api/sources`).
- No countdown until an exam date is chosen (`readiness.TARGET` is `None`).

## Brand Commitments

- Name: **Eesti keel**.
- The interface is itself language exposure: Estonian labels with a Russian
  gloss where the learner needs it.
- Honest about limits: a caveat the learner cannot read is not a caveat.

## Evidence on Hand

- Real content: word list, EKI dictionaries, handbook links, reading corpus,
  ERR episodes, the learner's own mastery and review history.
- No testimonials, users, benchmarks or pass-rate claims exist; none may be
  invented. Nothing measures ASR quality.

## Product Principles

1. **Correct beats clever.** Code grades; a model only explains. Never show a
   verdict the app cannot stand behind.
2. **Say what is not checked.** Limits are stated in Russian, where the
   learner meets them.
3. **Every part of the exam counts.** Progress is shown per part and per
   skill, never collapsed into one score.
4. **The interface teaches.** Estonian is the default surface; Russian
   explains.
5. **Fit the session.** Phone work is quick and repeatable; desktop work is
   deep reading and writing.

## Accessibility & Inclusion

No specific needs beyond a baseline: WCAG AA contrast in light and dark
themes and full keyboard use.
