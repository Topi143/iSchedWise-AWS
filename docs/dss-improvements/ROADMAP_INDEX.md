# DSS Improvements — Master Roadmap Index

> **Project:** iSchedWise V4 — A Web-Based Class Management and Exam Scheduling with Decision Support System  
> **Design Principle:** *"Show answers, not data"* — Zero new pages, zero new sidebar items  
> **Date:** 2025  

---

## Overview

13 improvements organized into 4 tiers, designed to strengthen the Decision Support System (DSS) aspect of iSchedWise while making the user experience **simpler**, not more complex.

Every improvement either:
- **Replaces** existing UI with a smarter version
- **Enriches** existing UI with contextual intelligence
- **Hides** behind progressive disclosure (visible only when relevant)

---

## Quick Reference Table

| # | Plan | Category | Effort | DSS Impact | New Pages? | Key Benefit |
|---|------|----------|--------|------------|------------|-------------|
| A1 | [Schedule Form Panel Simplification](A1_SCHEDULE_FORM_PANEL_SIMPLIFICATION.md) | Simplify | Low | ★★★☆☆ | No | AI panel always visible via responsive layout |
| A2 | [Dashboard Priority Tiers](A2_DASHBOARD_PRIORITY_TIERS.md) | Simplify | Low | ★★★★☆ | No | Urgent items surface first, idle items hide |
| A3 | [Smart Quick Actions](A3_SMART_QUICK_ACTIONS.md) | Simplify | Low | ★★★☆☆ | No | Context-aware action suggestions |
| A4 | [Color-Coded Schedule Badges](A4_COLOR_CODED_BADGES.md) | Simplify | Low | ★★★☆☆ | No | Red/yellow/green status at a glance |
| B1 | [Schedule Quality Index (SQI)](B1_SCHEDULE_QUALITY_INDEX.md) | DSS Power | Medium | ★★★★★ | No | Single 0-100 score for schedule health |
| B2 | [Inline What-If Feedback](B2_INLINE_WHAT_IF_FEEDBACK.md) | DSS Power | Medium | ★★★★☆ | No | Live impact preview before saving |
| B3 | [Confidence Scores](B3_CONFIDENCE_SCORES.md) | DSS Power | Low-Med | ★★★★☆ | No | "92% match" on recommendations |
| B4 | [AI Smart Prefill](B4_AI_SMART_PREFILL.md) | DSS Power | Medium | ★★★★☆ | No | Auto-suggest day/time/room based on patterns |
| B5 | [Exam Auto Conflict Check](B5_EXAM_AUTO_CONFLICT_CHECK.md) | DSS Power | Low | ★★★☆☆ | No | Parity with class form's auto-check |
| C1 | [Stat Card Sparklines](C1_STAT_CARD_SPARKLINES.md) | Visual Analytics | Low | ★★★☆☆ | No | Trend arrows + activity dots on dashboard |
| C2 | [Reports Chart Visualizations](C2_REPORTS_CHART_VISUALIZATIONS.md) | Visual Analytics | Medium | ★★★★☆ | No | Heatmap, stacked bar, trend line charts |
| C3 | [AI Insights Banner](C3_AI_INSIGHTS_BANNER.md) | Visual Analytics | Low | ★★★☆☆ | No | Instant insight banner on reports page |
| D1 | [Optimized Auto-Scheduler](D1_OPTIMIZED_AUTO_SCHEDULER.md) | Advanced | High | ★★★★★ | No | Backtracking search for better auto-schedules |
| D2 | [Conflict Chain Resolution](D2_CONFLICT_CHAIN_RESOLUTION.md) | Advanced | Med-High | ★★★★☆ | No | One-click resolve for multiple conflicts |

---

## Implementation Priority

### Tier 1 — Foundation (Start Here)

Low effort, immediate user impact. Can be implemented in 1-2 days each.

| Order | Plan | Why First |
|-------|------|-----------|
| 1 | **B5** — Exam Auto Conflict Check | Parity fix — exam form is missing what class form already has |
| 2 | **A4** — Color-Coded Badges | Pure CSS change, instant visual intelligence |
| 3 | **B3** — Confidence Scores | Expose existing scores (already computed, just hidden) |
| 4 | **A3** — Smart Quick Actions | Small JS change, contextual dashboard actions |
| 5 | **C1** — Stat Card Sparklines | Small visual enrichment, no backend changes |

### Tier 2 — Core DSS (High Impact)

Medium effort, significant DSS strengthening. 2-4 days each.

| Order | Plan | Why Second |
|-------|------|------------|
| 6 | **B1** — Schedule Quality Index | Foundation for B2, D1 (other features reference SQI) |
| 7 | **A1** — Schedule Form Panel Simplification | Layout fix that makes AI panel always visible |
| 8 | **A2** — Dashboard Priority Tiers | Transforms dashboard from data dump to actionable |
| 9 | **C3** — AI Insights Banner | Quick win once reports stats are available |

### Tier 3 — Intelligence Layer

Medium-high effort, advanced DSS capabilities. 3-5 days each.

| Order | Plan | Why Third |
|-------|------|-----------|
| 10 | **B2** — Inline What-If Feedback | Requires B1 (SQI) to show impact delta |
| 11 | **B4** — AI Smart Prefill | Requires historical schedule data patterns |
| 12 | **C2** — Reports Chart Visualizations | Enriches existing reports with visual analytics |

### Tier 4 — Advanced (Stretch)

High effort, impressive DSS capabilities. 5-7 days each.

| Order | Plan | Why Last |
|-------|------|----------|
| 13 | **D1** — Optimized Auto-Scheduler | Complex algorithm, but biggest DSS impact |
| 14 | **D2** — Conflict Chain Resolution | Builds on B3 (recommendations) and conflict detector |

---

## Effort/Impact Matrix

```
                        ★ DSS IMPACT ★
               Low         Medium        High
         ┌─────────────┬─────────────┬──────────────┐
   Low   │             │ A3, A4      │ B3, B5       │  ← Quick Wins
         │             │ C1          │              │
Effort   ├─────────────┼─────────────┼──────────────┤
 Medium  │             │ A1, A2, C3  │ B1, B2, B4   │  ← Core Work
         │             │             │ C2           │
         ├─────────────┼─────────────┼──────────────┤
  High   │             │             │ D1, D2       │  ← Stretch Goals
         └─────────────┴─────────────┴──────────────┘
```

**Recommended path**: Start top-right (Quick Wins with High Impact), move down.

---

## Dependencies

```
B1 (SQI) ──────→ B2 (What-If) uses SQI delta
                → D1 (Smart Scheduler) shows SQI comparison

B3 (Confidence) → D2 (Chain Resolution) uses confidence to rank fixes

B5 (Exam Auto) → standalone (no deps)
```

Most improvements are **independent** — only B2 strictly requires B1 first.

---

## Technology Requirements

| Technology | Status | Used By |
|-----------|--------|---------|
| Chart.js | ✅ Already in use | C1, C2 |
| Tailwind CSS | ✅ Already in use | All |
| Google Gemini 2.5 Flash | ✅ Already integrated | B4, C3 (optional) |
| Flask-SocketIO | ✅ Already in use | B2 (live feedback) |
| Native Python | ✅ No new deps | D1, D2, D3, B1 |
| OR-Tools CP-SAT | ⚠️ Optional (~15MB) | D1 (future enhancement only) |

**Zero new mandatory dependencies** for all 14 improvements.

---

## Files Impact Summary

### New Files

| File | Created By |
|------|------------|
| `app/services/schedule_quality.py` | B1 |
| `app/services/smart_scheduler.py` | D1 |
| `app/services/conflict_resolver.py` | D2 |

### Most-Modified Existing Files

| File | Modified By |
|------|-------------|
| `app/templates/dashboard.html` | A2, A3, C1 |
| `app/templates/schedule_form.html` | A1 |
| `app/templates/schedule/_class_tab.html` | A4 |
| `app/templates/schedule/_exam_tab.html` | A4 |
| `app/routes/schedule.py` | B1, B2, D1, D2 |
| `app/routes/main.py` | A2, A3, C1 |
| `app/routes/reports.py` | C2, C3 |
| `app/services/recommendation_engine.py` | B3 |
| `app/static/js/schedule/auto_conflict_check.js` | B2, D2 |
| `app/static/js/schedule/exam_ai.js` | B5 |
| `ischedwise_db.sql` | — |

---

## DSS Thesis Alignment

Each improvement maps to a Decision Support System capability:

| DSS Capability | Plans |
|----------------|-------|
| **Conflict Detection & Prevention** | B5, B2, D2 |
| **Recommendation & Optimization** | B1, B3, B4, D1 |
| **Visual Analytics & Reporting** | C1, C2, C3 |
| **Decision Confidence** | B1, B3, B2 |
| **What-If Analysis** | B2 |
| **Automated Scheduling** | D1, B4 |
| **User Experience & Accessibility** | A1, A2, A3, A4 |

---

## Document Index

| Document | Path |
|----------|------|
| This file | `docs/dss-improvements/ROADMAP_INDEX.md` |
| A1 — Schedule Form Panel | `docs/dss-improvements/A1_SCHEDULE_FORM_PANEL_SIMPLIFICATION.md` |
| A2 — Dashboard Priority Tiers | `docs/dss-improvements/A2_DASHBOARD_PRIORITY_TIERS.md` |
| A3 — Smart Quick Actions | `docs/dss-improvements/A3_SMART_QUICK_ACTIONS.md` |
| A4 — Color-Coded Badges | `docs/dss-improvements/A4_COLOR_CODED_BADGES.md` |
| B1 — Schedule Quality Index | `docs/dss-improvements/B1_SCHEDULE_QUALITY_INDEX.md` |
| B2 — Inline What-If Feedback | `docs/dss-improvements/B2_INLINE_WHAT_IF_FEEDBACK.md` |
| B3 — Confidence Scores | `docs/dss-improvements/B3_CONFIDENCE_SCORES.md` |
| B4 — AI Smart Prefill | `docs/dss-improvements/B4_AI_SMART_PREFILL.md` |
| B5 — Exam Auto Conflict Check | `docs/dss-improvements/B5_EXAM_AUTO_CONFLICT_CHECK.md` |
| C1 — Stat Card Sparklines | `docs/dss-improvements/C1_STAT_CARD_SPARKLINES.md` |
| C2 — Reports Chart Visualizations | `docs/dss-improvements/C2_REPORTS_CHART_VISUALIZATIONS.md` |
| C3 — AI Insights Banner | `docs/dss-improvements/C3_AI_INSIGHTS_BANNER.md` |
| D1 — Optimized Auto-Scheduler | `docs/dss-improvements/D1_OPTIMIZED_AUTO_SCHEDULER.md` |
| D2 — Conflict Chain Resolution | `docs/dss-improvements/D2_CONFLICT_CHAIN_RESOLUTION.md` |
