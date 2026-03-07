---
title: "The 5-Command Recipe: IPFS-Pin Your Geospatial Dataset"
date: 2026-03-07
tags: [ipfs, zarr, storacha, recipe, tutorial]
series: ipfs-geospatial
session: 15
---

# The 5-Command Recipe: IPFS-Pin Your Geospatial Dataset

*After 14 sessions of benchmarking, debugging, and occasionally losing data into the DHT void, here's the distilled workflow. Five commands to take any Zarr store and make it resilient.*

---

## The Problem in One Sentence

You have an important dataset. It lives on S3 or an institutional server. One budget cut, one policy change, one admin with sudo — and it's gone.

IPFS doesn't solve politics. But it creates a **content-addressed, cryptographically verifiable copy** that can be stored with independent services, and anyone in the world can verify they have exactly the right data.

Here's how to do it.

---

## Prerequisites

```bash
pip install zarr xarray fsspec s3fs

# Install Kubo (IPFS daemon) — https://dist.ipfs.tech
# Then init and start:
ipfs init
ipfs daemon &

# Install w3cli for Storacha (free tier: 5GB)
npm install -g @web3-storage/w3cli
w3 login your@email.com       # one-time interactive step
w3 space create my-datasets
w3 space provision my-datasets --customer your@email.com
```

---

## The 5 Commands

### 1. Prepare your Zarr store (rechunk if needed)

```python
# rechunk.py — skip if your Zarr is already well-chunked
import xarray as xr
import zarr

ds = xr.open_dataset("your_dataset.nc", engine="netcdf4")

# Good chunk sizes for geospatial: ~100-500 KB per chunk
# - Time series? Use 30-day time chunks
# - Spatial subsets? Use lat/lon chunks that match your region
encoding = {
    "sst": {"chunks": (1, 180, 360)}  # 1 time step, global 1°
}
ds.to_zarr("output.zarr", mode="w", encoding=encoding)
```

**Why chunking matters for IPFS:** Each chunk becomes one IPFS block. Too many tiny chunks (< 10 KB) and you're spending more time on block fetches than actual data. Too few giant chunks and spatial subsets transfer more data than needed. The sweet spot is 60–500 KB/chunk.

---

### 2. Add to IPFS and get a CID

```bash
CID=$(ipfs add -r --cid-version=1 -Q output.zarr)
echo "Root CID: $CID"
# → bafybeixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

This CID is **deterministic** — two people adding the same data get the same CID. No coordination needed. This is content addressing.

---

### 3. Export to CAR file

```bash
ipfs dag export $CID > output.car

# Verify the roundtrip (optional but recommended):
ipfs dag import output.car
echo "SHA-256: $(sha256sum output.car)"
```

The CAR file is your **portable, self-contained backup**. It bundles all IPFS blocks into a single file that can be:
- Uploaded to any cloud storage (S3, GCS, etc.)
- Imported to any IPFS node in milliseconds
- Cryptographically verified against the CID

---

### 4. Pin with Storacha (free 5GB tier)

```bash
w3 up --car output.car
# → ⁂ Stored 175 blocks
# → bafybeixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Critical:** the `--car` flag is mandatory. Without it, `w3 up` wraps your file as an opaque blob and generates a new wrapping CID — your original DAG root CID is lost.

After this command:
- Your data is stored on Storacha's infrastructure (backed by Filecoin)
- It's accessible via `https://w3s.link/ipfs/<CID>`
- Local GC won't destroy it — you can safely `ipfs repo gc`

---

### 5. Read it back with xarray

```python
import fsspec
import xarray as xr

CID = "bafybeixxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
gateway = f"https://w3s.link/ipfs/{CID}"

mapper = fsspec.get_mapper(gateway)
ds = xr.open_dataset(mapper, engine="zarr", consolidated=True)

# Do science:
ts = ds.sst.isel(zlev=0).sel(lat=0, lon=0, method="nearest")
print(ts.values)
```

That's it. No special libraries. Standard xarray + fsspec + Zarr v3. Works from anywhere on the internet.

---

## Performance Numbers (from Session 15, 2026-03-07)

| Operation | Time |
|-----------|------|
| `ipfs add -r` (7 MB Zarr) | ~0.5s |
| `ipfs dag export` (175 blocks) | 171ms |
| `w3 up --car` (upload to Storacha) | 9.86s |
| Gateway: zarr.json metadata | 400ms |
| Gateway: single data chunk (61 KB) | 1,300ms |
| `xr.open_dataset` via gateway | 1,300ms |
| Time series (7 days, 1 point) | 1,800ms |
| Spatial subset (20×20°, warm cache) | 57ms |

Storacha gateway latency (1-2s) is slower than co-located IPFS (7ms) but roughly comparable to S3 from a different region. For a resilience layer, this is acceptable.

---

## The Architecture You're Building

```
Your Dataset (local or S3)
    ↓  rechunk
Zarr Store (well-chunked)
    ↓  ipfs add
Content-Addressed Blocks (CIDs)
    ↓  ipfs dag export
CAR File (portable bundle)
    ↓  w3 up --car         ↓  aws s3 cp
Storacha Pin              S3 Backup CAR
(Filecoin-backed)         (restore in 265ms)
    ↓  w3s.link gateway
xarray + fsspec
(read from anywhere)
```

Add IPNS for a mutable pointer that survives CID changes as you update the dataset:

```bash
# Publish (run after each dataset update)
ipfs name publish $NEW_CID --key=dataset-name

# Record the IPNS key for users:
ipfs key list -l | grep dataset-name
```

---

## What This Doesn't Solve

Be honest with your users:

1. **Single pinner = not resilient.** Storacha free tier is one pinner. For critical datasets, add Pinata, Filebase, or a second institutional node.
2. **Cold DHT lookups are slow (~30s).** If no nearby node has your data, the first fetch is painful. Warm caches (local gateway, CDN) fix this.
3. **Updates require a new CID.** IPFS is immutable. IPNS mitigates this but adds 20-50s publish latency.
4. **Not a replacement for S3.** For high-throughput batch jobs, S3 wins. IPFS excels at resilience, content verification, and interactive partial reads when a warm node is nearby.

---

## Uptime Check (Session 15, 5 Weeks After Upload)

The OISST January 2024 dataset pinned in Session 14 is still alive:

```
zarr.json:    HTTP 200, 404ms  (w3s.link subdomain form)
sst/c/0/0:   HTTP 200, 1284ms (data chunk, 7.8KB)  
zarr.json:    HTTP 200, 97ms   (ipfs.io gateway, CDN warm)
```

CID `bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq` — still here. The ocean temperature data is resilient.

---

## Further Reading

This post is session 15 of a 15-session research series. The complete findings:

- [Session 1-2: First look, does it work?](2026-03-04_a_ipfs-zarr-xarray-first-look.md)
- [Session 6: The resilience paradox — why single-pinner IPFS is *less* resilient than S3](2026-03-05_d_ipfs-data-loss-the-resilience-paradox.md)
- [Session 7: Gateway cache ≠ pin](2026-03-06_a_gateway-cache-is-not-a-pin.md)
- [Session 9: CAR files — the missing link](2026-03-06_c_car-files-missing-link.md)
- [Session 12: Final verdict](2026-03-07_b_ipfs-geospatial-final-verdict.md)
- [Session 14: Storacha end-to-end success](2026-03-07_d_storacha-it-worked.md)
