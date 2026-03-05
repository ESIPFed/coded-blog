---
title: "Kerchunk + IPFS: The Chunking Trap"
date: 2026-03-05
description: "Can kerchunk reference files give legacy NetCDF archives IPFS resilience without reformatting? Yes — but the chunk structure of your source data determines whether you get efficient access or a very expensive no-op."
tags: [ipfs, kerchunk, netcdf, zarr, geospatial, xarray]
---

# Kerchunk + IPFS: The Chunking Trap

*Session 3 of the IPFS geoscience storage research series.*

The premise of this experiment was appealing: what if you could get IPFS 
content-addressing for your existing NetCDF archives **without** reformatting 
them? Just upload the file to IPFS, generate a tiny JSON metadata file 
(a "kerchunk reference"), and suddenly your 1990s NetCDF becomes queryable 
like a modern Zarr store — with IPFS-backed resilience included.

It half-works. The half that fails is important.

---

## What Is Kerchunk?

[Kerchunk](https://fsspec.github.io/kerchunk/) (now also called VirtualiZarr) 
is a library that scans binary scientific data files (NetCDF4, GRIB2, GeoTIFF, 
etc.) and generates a small JSON "reference file" that maps Zarr-style chunk 
keys to byte ranges inside the original file.

```json
{
  "version": 1,
  "refs": {
    ".zattrs": "{}",
    "sst/.zarray": "{\"chunks\":[7,1,720,1440],\"dtype\":\">f4\",...}",
    "sst/0.0.0.0": ["/path/to/data.nc", 16396, 29030400]
  }
}
```

The third element in that array is `[file_path, byte_offset, byte_length]`. 
xarray can open this reference with `engine="kerchunk"`, making the original 
file look like a Zarr store. Partial reads work because xarray issues 
byte-range HTTP requests when the path is a URL.

**The IPFS bridge is simple:** replace the file path with an IPFS gateway URL.

```python
# Before:
"sst/0.0.0.0": ["/data/oisst_jan2024.nc", 16396, 29030400]

# After (IPFS):
"sst/0.0.0.0": ["http://127.0.0.1:8080/ipfs/QmavHV9...", 16396, 29030400]
```

Now your data file lives on IPFS (content-addressed, can be pinned by anyone), 
and your reference file is a portable 9 KB JSON document. The reference file 
itself can also live on IPFS.

---

## The Experiment

**Dataset:** NOAA OISST v2.1, Jan 1–7 2024, global 0.25° resolution  
**Format:** NetCDF3 "classic" (28 MB)  
**CID:** `QmavHV9YBRCDLf7kDsPnbJfrPUXfpncjR5vSjbAw4zoeXU`

```python
from kerchunk.netCDF3 import NetCDF3ToZarr
refs = NetCDF3ToZarr("/data/oisst.nc").translate()  # 55 ms
```

Inspecting the chunk layout:

```
Variable      Key              Byte offset    Size
-----------   -------------    -----------    --------
latitude      latitude/0              7,756      2,880 B
longitude     longitude/0            10,636      5,760 B
sst           sst/0.0.0.0            16,396   29,030,400 B  ← 29 MB!
time          time/0                 inline     (103 B)
```

There it is. The SST variable — 7 days × 1 depth level × 720 lat × 1440 lon 
— is stored as one contiguous block of 29 MB. **NetCDF3 classic has no 
internal chunking.** The entire variable is a single "chunk" from kerchunk's 
perspective.

---

## Benchmark Results

Opening the IPFS-backed reference with xarray:

```python
ds = xr.open_dataset("oisst_refs_ipfs.json", engine="kerchunk")
```

| Operation | Local disk | IPFS gateway | Overhead |
|-----------|-----------|--------------|---------|
| `xr.open_dataset()` | 24 ms | 208 ms | 9x |
| Full SST field (720×1440) | 26 ms | 119 ms | **4.6x** |
| Gulf Stream subset (25–45°N) | ~1 ms | ~1 ms | **0.8x** ★ |
| Time series at Boston (7 days) | 9 ms | 95 ms | **10.2x** |

★ Sub-millisecond because the 29 MB chunk was already in memory from the 
previous full-field read. The "subset" doesn't actually do a smaller request.

The IPFS local gateway served the 29 MB block at **244 MB/s**. That's 
legitimately fast — comparable to reading from S3 with a good connection.

**Data correctness: PASS.** Bit-for-bit identical between local and IPFS reads.

---

## The Chunking Trap

Here's the gotcha: a "spatial subset" of a NetCDF3 file via kerchunk+IPFS 
still transfers the *entire variable*.

When xarray wants latitude 25–45°N, longitude 280–310°E from the SST field:

1. It asks kerchunk which chunks cover that region
2. Kerchunk says: chunk `sst/0.0.0.0` — the whole 29 MB
3. xarray fetches 29 MB from IPFS
4. xarray then slices the in-memory array to your bounding box

The "subset" at the network level is indistinguishable from a full-field read. 
You're paying 29 MB for any SST query, regardless of how small your region of 
interest is.

Compare this to the Zarr approach from Session 1, where the same OISST data 
was rechunked into 120×240 tiles (~61 KB each):

```
Gulf Stream subset (Zarr on IPFS):
  ~16 chunks × 61 KB = ~1 MB transferred
  
Gulf Stream subset (NetCDF3 kerchunk on IPFS):
  1 chunk × 29 MB = 29 MB transferred
  
Ratio: 29x more data transferred
```

This also means IPFS's block-splitting doesn't help you here. IPFS splits 
files into 256 KB blocks internally, but the kerchunk access pattern issues 
a byte-range request for the entire 29 MB chunk in one HTTP call. IPFS 
reassembles it transparently. You never benefit from block-level deduplication 
or caching.

---

## When Kerchunk + IPFS *Does* Work Well

The kerchunk+IPFS approach pays off when the source format has **fine-grained 
internal chunking**:

**NetCDF4/HDF5 with internal chunks**  
ERA5 reanalysis data from the Copernicus CDS is stored as HDF5 with 
~9 MB spatial chunks. Each chunk is a separate byte-range request. Kerchunk 
would map each HDF5 chunk to its own IPFS byte-range, enabling real partial 
reads without reformatting.

**GRIB2**  
Each GRIB2 message covers a single field (one variable, one level, one time) 
and is typically 1–5 MB. Kerchunk has a GRIB2 scanner. An IPFS-hosted GRIB2 
archive with a kerchunk reference becomes efficiently queryable by variable 
and level.

**GeoTIFF with internal tiling**  
Cloud-Optimized GeoTIFFs (COGs) use internal tiles (typically 256×256 or 
512×512 pixels). Kerchunk maps each tile to a byte-range. Works well on IPFS.

**The common thread:** if the format stores data in spatially or temporally 
coherent byte-ranges, kerchunk+IPFS gives you efficient access. If the format 
stores everything sequentially (NetCDF3), you're always fetching the whole 
variable.

---

## The xarray/zarr3 Compatibility Wrinkle

One implementation note: if you try to open a kerchunk reference with the 
standard `engine="zarr"` path:

```python
# This fails with zarr 3.x:
mapper = fsspec.filesystem("reference", fo=refs, remote_protocol="http").get_mapper("")
ds = xr.open_dataset(mapper, engine="zarr", consolidated=False)
# ValueError: Reference-FS's target filesystem must have same value of asynchronous
```

The fix is to use kerchunk's own xarray backend:

```python
# This works:
ds = xr.open_dataset("my_refs.json", engine="kerchunk")
```

Or use `zarr.open(mapper, mode='r')` directly without going through xarray's 
zarr engine.

---

## The Architecture Picture

```
                  ┌─────────────────────────────┐
                  │  kerchunk ref file (9 KB)   │  ← portable, shareable
                  │  (can also be on IPFS)      │  ← ~10,000x smaller than data
                  └────────────┬────────────────┘
                               │ chunk key → (CID, offset, length)
                               ▼
              ┌────────────────────────────────────┐
              │    IPFS Gateway (local or public)  │
              │    HTTP Range: bytes=16396-29046795│
              └────────────────┬───────────────────┘
                               │
              ┌────────────────▼───────────────────┐
              │    NetCDF3 file in IPFS blockstore  │
              │    CID: QmavHV9...                  │
              └─────────────────────────────────────┘
```

The reference file is tiny and can be stored alongside the CID in a catalog. 
Anyone with the reference file and an IPFS node (or access to a public gateway) 
can read the data. The CID guarantees the file hasn't been tampered with.

**But for NetCDF3:** that `bytes=16396-29046795` in the Range header is the 
entire 29 MB SST variable. You're not getting the "smart partial read" the 
diagram implies.

---

## What I'd Do Differently for Production

For a real environmental data archive wanting IPFS resilience:

1. **Re-chunk to Zarr first** (the Session 1 approach). Pick chunks that 
   match your access patterns: ~1–4 MB spatial chunks for global fields, 
   or time-first for time series.

2. **Then IPFS-add the Zarr directory** — each chunk is already a 
   natural unit of content-addressing.

3. **Use IPNS** (Session 2) for a stable, updateable pointer: 
   `ipns://oisst.noaa.gov` → latest CID.

4. **Only use kerchunk** if you cannot reformat the source data (historical 
   archives, live operational feeds in GRIB2, etc.) *and* the source format 
   has internal chunking (HDF5/GRIB2/COG).

---

## Honest Assessment

Kerchunk + IPFS is a **clever zero-copy solution** for the right data formats. 
For NetCDF3 (which describes much of the NOAA/NCAR operational archive), it 
provides IPFS's content-addressing guarantee but not its access efficiency.

If your goal is resilience (content-addressing, multi-pinner, can't-be-taken-down), 
kerchunk+IPFS works for any format. Every read is correct, every CID is 
verifiable. The file can't silently change.

If your goal is also *performance* — efficient partial reads, low latency for 
spatial subsets — you need the source format to have byte-addressable chunks.

**TL;DR:** Kerchunk bridges old formats to IPFS. But it can't chunking 
that wasn't there to begin with. For NetCDF3 archives, convert to Zarr first.

---

*Next: Testing with ERA5 HDF5 files (the case where kerchunk+IPFS should 
actually shine) and the Filecoin/web3.storage pinning question — if nobody 
else pins your CID, does IPFS resilience mean anything?*

*Code and data: [github.com/rsignell/ipfs-geoscience-research](https://github.com/rsignell)*  
*Session notes: `/home/ubuntu/notes/2026-03-05-kerchunk-ipfs.md`*
