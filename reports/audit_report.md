# YouTube Growth Autopilot — Initial Audit & Growth Baseline Report

**Channel:** Eutuber (@nikhil007702)  
**Date:** 23 October 2026  
**Auditor:** Antigravity AI Growth Strategist  
**Target Deadline:** 31 December 2026 (70 calendar days remaining)  
**Primary Goal:** 5,000 genuine subscribers  
**Secondary Goal:** Meaningful progress toward eligible YPP watch hours (4,000 hours / 10M Shorts views)  

---

## 1. Executive Summary & Growth Gap Analysis

| Metric | Current Baseline | Goal (31 Dec 2026) | Gap to Close | Required Daily Run Rate |
| :--- | :--- | :--- | :--- | :--- |
| **Subscribers** | **14** | 5,000 | **4,986** | **~71.2 net subs/day** (498.6/week) |
| **Total Channel Views** | **11,903** | 2,500,000+ | 2,488,097 | ~35,544 views/day |
| **Public Watch Time** | **17.45 hours** (1,047 mins) | 4,000 hours | **3,982.5 hours** | ~56.9 hours/day |
| **Published Videos** | **78 total** | 350+ (capacity) | 272 | ~4-5 uploads/day |

> [!IMPORTANT]
> **Growth Gap Reality Check**:  
> To scale from 14 subscribers to 5,000 subscribers in 70 days, the channel must transition from linear output to algorithmic compound distribution. Relying solely on volume (5 Shorts/day) at current conversion rates (1 sub per ~1,200 views) would yield only ~20-30 subscribers. Growth will require:
> 1. Capitalizing on proven breakout formats (Immediate Interactive Visual Tests & Border Glitches).
> 2. Improving subscriber conversion hooks at the end of high-retention Shorts.
> 3. Linking high-traffic Shorts to 7-minute long-form deep dives to build eligible public watch time.

---

## 2. Channel Analytics & Audience Profile

### A. Traffic Distribution
* **Shorts Feed:** **92.3%** of all traffic (10,682 views).
* **YouTube Search:** **6.2%** (716 views).
* **Browse Features / Channel / Other:** **1.5%** (~180 views).

### B. Geographic Demographics
* **India (IN):** **47.3%** of total views (5,472 views) and **49.5%** of watch time (518 minutes).
* **Philippines (PH):** **4.4%** (513 views).
* **United States (US):** **3.2%** (374 views).
* **United Kingdom (GB):** **3.0%** (352 views).
* **Germany (DE):** **1.5%** (179 views).

---

## 3. Content Performance Audit: What Works vs. What Flopped

### Category Breakdown (from `reports/shorts_tracker.csv`)

| Category | Videos Tracked | Total Views | Avg Views/Video | Avg Percentage Viewed (AVP) |
| :--- | :--- | :--- | :--- | :--- |
| **Geography** | 30 | **6,386** | **212.9** | **75.2%** (Top Performing) |
| **Space** | 15 | **3,204** | **213.6** | **61.6%** |
| **Technology** | 16 | **2,078** | **129.9** | **55.4%** (High Variance) |
| **Diwali / Event** | 2 | **130** | 65.0 | 53.6% |

### Top 5 Breakout Performers
1. **[Geography]** *Your Front Door Picks Your Country* — **1,276 views**, 17 likes, **63.6% AVP**.
2. **[Technology]** *Your Phone Camera Can See Light You Can't* — **1,216 views**, 13 likes, **1 sub**, 52.5% AVP.
3. **[Geography]** *A Red Light That Stops for Jets* — **1,124 views**, 6 likes, 49.1% AVP.
4. **[Geography]** *Earth's 0,0 Point Is Not Supposed to Exist* — **1,091 views**, 16 likes, 53.6% AVP.
5. **[Space]** *Your Candle Flame Turns Into a Ball* — **1,042 views**, 5 likes, 46.4% AVP.

### Key Content Insights
* **The "Can I See It in 3 Seconds?" Rule:** Videos with immediate physical or visual proof on screen (*flame turning into a sphere*, *jet landing on an avenue*, *TV remote beam on phone camera*) break 1,000+ views.
* **The Invisible Flop:** Abstract or sensor-only topics (*phone barometer*, *bland food in space*, *phone seismometer*) received **0 to 10 views**. Viewers swipe away before the concept is explained.
* **The India Relevance Advantage:** Border enclaves, regional curiosities, and IST time-zone quirks resonate strongly with the 47% Indian audience.

---

## 4. Repository & Automation Workflow Inventory

*(Full details documented in [script_inventory.json](file:///c:/Users/Neha/Documents/AI/YoutubeShortsInc/reports/script_inventory.json))*

* **`pipeline/shorts.py`**: Central engine governing script retrieval, voice narration (Edge-TTS / Piper), Remotion staging, YouTube Data API upload, and nightly analytics tracking.
* **`pipeline/bank.py`**: Offline script pre-writer that populates `script_bank/` for up to 60 days of unattended automation.
* **`pipeline/dashboard.py`**: Local HTML dashboard compiler ([Video-Dashboard.html](file:///c:/Users/Neha/Documents/AI/YoutubeShortsInc/Video-Dashboard.html)).
* **`pipeline/audit_channel.py`**: Automated security and compliance verification suite.
* **`OpenMontage/`**: Submodule containing Remotion video compositions and stock media adapters (Wikimedia, Pixabay, Pexels, NASA).

---

## 5. Three Proposed Reversible Improvements

### Improvement 1: Dynamic Category Weighting (Config-Only)
* **Hypothesis:** Rebalancing the daily upload ratio from `[geography: 2, space: 2, technology: 1]` to `[geography: 3, space: 1, technology: 1]` will increase average views per video by ~25% because Geography has a 75.2% average retention rate.
* **Implementation:** Update `pipeline/category_weights.json` and `pipeline/config.yaml`.
* **Rollback:** Revert JSON weights to 1:1:1.

### Improvement 2: Interactive "Try This Right Now" End Card Conversion Hook
* **Hypothesis:** Adding a specific, actionable call-to-action in the last 2 seconds (*"Subscribe for tomorrow's geography glitch"*) instead of generic *"Follow for more facts"* will increase subscriber conversion from 0.08% to 0.35% per view.
* **Implementation:** Adjust `growth.end_card` in `pipeline/config.yaml`.
* **Rollback:** One-line string revert in config.

### Improvement 3: Long-Form Video Related-Shorts Linking
* **Hypothesis:** Using the YouTube Data API to link the day's top Geography Short directly to the 7-minute long-form video via `relatedVideoId` will drive traffic from the Shorts feed into long-form watch hours.
* **Implementation:** Add optional `related_video_id` metadata during Short upload.
* **Rollback:** Disable the flag in `config.yaml`.

---

## 6. Seven-Day Implementation Plan

* **Day 1 (Today):** Finalize audit, verify baselines, and test analytics logging.
* **Day 2:** Apply Category Weight optimization (`category_weights.json`) favoring Geography and Visual Space experiments.
* **Day 3:** Optimize Call-to-Action end cards and test the new conversion hooks.
* **Day 4:** Link the 7-minute long-form borders video to the day's top performing Short.
* **Day 5:** Review 48-hour analytics cohort on the newly formatted videos.
* **Day 6:** Audit weekly subscriber acquisition and adjust title/hook scoring models.
* **Day 7:** Deliver First Weekly Growth Report comparing pre- and post-optimization cohorts.

---

## 7. Verification & Run Commands

```powershell
# 1. Run local channel safety and metadata audit
OpenMontage\.venv\Scripts\python.exe pipeline\audit_channel.py

# 2. View local analytics dashboard
Start-Process "Video-Dashboard.html"

# 3. Test script bank queue status
OpenMontage\.venv\Scripts\python.exe pipeline\shorts.py list
```
