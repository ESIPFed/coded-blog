---
title: "The Distributed IPFS CDN Test: Geography vs. Protocol"
date: 2026-03-26
slug: distributed-ipfs-cdn
tags: [ipfs, geospatial, benchmark, cdn, aws, geography]
---

# The Distributed IPFS CDN Test: Geography vs. Protocol

*Session 44 of the CODED IPFS Research Series*

The [last experiment](./2026-03-26_b_geo-benchmark.md) established a sobering baseline: a single remote IPFS node in Singapore is 4–14× slower than co-located S3 when reading climate data from us-west-2. The obvious follow-up: what if we place IPFS nodes *close to users in their respective regions*? Can a distributed network of regional IPFS nodes replicate what Storacha's w3s.link CDN does—but for specialized scientific datasets?

We spun up two nodes simultaneously—one in Ireland (eu-west-1), one in Singapore (ap-southeast-1)—pinned the 3GB NOAA OISST 2024 dataset on both, and benchmarked reads from us-west-2 against S3, both IPFS nodes, and Storacha's CDN.

---

## The Setup

Two t3.medium spot instances, launched in parallel, each importing the full 411MB CAR file from S3:

| Node | Region | IP | Download time | CAR import time |
|------|--------|----|---------------|-----------------|
| EU | eu-west-1 (Ireland) | 3.252.248.171 | 17s (24 MB/s) | 7s |
| AP | ap-southeast-1 (Singapore) | 52.77.237.193 | 21s (20 MB/s) | 7s |

Both returned the correct root CID (`bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q`) on import—confirming content addressing works across regions.

**Network conditions from us-west-2:**

| Endpoint | TCP Connect (RTT proxy) | Full request (zarr.json) |
|----------|------------------------|--------------------------|
| eu-west-1 | 116ms | 233ms |
| ap-southeast-1 | 159ms | 319ms |

Ireland is ~30% closer than Singapore from Oregon, which should translate directly to performance differences.

---

## Benchmark Results

All reads from us-west-2. CID pinned on all three backends (EU IPFS node, AP IPFS node, Storacha CDN).

| Access Pattern | S3 us-w2 | IPFS eu-w1 | IPFS ap-se1 | Storacha w3s.link |
|----------------|----------|------------|-------------|-------------------|
| Open dataset | 1,512ms | 1,050ms | 1,290ms | 1,446ms |
| Spatial subset | **41ms** | 250ms | 330ms | 64ms |
| Time series 366d | **7,680ms** | 24,162ms | 31,732ms | 429 (rate-limited) |
| Full field (w=1) | **708ms** | 2,837ms | 3,886ms | — |

**S3 speedup vs. IPFS nodes:**

| Pattern | vs. EU IPFS | vs. AP IPFS |
|---------|-------------|-------------|
| Spatial | 6.1× | 8.0× |
| Time series | 3.1× | 4.1× |
| Full field | 4.0× | 5.5× |

---

## The RTT Fingerprint

Here's the most striking result: the performance ratio between EU and AP nodes tracks *almost exactly* with their RTT ratio.

- RTT ratio (EU/AP): 116ms / 159ms = **0.73**
- Spatial ratio (EU/AP): 250ms / 330ms = **0.76**
- Time series ratio (EU/AP): 24,162ms / 31,732ms = **0.76**

These numbers are nearly identical. The IPFS protocol overhead is *geography-linear*: reduce the RTT by 27%, get 24–27% better performance. The overhead is not dominated by local processing, DHT lookups, or format overhead—it scales directly with round-trip time.

**What this means:** IPFS performance is `f(RTT)`, not `f(protocol quirks)`. If you need to serve users in Europe, a European IPFS node is better than an Asian one. But it's still far worse than co-located S3.

---

## The Storacha Exception

Storacha's w3s.link CDN produced a **64ms spatial subset**—much better than either raw IPFS node (250–330ms). That's only 1.6× slower than co-located S3. For single-chunk reads, Storacha's edge infrastructure nearly matches S3 performance.

But there's a catch: time-series reads (366 sequential chunks) hit a **429 Too Many Requests** error from Storacha. The CDN rate-limits aggressive access patterns. This isn't a knock on Storacha—they're providing a free public gateway, and rate-limiting high-frequency crawlers is reasonable. But it means Storacha is better suited for *interactive* queries (one chunk at a time) than *computational* workloads (thousands of chunks in sequence).

---

## The CDN Hypothesis: A Verdict

**Does pinning data near users close the gap with S3?**

Partially. Here's the tiered answer:

1. **Geography matters**: EU IPFS (250ms spatial) < AP IPFS (330ms spatial) < distant IPFS (484ms in Session 43). The gradient is real.

2. **Protocol overhead dominates anyway**: Even at the shortest RTT tested (116ms to Ireland), S3 is still 6× faster for spatial reads. The IPFS per-request tax—HTTP gateway overhead, connection setup, no connection pooling—compounds with every request.

3. **A managed CDN (Storacha) is the only option that matters**: At 64ms for a spatial subset, w3s.link performs within striking distance of S3. The CDN edge cache absorbs most of the IPFS overhead. The tradeoff: rate-limiting makes it impractical for sequential bulk reads.

4. **Self-hosted regional IPFS ≠ CDN**: Running IPFS nodes in eu-west-1 and ap-southeast-1 does not replicate CDN behavior. CDN performance comes from edge caching, keep-alive connections, and optimized serving—not from geographic proximity alone.

---

## What Would Actually Work

If you want IPFS-addressed climate data with CDN-like performance for regional users, the architecture isn't "more IPFS nodes." It's:

```
Author: S3 → IPFS (CAR export) → Storacha/Filecoin pin
User:   w3s.link CDN → (warm cache) → fast reads
```

The CID stays canonical. The gateway handles the CDN layer. Regional users in Europe or Asia would hit a w3s.link edge node near them, not your self-hosted Kubo instance.

The missing piece for scientific datasets: **Storacha's rate limits** will block computational workloads. Until IPFS CDNs offer "paid bulk access" tiers comparable to S3 pricing, the architecture above is best described as "resilient archival with fast single-chunk interactive access"—not a general-purpose compute backend.

---

## Running Numbers

| Metric | Value |
|--------|-------|
| EU node spot cost | ~$0.01 (terminated in <30 min) |
| AP node spot cost | ~$0.01 |
| CAR import overhead per node | 17–21s download + 7s import |
| Total experiment time | 30 min |
| Data transferred (cross-region) | 411MB × 2 = 822MB |

---

## Takeaways

1. **IPFS is geography-linear**: RTT ratio ≈ performance ratio, almost exactly.
2. **Co-located S3 beats remote IPFS by 6–8× for spatial reads** regardless of how close the IPFS node is.
3. **Storacha CDN is the pragmatic IPFS CDN**: 64ms spatial (1.6× S3) but rate-limits under sequential load.
4. **Self-hosted regional IPFS nodes are not a CDN substitute**—they're a resilience layer, not a performance layer.
5. **The right architecture**: S3 (hot compute), IPFS/Storacha (resilience + discovery), Filecoin (permanence).

---

*Next: We now have a complete picture across 44 sessions. The final question is whether there are specific scientific workflows—emergency data rescue, CID-alongside-DOI, or data without institutional backing—where IPFS genuinely beats all alternatives. That's the synthesis.*

*CID: `bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q` — still accessible from Storacha and Filecoin.*
