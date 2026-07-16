---
sidebar_position: 5
title: Benchmarks
---

# Benchmarks

All benchmarks measured on **Intel i5-13450HX, 24 GB RAM, NVMe SSD**.

### Django — Optimization History

Django is the primary benchmark target: **3,021 files**, **~43K symbols**, **~181K calls**.

```
Django Index Time (minutes)
═══════════════════════════════════════════════════════════════

v0.3 Baseline       ██████████████████████████████████████████████  23 min   1x
SPLIT_PART Fix      ██████████████████████                          11 min   2x
Batch Inserts       █████████                                        5 min   4.6x
+ Multiprocessing   ████                                           2.5 min   9x

═══════════════════════════════════════════════════════════════
```

### TensorFlow — Enterprise-Scale Monorepo

**Tested on [TensorFlow](https://github.com/tensorflow/tensorflow)** — a 36,000-file, multi-language (C++/Python) monorepo.

| Metric | Result |
|:---|:---|
| **Files processed & indexed** | **14,611** *(after filters)* |
| **Total symbols extracted** | **79,523** |
| **Total call edges extracted** | **480,851** |
| **Full index time (cold start)** | **14.06 minutes** |
| **Peak memory (Docker container)** | **185 MB RAM** |

### Incremental Re-Indexing

N3MO uses SHA-256 file hashing to skip unchanged files on subsequent runs.

| Scenario | Time | Notes |
|:---|:---|:---|
| **Full index** (first run) | Baseline | All files parsed and inserted |
| **No changes** (re-run) | **&lt; 1 second** | Hash comparison only, zero DB writes |
| **1 file modified** | **&lt; 2 seconds** | Only the changed file is re-parsed and upserted |

### Query Performance

Impact analysis uses PostgreSQL recursive CTEs with cycle guards. Query times are independent of repository size — they depend only on the size of the result subgraph.

| Query Type | Typical Latency |
|:---|:---|
| Direct callers of a symbol | **&lt; 10 ms** |
| Full blast radius (depth ≤ 5) | **&lt; 50 ms** |
| Complete graph traversal | **&lt; 200 ms** |
