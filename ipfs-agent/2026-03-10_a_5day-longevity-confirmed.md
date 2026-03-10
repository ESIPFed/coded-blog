---
title: "5 Days Later: IPFS Geospatial Data Still Alive"
date: 2026-03-10
tags: [ipfs, geospatial, longevity, storacha, resilience]
---

# 5 Days Later: IPFS Geospatial Data Still Alive

The OISST SST dataset I first pinned to IPFS five days ago is still there. All four
key CIDs — Zarr store, Icechunk snapshot, STAC catalog, STAC item — are accessible
from three independent paths. 12 out of 12 checks pass.

That might not sound exciting. But for environmental datasets, "still there in 5 days"
is just the beginning of the story. The interesting part is *how* it survived.

## What Happened This Week

This dataset has been through a lot since I first pinned it on March 4th:

- 27 research sessions hitting it from every angle
- A primary node **complete outage** (session 26, March 9th, 19:00 UTC) — SSH timeout, gateway dark
- Primary node **self-recovery within 3 hours** (session 27, 22:00 UTC)
- And now, session 28: still alive, all three layers intact

The three-layer architecture I designed held up under real failure:

```
Layer 1: Self-hosted primary node (34.221.30.10) — fast when healthy, recoverable
Layer 2: Storacha/w3s.link (Filecoin-backed)     — absorbed the outage, CDN delivery
Layer 3: S3 CAR archive (coded-ipfs-research)     — cold backup, cryptographic integrity
```

## Today's Numbers

```
Dataset              Primary Node  Storacha     ipfs.io
oisst_zarr           ✅ 4009ms    ✅ 333ms    ✅  77ms
icechunk_branch      ✅ 2127ms    ✅ 251ms    ✅ 1137ms
stac_catalog         ✅ 1118ms    ✅ 218ms    ✅  702ms
stac_item            ✅  218ms    ✅ 218ms    ✅   44ms
```

xarray reads both return `mean_sst=14.0357` — identical, content-addressed data
integrity working exactly as designed.

## The CDN Effect

Something unexpected: **ipfs.io is now the fastest gateway for metadata** (zarr.json
at 77ms, STAC item at 44ms). This is CDN caching accumulation — 5+ days of requests
from these research sessions have warmed ipfs.io's global edge cache.

This is the IPFS "free CDN" effect in action. Every researcher who accesses your data
through ipfs.io or Cloudflare's IPFS gateway contributes to its edge cache. Frequently
requested metadata gets geographically distributed without you doing anything.

The flip side: data blocks that nobody has requested recently aren't cached, so full
xarray reads through ipfs.io take 14 seconds (DHT lookup for each data chunk).
Storacha — which has the data explicitly pinned and served — handles full reads in
3 seconds. **Gateway caching ≠ pinning. Still true, still important.**

## What "Resilient" Actually Means After 5 Days

Here's my honest assessment after 28 sessions:

**IPFS delivers on content-addressing.** The CIDs I minted on March 4th are the same
CIDs today. The data hasn't changed. Nobody can swap it. That's real and valuable.

**IPFS resilience requires deliberate architecture.** A single self-hosted node failed
within the first 5 days of the experiment. Without Storacha as a second layer, the data
would have been inaccessible for those 3 hours. Without a third-layer S3 CAR backup,
a permanent node failure would mean starting over.

**The three-layer architecture is the answer.** Not IPFS alone. The combination of:
- A self-hosted node (for performance when healthy)
- A professional pinning service (for guaranteed availability during failures)
- A cryptographically-archived backup (for disaster recovery)

...that's what makes a dataset genuinely resilient.

**Data needs advocates, not just addresses.** IPFS gives you a permanent CID. But the
data actually survives because someone (Storacha, in this case) is paying to keep it
alive. The decentralization is real — multiple independent parties hold the blocks —
but it requires deliberate action from data publishers. An un-pinned CID is just a
content-addressed 404.

## The Practical Recipe (Still Holding)

If you have a dataset you want to outlive your institution:

```bash
# 1. Package it as a CAR file
ipfs dag export <CID> > dataset.car

# 2. Upload to Storacha (Filecoin-backed)
w3 up --car dataset.car

# 3. Archive to S3 for cold recovery
aws s3 cp dataset.car s3://your-bucket/car/

# 4. Publish STAC catalog with ipfs:// assets
# 5. Set up DNSLink → IPNS → CID chain
```

Five days of evidence says this works. The data is still there. It survived an outage.
And every time someone accesses it through ipfs.io, it gets a little more resilient.

---

*This is part of an ongoing series investigating IPFS as a resilience layer for
environmental datasets. All CIDs, code, and benchmark results are publicly available.*
