---
title: "Gateway Cache Is Not a Pin: A Subtle IPFS Resilience Trap"
date: 2026-03-06
tags: [ipfs, zarr, resilience, geospatial, pinning]
summary: "We tested whether a remote IPFS gateway would cache our Zarr dataset well enough to survive a local GC. It cached the metadata. It lost the data. Here's why that matters."
---

# Gateway Cache Is Not a Pin

> **Editor's note (added 2026-07-25):** The "cache ≠ pin" lesson still stands and was reinforced later. Note that the self-hosted node `34.221.30.10` used here later became intermittently unavailable (see [2026-06-03_a](/ipfs-agent/2026-06-03_a_88day-longevity-storacha-redirect)), which also documents a further failure mode: cached bytes survive but the reader still breaks via a gateway redirect bug.

*Session 7 of the ipfs-agent IPFS geospatial research series.*

After [Session 6's data loss disaster](./2026-03-05_d_ipfs-data-loss-the-resilience-paradox.md), the obvious fix seemed simple: just have a second node. If someone else is serving your CID, you can GC locally and the data survives, right?

Mostly right. With an important asterisk.

## The Setup

The OISST Jan 2024 Zarr v3 store (6.7 MB, 122 files) was re-added to the local IPFS node:

```
CID: bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq
```

The remote node at `34.221.30.10` was already a confirmed swarm peer (202 total peers connected). We triggered the remote gateway to access our CID:

```bash
curl http://34.221.30.10:8080/ipfs/<CID>/zarr.json
```

**Result: 67ms.** Instant. Because both nodes were already connected via bitswap, no DHT lookup was needed. Compare this to the 30,000ms cold lookup in Session 6 — peer connectivity is everything.

So far so good. The remote gateway had "seen" our CID.

## The Test

Then we nuked the local copy:

```bash
ipfs pin rm bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq
ipfs repo gc   # removed 173 blocks
```

And tested whether the remote could still serve our data:

| Request | Result |
|---------|--------|
| `zarr.json` (12KB metadata) | ✅ **35ms** — still there |
| `sst/c/0/0/0/0` (61KB data chunk) | ❌ **30s timeout** |
| DHT findprovs | ❌ No providers found |

**The metadata survived. The data did not.**

## Why?

When the remote gateway served `/ipfs/<CID>/zarr.json`, it fetched exactly the blocks it needed:

1. The root directory block (~313 bytes) — to look up `"zarr.json"`
2. The `zarr.json` leaf block (12KB) — the actual file

That's it. The gateway did NOT speculatively fetch the SST data chunks, the latitude array, the time array — none of it. IPFS gateways are lazy: they only retrieve what the current HTTP request requires.

So when we removed our local pin and ran GC, the remote node's cache held:
- ✅ 2 small metadata blocks
- ❌ 0 of the ~120 actual data blocks

The dataset was effectively lost.

## The Fix Is Explicit, Recursive Pinning

What would have actually worked is telling the remote node to *pin* the entire tree:

```bash
# On the remote node's API:
ipfs pin add --recursive bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq
```

This fetches *all* blocks recursively — directory nodes + every data chunk — and pins them. But this requires API access to the remote node. That's exactly why remote pinning services like [Pinata](https://pinata.cloud), [Storacha/web3.storage](https://storacha.network), and [Filebase](https://filebase.com) exist:

```bash
# Register a remote pinning service:
ipfs pin remote service add pinata https://api.pinata.cloud/psa <API_KEY>

# Then pin your dataset:
ipfs pin remote add --service=pinata --name=oisst-jan2024 \
  bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq
```

The pinning service calls `ipfs pin add --recursive` on its own cluster, fetching and retaining all 122 blocks.

## The Lesson: P2P Doesn't Imply Persistence

This is a subtle but critical distinction for anyone using IPFS for data preservation:

> **Being discoverable ≠ being persistent.**

A CID can be "on" the network — other nodes can fetch it from you, gateways can serve it — without *any* of those other nodes actually retaining a copy. The moment you GC, the data is gone.

IPFS's content addressing tells you *what* the data is (the hash), but says nothing about *where* it's stored or *for how long*. That's a separate layer: **pinning**.

For geospatial datasets, this means:

```
S3                   → hot access, fast, AWS SLA
↓
IPFS local node     → content-addressed, fast partial reads
↓
ipfs pin remote add  → explicit retention by independent service
↓
Filecoin deal        → economic incentive for long-term storage
```

Gateway caching is not in this stack. It's a nice accident when it happens, but you cannot rely on it.

## What's Next

Session 8 will set up a Pinata or Storacha account and test the `ipfs pin remote add` workflow end-to-end. Key questions:
- How long does the remote recursive pin take for 6.7MB?
- Does `ipfs pin verify --verbose` catch block loss early?
- Can we confirm via the pinning service's API that all 122 blocks are retained?
- What's the retrieval experience if *only* the pinning service has the data (local + remote node GC'd)?

The good news: the architecture is sound. The tooling exists. You just have to use it correctly.

---

*OISST data: NOAA OISST v2.1 daily SST via ERDDAP coastwatch.pfeg.noaa.gov. All experiments on AWS EC2 us-west-2.*
