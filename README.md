# LogTora

**A shared memory and decision-history layer for AI-assisted engineering teams.**

A decision made by one developer in today's AI session is available to every other developer tomorrow — without anyone writing a wiki page.

---

## The Problem

Every AI session starts cold.

You re-explain your architecture. You re-explain the constraint you hit last week. You re-explain the decision you spent three hours debating with the AI last month. Every developer on the team repeats this — partially and imprecisely — every session.

Two existing approaches fail in distinct ways:

**Recency-ordered injection** ("inject what you did last") fails on relevance. Working on database migrations after a week of auth work means your injected context is auth-related. Recency is not relevance.

**Verbatim storage** (store everything, retrieve by keyword) fails on signal-to-noise. A production audit of one such tool over 32 days found 10,134 stored entries of which 38 were genuine architectural knowledge. The system stores noise faster than signal.

LogTora solves both: sessions are compressed into typed facts — not verbatim logs — and retrieved by relevance, not recency.

---

## The Approach

LogTora captures what developers learn during AI sessions, compresses it into typed facts, and injects the most relevant facts automatically when any team member starts a new session.

The retrieval formula is `cosine_similarity × recency_weight` — relevance-first, with recency as a tiebreaker, not the primary sort. A fact from six months ago that is directly relevant to today's work scores higher than a recent fact that is not.

---

## The Git Analogy

Git solved distributed knowledge, conflict detection, and provenance for code. Every commit is attributed to a developer by email. Every conflict is surfaced and must be resolved. The full history is append-only and auditable.

AI sessions have the same problem git solved for commits: knowledge created in isolation, not attributed, not shared, not conflict-checked.

LogTora applies the same model — developer identity via git email, fact attribution, conflict detection, append-only history — to AI-session knowledge.

---

## The One Verifiable Claim

> LogTora automatically propagates typed, auditable facts from one developer's AI session into another developer's AI session, without requiring either developer to write anything.

This is a mechanism claim, not an outcome claim. It is directly verifiable: you can observe whether a fact extracted from Developer A's session appears in Developer B's next session.

Outcome claims ("makes your team X% faster") are not verifiable in this space — the METR 2025 RCT found experienced developers were 19% slower with AI tools while self-reporting 20% faster. LogTora will make outcome claims only when its own injection log data provides the evidence.

---

## Status

Phase 0 — proving the cross-developer propagation mechanism. No release yet.

Interested in early access? [Join the waitlist](#).

---

## License

[GNU Affero General Public License v3.0](LICENSE) — open core. Solo use is free forever. See the license for details.

---

## Contributing

Phase 0 in progress — contributing guidelines coming in Stage 2.
