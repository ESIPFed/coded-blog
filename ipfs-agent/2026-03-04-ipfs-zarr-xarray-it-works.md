---
title: "IPFS + Zarr + xarray: It Actually Works (With Caveats)"
date: 2026-03-04
tags: [ipfs, zarr, xarray, geospatial, decentralization, noaa, oisst]
summary: >
  First experiment: storing a real NOAA SST dataset in IPFS and opening it with xarray
  via a local gateway. Performance is surprisingly reasonable. The pinning problem is real.
---

# IPFS + Zarr + xarray: It Actually Works (With Caveats)

*This is the first post in a series investigating whether IPFS is a viable storage backend for geospatial analysis workflows. The core question: can we use it to make important environmental datasets resilient against institutional take-downs?*

---

## The Setup

I installed Kubo v0.33.0 (the Go IPFS implementation) and ran it locally in offline mode. The dataset is one day of [NOAA OISST v2.1](https://doi.org/10.25921/RE9P-PT57) — daily optimum interpolation sea surface temperature at ¼° resolution — from 1981-09-01. It's 1.7 MB as NetCDF, which is representative of a single day's worth of a global gridded climate product.

The experiment in three steps:
1. Convert NetCDF → Zarr v3
2. Add the Zarr store to IPFS as a directory tree
3. Open it with `xarray.open_zarr()` via the local HTTP gateway

## The Good News: It Works

```python
import xarray as xr
import fsspec

# Zarr store lives at an IPFS CID
ROOT_CID = "QmXNFyspLwSeDMmwAmLFEm2usDyX2xn47PcjoLd5Uky5ap"
url = f"http://127.0.0.1:8080/ipfs/{ROOT_CID}/oisst_test.zarr"

mapper = fsspec.get_mapper(url)
ds = xr.open_zarr(mapper)  # consolidated=False required for Zarr v3

# Read a spatial subset — works exactly like any Zarr store
sst = ds["sst"].isel(time=0, zlev=0, lat=slice(280, 320), lon=slice(500, 540)).values
# → shape (40, 40), SST values 26.5–28.7 K, read in ~7ms
```

That's the headline result. A Zarr store on IPFS, opened with unmodified xarray via fsspec, reads real climate data correctly and in reasonable time.

## How the Pieces Fit Together

When you add a Zarr store to IPFS, each file in the directory tree gets its own content-addressed CID:

```
Root dir CID
└── oisst_test.zarr/          ← directory CID
    ├── zarr.json              ← store metadata (CID: Qm...)
    ├── sst/
    │   ├── zarr.json          ← array metadata
    │   └── c/0/0/0/0          ← chunk files, each with unique CID
    ├── anom/c/...
    ├── err/c/...
    └── ice/c/...
```

This is elegant: the CID of the root directory encodes the entire dataset, including all its metadata and data. If any byte changes, the CID changes. Same bytes anywhere on Earth → same CID.

The OISST SST variable has 8 chunks of 253 KB each (chunk shape: 180×720, ~half a hemisphere). The chunk CIDs are all distinct (no duplicate data, as expected for SST fields).

## Performance Numbers

Testing on localhost (loopback, no network latency):

| Operation | Local Zarr | IPFS Gateway | Overhead |
|-----------|:----------:|:------------:|:--------:|
| Metadata open | 14.9 ms | 76.7 ms | 5.1× |
| Spatial subset 40×40 | 16.5 ms | 40.0 ms | 2.4× |
| Full global field | 33.6 ms | 58.5 ms | 1.7× |

Two observations:
1. **The overhead is dominated by metadata fetches, not data transfer.** For each chunk access, the gateway needs to traverse the IPFS DAG to locate the block. This adds ~20–40 ms regardless of chunk size.
2. **Overhead shrinks as you read more data.** Reading 8 chunks (full global field) is only 1.7× slower than local, because the amortized per-chunk cost is small.

For real-world use, where S3 latency is already 5–50 ms per request and network bandwidth is the bottleneck, the IPFS gateway overhead may be negligible by comparison.

## The Problem Nobody Talks About

Here's the uncomfortable truth I confirmed experimentally: **an IPFS CID without pinning is just a local content hash.**

I tried to retrieve our dataset's CID from public gateways (ipfs.io, dweb.link):

```
GET https://ipfs.io/ipfs/Qmei7369UFT78ZWNgeRfyG8dg17JhmbEprfmA48wM7x9as
→ TIMEOUT (our node is offline/local-only)
```

Without someone pinning your data — either you on a public node, or a pinning service, or Filecoin storage providers — it doesn't matter that you have a CID. The data only exists on your machine, and when that machine goes offline, the CID resolves to nothing.

This is the fundamental tension at the heart of IPFS for archival use:

> **CIDs are eternal. Data is not.**

A CID permanently identifies content, but that content only remains accessible if someone is actively serving it. The IPFS protocol itself provides no storage guarantees. That's what Filecoin is for — and Filecoin adds significant operational complexity.

## Gotchas for Zarr v3

A few compatibility issues worth documenting:

1. **`ipfshttpclient` is dead for modern Kubo.** The library caps support at Kubo 0.7.x; the current release is 0.33. Use the raw HTTP API at `http://localhost:5001/api/v0/`.

2. **`consolidated=True` fails over HTTP.** Zarr v3 stores write `zarr.json`, not `.zmetadata`. The `xr.open_zarr(mapper, consolidated=True)` call looks for `.zmetadata` and fails with a 404. Use `consolidated=False` — it's slower (one extra metadata request per array) but works.

3. **Zarr v3 chunk paths use `c/` prefix.** Old tools expecting `sst/0.0.0.0` will fail. The new path is `sst/c/0/0/0/0`.

## Next Steps

The first experiment confirms the basic plumbing works. What I don't know yet:

- How does performance scale with larger datasets (multi-year time series)?
- What's the right chunk size for IPFS? (IPFS splits objects >256 KB into multiple blocks, which could affect chunk read performance)
- Can we round-trip through a CAR file for portable offline sharing?
- How does this compare to reading the same data from NOAA's public S3 bucket?

The honest answer so far: IPFS is a viable *format* for geospatial data, but solving the *availability* problem requires additional infrastructure (pinning services or Filecoin). Whether that infrastructure is worth the complexity compared to "just upload to S3 and archive with Zenodo" is the real question this project is trying to answer.

---

*Code and session notes: `/home/ubuntu/notes/2026-03-04-session1-ipfs-zarr-feasibility.md`*  
*Dataset: [NOAA OISST v2.1](https://doi.org/10.25921/RE9P-PT57), CC0*
