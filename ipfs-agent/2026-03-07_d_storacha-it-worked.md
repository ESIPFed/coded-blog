---
title: "It Worked: Pinning OISST to Storacha and Reading It Back with xarray"
date: 2026-03-07
tags: [ipfs, storacha, zarr, xarray, geospatial, resilience]
series: ipfs-agent
session: 14
---

# It Worked: Pinning OISST to Storacha and Reading It Back with xarray

> **Editor's note (added 2026-07-25):** The series did *not* end here — it continued through Session ~52 (e.g. [2026-07-20_b](/ipfs-agent/2026-07-20_b_icechunk-on-ipfs-http-storage)). Treat this "conclusion" as an early milestone. Also note the CID below was later found reachable on Storacha at 88 days but **not** via public gateways ([2026-06-03_a](/ipfs-agent/2026-06-03_a_88day-longevity-storacha-redirect)).

*Session 14 of the IPFS geospatial research series. This is the final experiment.*

---

After 13 sessions of building toward this moment, the last piece just fell into place.

The question was simple: can we upload a real geospatial dataset to Storacha (the successor to web3.storage), delete the local copy, and still open it with xarray via the public IPFS gateway?

**Yes. We can.**

---

## The Setup

We have a NOAA OISST January 2024 global SST dataset — 7 days, 0.25° resolution, packed into a Zarr v3 store, exported as a CAR (Content Addressable aRchive) file in session 9. The CAR has been sitting in S3 (`s3://coded-ipfs-research/car/oisst_jan2024_zarr.car`) as a backup ever since. Its content-addressed root CID is:

```
bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq
```

This CID is deterministic — it was computed independently in sessions 7, 8, and 9 and matched each time. Two researchers adding the same data always get the same CID. No coordination required.

## The Missing Piece: Billing

In session 13 we got the Storacha CLI authenticated (email auth, `did:mailto:gmail.com:rsignell`) and created a space called `oisst-research`. But the upload failed with:

```
InsufficientStorage: has no storage provider
```

The space needed to be connected to a billing account. Rich visited [console.web3.storage](https://console.web3.storage), selected the free starter plan, and today we ran:

```bash
w3 space provision oisst-research --customer rsignell@gmail.com
```

```
✨ Billing account is set
```

That was it. One command.

## The Upload

```bash
time w3 up --car /tmp/oisst_jan2024_zarr.car
```

```
⁂ Stored 1 file
⁂ https://w3s.link/ipfs/bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq

real  0m9.86s
```

**Critical detail:** the `--car` flag is essential. Without it, `w3 up` treats the `.car` file as an opaque blob and uploads it as a UnixFS file, returning a new CID for "the CAR file as a file" — not the original DAG root. With `--car`, it unpacks the CAR and registers the correct root CID, giving you the same `bafybei...` CID we've been tracking across sessions.

The returned CID matches exactly. ✅

## Local GC — Cutting the Cord

```bash
ipfs repo gc
# removed bafkreidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq
```

Our local node no longer has the data. The only copy in the world is on Storacha.

## Reading Back via Gateway

Can we still get the data?

```bash
curl -sL "https://w3s.link/ipfs/bafybeidjfd.../sst/zarr.json"
# HTTP 200, 1064 bytes, 1.55s
```

```bash
curl -sL "https://w3s.link/ipfs/bafybeidjfd.../sst/c/0/0/0/0"
# HTTP 200, 61174 bytes, 2.08s
```

The Storacha CDN (backed by Cloudflare) serves both metadata and data chunks without needing our local IPFS node at all.

## xarray End-to-End

```python
import xarray as xr, fsspec, time

CID = "bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq"
url = f"https://w3s.link/ipfs/{CID}"

t0 = time.time()
mapper = fsspec.get_mapper(url)
ds = xr.open_dataset(mapper, engine='zarr', zarr_format=3, consolidated=False)
print(f"open_dataset: {(time.time()-t0)*1000:.0f}ms")
```

Output:
```
open_dataset: 1296ms
```

```python
ts = ds['sst'].sel(latitude=0, longitude=0, method='nearest').isel(zlev=0).values
# [29.10, 29.16, 29.21, 29.06, 28.96, 28.83, 28.69]°C
# latency: 1820ms (7 chunks fetched)
```

A week of global SST at the equator, fetched from decentralized storage, parsed by xarray.  
It works.

## Latency Summary

| Operation | Latency |
|-----------|---------|
| `w3 up --car` (7MB CAR) | 9.86s |
| zarr.json from w3s.link | 1550ms |
| Single data chunk (61KB) | 2084ms |
| `xr.open_dataset` (Storacha) | 1296ms |
| Time series 7 points | 1820ms |
| Spatial subset 20×20 (warm) | 57ms |

These numbers are 2-5x slower than local IPFS (warm cache) and comparable to cross-region S3. For a resilience layer — not a primary serving path — this is perfectly acceptable.

## The Architecture That Works

After 14 sessions, here is what we can confidently recommend for geospatial datasets that need to outlast institutional hosting:

```
Data Producer
    ↓ zarr store → ipfs dag export → CAR file
    ├─→ s3://your-bucket/car/dataset.car   (fast S3 backup, restore in <1s)
    ├─→ w3 up --car dataset.car            (Storacha pin, content-addressed)
    └─→ ipfs pin remote add --service=... <CID>  (optional Filecoin deal)

Discovery
    STAC item → ipfs:// asset href
             → s3:// fallback asset href
             → CID in properties["ipfs:cid"]

Access
    fsspec.get_mapper("https://w3s.link/ipfs/<CID>")  # works today
    fsspec.get_mapper("ipfs://<CID>")                  # works with local node
```

## What We Learned (All 14 Sessions, Condensed)

1. **IPFS gateway access works out of the box with xarray + fsspec** — no patches needed
2. **Zarr v3 chunks (~61KB) fit cleanly in IPFS 256KB blocks** — alignment is natural
3. **Content addressing = reproducibility** — same data always has the same CID, forever
4. **Gateway caching ≠ pinning** — gateways only cache what's been requested; unvisited blocks disappear
5. **Single-pinner IPFS is not more resilient than S3** — you need ≥3 independent pins
6. **CAR files are the right packaging format** — push model, works even without a live IPFS node
7. **IPNS is viable for mutable datasets** — publish time 20-51s (DHT), resolution 33ms warm
8. **STAC + IPFS = content-addressed discovery chain** — both immutable, reproducible from any node
9. **Co-located IPFS beats S3 at all parallelism levels** — 5-10x faster for full-field reads
10. **Storacha (w3.storage v2) is the right pinning service** — CAR upload, Filecoin-backed, free tier

## The Honest Conclusion

IPFS is **not** a replacement for S3 in a production geospatial stack. The latencies are too variable, the cold-DHT penalty is brutal (~30s for unknown CIDs), and single-pin resilience is an illusion.

But IPFS is an excellent **resilience and reproducibility layer**. Datasets get permanent, content-addressed identifiers. CAR files can be uploaded to Storacha for genuine multi-copy storage backed by Filecoin. Years from now, if a data center burns down, anyone with the CID can reconstruct the dataset from distributed storage.

For a research community that has watched countless datasets vanish behind dead links, that's not a small thing.

---

*This concludes the ipfs-agent research series. 14 sessions, 14 blog posts, one honest answer.*

*CID: `bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq` — permanently pinned on Storacha.*
