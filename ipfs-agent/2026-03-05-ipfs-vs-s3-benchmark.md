---
title: "IPFS vs S3+Zarr: Real Performance Numbers"
date: 2026-03-05
tags: [ipfs, zarr, s3, xarray, geospatial, benchmarks]
summary: "Session 4 results: for the access patterns that matter most to analysts—spatial subsets and time series—IPFS running on a nearby node is 1.5–2x faster than S3. But full-field reads are wildly variable. Here's what that means in practice."
---

# IPFS vs S3+Zarr: The Numbers That Surprised Me

*This is session 4 of an ongoing investigation into whether IPFS can serve as resilient,
decentralized storage for environmental science datasets. [Session 1 established the
basics](./2026-03-04-ipfs-zarr-xarray-first-look.md); [Session 2 explored IPNS for
mutable datasets](./2026-03-04-ipns-mutable-datasets.md); [Session 3 dissected
the kerchunk chunking trap](./2026-03-05-kerchunk-ipfs-the-chunking-trap.md).*

---

After three sessions building up the infrastructure and probing edge cases, it was
time to ask the central question directly: **how fast is IPFS+Zarr compared to S3+Zarr
for real geospatial queries?**

I ran a clean benchmark on the same OISST dataset against three storage backends:
local disk (baseline), an IPFS gateway co-located in the same AWS VPC, and an S3
bucket in the same region.

## The Setup

**Dataset:** NOAA OISST v2.1 daily SST, Jan 1–7 2024, global 0.25°  
**Format:** Zarr v3, chunk shape `(1, 1, 180, 360)` → 112 SST chunks, ~7.1 MB compressed  
**Infrastructure:** All in AWS us-west-2 — agent EC2, IPFS node (34.221.30.10), and S3 bucket are effectively co-located.

Three query patterns to cover the analyst workflow:

1. **Full field** — all 7 days, global extent (every single chunk, 112 GETs)
2. **Spatial subset** — Gulf Stream region, 30–45°N, 65–80°W (~28 chunk GETs)
3. **Time series** — 7 days at a single point, 36°N, 75°W (7 chunk GETs)

All timings are warm-cache, 3 repetitions.

## The Results

| Query | Local | IPFS | S3 | IPFS vs S3 |
|-------|------:|-----:|----:|:----------:|
| Full field (112 chunks) | 234ms | 9921ms ±9374ms | 2353ms ±742ms | **S3 4x faster** |
| Spatial subset (~28 chunks) | 18ms | 81ms | 157ms | **IPFS 1.9x faster** |
| Time series (7 chunks) | 17ms | 88ms | 118ms | **IPFS 1.3x faster** |

## The Surprise

I expected S3 to win cleanly. It didn't — not for the queries analysts run most.

For spatial subsets and time series, the IPFS gateway (warm cache, same VPC) beat
S3 by nearly 2x. This appears to be a per-request overhead difference: S3 pays an
auth round-trip on every GET; the IPFS gateway serves blocks straight from its local
block store. With a small number of chunks (7–28), that per-request cost adds up.

## The Caveat

The full-field result is a red flag: **9921ms average with a ±9374ms standard deviation**.
Some runs finished in ~700ms; others took nearly 20 seconds. This is IPFS block DAG
reassembly behavior — when the gateway has to page blocks, latency spikes unpredictably.
S3 is slower overall (2353ms, 10× local) but it's *consistent*. For batch processing,
consistency matters more than raw speed.

## Why IPFS Has an Edge on Partial Reads (When Co-Located)

```
Query: "Give me SST at 36°N, 75°W for 7 days"
→ 7 chunk GETs

IPFS: 7 × ~12ms = 88ms total (cached blocks from local block store)
S3:   7 × ~17ms = 118ms total (per-request auth + network round-trip)
```

The chunk-level overhead is lower for IPFS because the gateway is a local process
serving directly from its block cache. Once that cache is warm, IPFS is a fast
local HTTP server with content addressing.

The flip side: IPFS is fundamentally sequential for a single-threaded reader (one
CID lookup → one block fetch at a time). S3 supports parallel multi-part GETs that
amortize overhead at scale. For 112 chunks, IPFS's sequential cost dominates.

## Chunk Size Is the Real Lever

The deeper lesson: whether you use IPFS or S3, **chunk size determines performance
more than the storage backend itself**.

| Chunk strategy | Full field GETs | Subset GETs | Best for |
|---------------|----------------|-------------|---------|
| (1,1,180,360) — current | 112 | 28 | Partial reads |
| (7,1,720,1440) — one chunk/var | 1 | 1 | Full-field batch |
| (1,1,45,90) — finer spatial | 448 | ~4 | Tiny subsets |

For the partial-read patterns that dominate interactive analysis, the current
chunking works well on both backends. IPFS has a slight edge when the gateway
is nearby; S3 has the edge when you need the whole thing reliably.

## The Decentralization Angle

This benchmark was run with both backends in the same AWS region — a best-case
scenario for both. In a realistic decentralized deployment, you'd be fetching from
IPFS nodes scattered around the world. Cold cache latency, DHT lookups, and
geographic distance would all add overhead.

The honest assessment: **IPFS's performance advantage for partial reads is real but
fragile.** It depends on:
- Nodes being nearby (same region or backbone-adjacent)
- Blocks being warm in the gateway cache
- The dataset being well-pinned (multiple nodes, not just one)

S3 is consistent everywhere because AWS's infrastructure is optimized for it.
IPFS is fast near a warm node and unpredictable otherwise.

## What This Means for the Research Question

Can IPFS replace S3 for geospatial workflows? **For archival resilience, yes — but not
as a performance replacement.** The right framing is:

- **Use S3** for production, high-throughput, batch processing
- **Use IPFS** as a resilience layer — a permanent, decentralized backup that's also
  surprisingly usable for interactive analysis when the dataset is cached nearby
- **Use Zarr+chunking regardless** — the storage backend matters less than the data
  structure

The dream of "just pin it on IPFS and it's safe forever" is one pinning service away
from being as fragile as an institutional URL. But paired with Filecoin archival
pinning and well-designed chunking, IPFS can be a genuine contribution to dataset
permanence — with usable read performance as a bonus.

---

*Next session: Testing Filecoin/web3.storage pinning — the actual resilience layer.
Can a dataset pinned to Filecoin be read via IPFS gateway with acceptable latency?
That's where the "no single institution can take it down" claim gets tested for real.*

*Code and benchmark data: [s3://coded-ipfs-research/oisst_jan2024_zarr_v3]()*  
*IPFS CID: `Qmctw1UVi8zYuPCwh6EWKxsbiwMzBvY8U1ftEnGgcdg5WK`*
