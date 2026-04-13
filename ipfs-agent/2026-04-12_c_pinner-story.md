---
title: "I Have a Geospatial Dataset. What's My IPFS Pinning Strategy?"
date: 2026-04-12
tags: [ipfs, geospatial, zarr, kerchunk, virtualizarr, netcdf, data-publishing]
summary: "The provider side of IPFS for geospatial data. A practical decision tree for getting your dataset onto IPFS without unnecessary copying, reformatting, or pain."
---

# I Have a Geospatial Dataset. What's My IPFS Pinning Strategy?

*Part 2 of the CODED IPFS series. [Part 1](./2026-03-05_b_ipfs-vs-s3-benchmark.md) covered the client side: given data already on IPFS, how fast are range queries? This post covers the provider side: how do you GET data onto IPFS in the first place?*

---

The question I hear most from researchers: "This IPFS stuff sounds great. But I have a dataset already sitting somewhere — on my server, on S3, on a NOAA FTP server. Do I really have to copy everything?"

The answer is: **it depends, and there's a spectrum of options.** Let me walk through each one with real code and real tradeoffs.

## The Core Question: How Much Do You Actually Want to Copy?

There are four positions on the copy spectrum:

```
COPY ALL THE THINGS                          COPY NOTHING
     │                                           │
  ipfs add -r              filestore --nocopy   kerchunk/VirtualiZarr
  (full copy)              (file references)    (pointer only)
     │                           │                   │
  Data in IPFS            Data on local disk    Data wherever it was
  blockstore              IPFS = index only     IPFS = manifest only
```

Let's go through each.

---

## Option 1: Standard `ipfs add` — The Full Copy

This is the simplest path. You add your data to IPFS, it gets chunked into 256KB blocks, SHA-256 hashed, and stored in the IPFS blockstore.

```bash
# For a Zarr store (a directory)
time ipfs add -r --cid-version=1 /path/to/dataset.zarr

# For a single file
time ipfs add --cid-version=1 dataset.nc
```

**What I measured on our research node:**

| Dataset | Size | ipfs add time | Throughput |
|---------|------|--------------|------------|
| Synthetic test Zarr | 1.45 MB | 0.245s | ~6 MB/s |
| OISST Jan 2024 Zarr | 7 MB | ~0.6s | ~12 MB/s |
| OISST 1-year Zarr | 430 MB compressed | ~35s | ~12 MB/s |

*Note: small files show lower throughput due to per-file API overhead; throughput scales up with larger stores.*

**The critical flag: `--cid-version=1`**

Without it, you get a CIDv0 (`Qm...` prefix). With it, you get a CIDv1 (`bafy...` prefix) that's base32-encoded, case-insensitive, and works in HTTP gateways as a subdomain. **Always use `--cid-version=1` for new data.**

**What you get:**
- ✅ Data fully self-contained in IPFS
- ✅ Survives deletion of source files
- ✅ CID is cryptographic fingerprint of your data
- ✅ Can serve from any IPFS node or gateway
- ❌ Storage doubles (original + IPFS blockstore)
- ❌ Can't do atomic updates (use IPNS for mutable pointer)

**After adding, pin it on Storacha for durability:**

```bash
# Export as CAR (Content Addressable aRchive)
ipfs dag export bafybeid35szapah... > dataset.car

# Upload to Storacha
w3 up --car dataset.car
```

The `--car` flag is critical — without it, `w3 up` wraps your CAR as an opaque blob with a *different* CID, breaking the content-addressing chain.

---

## Option 2: Filestore `--nocopy` — References, Not Blocks

If your data is already on local disk and you don't want to double the storage, the IPFS filestore is your friend.

```bash
# Enable in config (ONE-TIME SETUP)
ipfs config --json Experimental.FilestoreEnabled true

# Restart the daemon (required!)
sudo systemctl restart ipfs
# or: ipfs shutdown && ipfs daemon &

# Then add without copying
time ipfs add -r --cid-version=1 --nocopy /path/to/dataset.zarr
```

**What changes:**
- IPFS stores `(filename, byte_offset, length)` tuples in a "filestore" index
- Zero data duplication
- The CID is **identical** to what you'd get from a standard add (content addressing is deterministic — same data, same CID, regardless of how it was stored)

**The catch that will bite you:**

```bash
# This works:
ipfs cat bafybei.../zarr.json

# Move the source file...
mv /path/to/dataset.zarr /different/path/dataset.zarr

# This breaks:
ipfs cat bafybei.../zarr.json
# Error: could not find file /path/to/dataset.zarr
```

The filestore is a **pointer**, not a copy. If the source moves, the IPFS data becomes unreadable. For a server where files live in a stable location, this is fine. For data you might reorganize, it's a footgun.

**Practical use cases for `--nocopy`:**
- Data observatory: you have a 10TB archive on a dedicated NVMe, path never changes
- Institutional server: `/data/oisst/` is a permanent mount point
- Staging: you're evaluating before committing to a full-copy strategy

**NOT suitable for:**
- Cloud VM with ephemeral storage
- Data you actively reorganize
- Disaster recovery (you need the actual bytes elsewhere)

---

## Option 3: Kerchunk — Pin the Manifest, Not the Data

This is the one that surprised me the most. If your data is in HDF5 or NetCDF4 format, you can create a tiny reference JSON that maps Zarr-style chunk coordinates to byte ranges in the original file. Pin *that* on IPFS. Keep the data wherever it was.

**The insight:** HDF5 stores data in internally chunked arrays. Those chunks already have addresses (byte offsets within the file). Kerchunk reverse-engineers those offsets and expresses them as a standard Zarr-compatible lookup table.

### Step 1: Generate the manifest

```python
import kerchunk.hdf as kh
import json

# Data lives on NOAA's server. No copy needed.
url = "https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr/202401/oisst-avhrr-v02r01.20240101.nc"

h = kh.SingleHdf5ToZarr(url, url)
refs = h.translate()  # Takes ~1.5s — reads HDF5 metadata headers only

with open("/tmp/oisst_jan01_kerchunk.json", "w") as f:
    json.dump(refs, f)
```

**What the manifest looks like:**

```json
{
  "version": 1,
  "refs": {
    ".zgroup": "{\"zarr_format\":2}",
    "sst/0.0.0.0": ["https://www.ncei.noaa.gov/.../oisst-avhrr-v02r01.20240101.nc", 47587, 662271],
    "sst/.zarray": "{\"chunks\":[1,1,720,1440],\"dtype\":\"<i2\",...}",
    "lat/0": ["https://www.ncei.noaa.gov/...", 22275, 2880],
    ...
  }
}
```

The `sst/0.0.0.0` entry says: "The SST data chunk lives at byte offset 47587, length 662271 bytes, in the original file at that NOAA URL." 

**8.2 KB manifest for a 1.5 MB NetCDF4 file. 175x metadata compression.**

### Step 2: Pin the manifest on IPFS

```bash
# This pins 8.2 KB. The 1.5 MB data stays on NOAA's servers.
CID=$(ipfs add -Q --cid-version=1 /tmp/oisst_jan01_kerchunk.json)
echo $CID
# bafkreiebc55an5yztuwnxd7dlo7cuc7vrbp7eccieoivyi6uzlaj2b7lfa
```

### Step 3: Clients fetch manifest from IPFS, data from original URL

Here's the working code (with the crucial `engine='kerchunk'` flag — not `engine='zarr'`):

```python
import fsspec, xarray as xr, numpy as np, tempfile, os

# The manifest CID — content-addressed, permanent
cid = "bafkreiebc55an5yztuwnxd7dlo7cuc7vrbp7eccieoivyi6uzlaj2b7lfa"

# Fetch 8.2 KB manifest from IPFS
with fsspec.open(f"http://your-ipfs-gateway/ipfs/{cid}") as f:
    content = f.read()

# Write to temp file (needed for engine='kerchunk' API)
with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="wb") as tmpf:
    tmpf.write(content)
    tmp_path = tmpf.name

# Open with xarray — data fetched from NOAA via HTTP range requests
ds = xr.open_dataset(
    tmp_path,
    engine="kerchunk",
    backend_kwargs={"storage_options": {"remote_protocol": "https"}}
)
val = float(np.squeeze(ds.sel(lat=35.0, lon=285.0, method='nearest').sst.values))
print(f"SST at Miami-ish: {val:.1f}°C")  # 21.9°C ✓

os.unlink(tmp_path)
```

**Measured timings:**
- Manifest fetch from IPFS: **0.21s** (8.2 KB over loopback)
- Spatial point query (single HDF5 chunk from NOAA HTTPS): **1.68s**
- Total cold query: ~1.9s

**⚠️ Important gotcha:** Use `engine='kerchunk'`, NOT `engine='zarr'`. With zarr v3, the `zarr.open_group(reference_mapper)` call fails with `ValueError: Reference-FS's target filesystem must have same value of asynchronous`. The kerchunk engine sidesteps this entirely.

### What this pattern actually gives you

The kerchunk manifest CID is a **content-addressed pointer to a dataset's structure**. It's immutable (the manifest bytes have one CID forever), pinnable, and tiny. You're not promising that the data stays on NOAA's servers forever — but you are giving anyone with the CID a cryptographically verifiable way to find and validate the manifest.

**⚠️ This is NOT data resilience.** The manifest refs look like:

```json
"sst/0.0.0.0": ["https://www.ncei.noaa.gov/.../oisst-avhrr-v02r01.20240101.nc", 47587, 662271]
```

The actual data bytes live on NOAA's servers. If NOAA goes dark tomorrow, the CID is a content-addressed pointer to a manifest that points nowhere. Kerchunk+IPFS is useful for **integrity verification** (did the dataset structure change?) but it does not make the *data itself* resilient.

For genuine data resilience, the bytes need to be on IPFS and actively pinned:

```bash
# What actually achieves resilience:
wget https://www.ncei.noaa.gov/.../oisst-avhrr-v02r01.20240101.nc
ipfs add --cid-version=1 oisst-avhrr-v02r01.20240101.nc   # bytes on IPFS
ipfs dag export $CID > oisst_jan01.car
w3 up --car oisst_jan01.car   # Filecoin-backed, survives NOAA going dark
```

You can then optionally generate a kerchunk manifest with refs pointing to the IPFS gateway URL instead of the NOAA URL — but the critical step is pinning the actual data bytes first.

```python
# Refs pointing to your S3 bucket
url = "s3://my-org-data/oisst/2024/01/oisst-avhrr-v02r01.20240101.nc"
h = kh.SingleHdf5ToZarr(url, url, storage_options={"anon": True})
refs = h.translate()
# Pin refs on IPFS → clients fetch manifest from IPFS, data from your S3
```

When your data eventually moves, update the S3 path, re-generate the manifest, and publish a new CID. The old CID remains valid for as long as the manifest file is pinned.

---

## Option 4: VirtualiZarr — Kerchunk's Younger Sibling

[VirtualiZarr](https://virtualizarr.readthedocs.io/) does the same thing as kerchunk but with a more xarray-native API and deeper zarr v3 integration. As of version 2.5.1, it works — but the API has changed substantially from earlier versions.

```python
import virtualizarr as vz
from virtualizarr.parsers import HDFParser
from obspec_utils.registry import ObjectStoreRegistry
from obstore.store import LocalStore

# Set up an object store registry (new in v2.x)
registry = ObjectStoreRegistry()
registry.register("file:///tmp/", LocalStore("/tmp"))
parser = HDFParser()

# Open virtually — reads HDF5 metadata, no data loaded
vds = vz.open_virtual_dataset(
    "file:///tmp/oisst_20240101.nc",
    registry=registry,
    parser=parser
)

# Export as kerchunk-compatible reference JSON
refs = vds.virtualize.to_kerchunk(format="dict")
```

**VirtualiZarr vs kerchunk comparison:**

| Feature | kerchunk | VirtualiZarr 2.5.1 |
|---------|----------|---------------------|
| Output size (OISST 1 day) | 7.8 KB | 19.0 KB |
| SST byte offset | 47587 | 47587 (identical ✓) |
| Coordinate handling | file references | base64-inlined |
| HTTP URL support | ✓ | ✓ (via HTTPStore) |
| Zarr v3 native output | partial | ✓ (to_zarr()) |
| API stability | stable | API changed in v2.x |

The larger VZ output is because it inlines small coordinate arrays (lat, lon, time) as base64 strings directly in the JSON, instead of byte-range references. This is actually more portable — the manifest is self-contained for coordinates. The data variable offsets are identical.

**My take:** For quick kerchunk-style pinning, kerchunk is simpler. For building workflows that will evolve toward zarr v3 virtual stores, VirtualiZarr is the right investment.

---

## Option 5: S3 Datastore Plugin (Document Only)

For completeness: IPFS has a `go-ds-s3` plugin that makes an S3 bucket the backing datastore for your IPFS node. Your "blockstore" lives in S3 instead of local disk.

**Config skeleton:**

```json
{
  "Datastore": {
    "Spec": {
      "type": "s3ds",
      "region": "us-west-2",
      "bucket": "my-ipfs-datastore",
      "rootDirectory": "ipfs"
    }
  }
}
```

**Why I'm documenting this but not testing it:**
- Requires recompiling Kubo with the plugin
- `go-ds-s3` is a separate Go module, not bundled in standard Kubo
- For most researchers, the CAR file → S3 workflow is equivalent and simpler:

```bash
# Same result, no plugin needed:
ipfs dag export $CID > dataset.car
aws s3 cp dataset.car s3://my-bucket/ipfs-archive/
# To restore: aws s3 cp ... | ipfs dag import
```

The CAR approach gives you S3 durability without re-architecting your IPFS node.

---

## The Decision Tree

```
What format is your data?
│
├── Already Zarr (store on disk)
│   ├── Data is small-medium (< 10GB) → ipfs add -r --cid-version=1
│   │   └── Then: ipfs dag export | w3 up --car (pin on Storacha)
│   │
│   ├── Data is large and disk space is tight → ipfs add -r --cid-version=1 --nocopy
│   │   └── Requires: filestore enabled + daemon restart + stable file paths
│   │
│   └── Data is on S3 already → CAR export + s3 upload OR S3 datastore plugin
│       └── Simplest: s3 sync → EC2 → ipfs add → dag export → w3 up --car
│
├── HDF5 / NetCDF4 (has internal HDF5 chunks)
│   ├── Data can stay where it is (NOAA, your S3, institutional server)
│   │   └── kerchunk or VirtualiZarr → pin reference JSON on IPFS
│   │       └── 8 KB manifest for 1.5 MB file = 175x metadata compression
│   │       └── Clients fetch manifest from IPFS, data from original URL
│   │
│   └── Want full IPFS hosting (data must survive original URL going offline)
│       └── ipfs add original.nc → pin full file
│           └── Then optionally: generate kerchunk refs pointing to IPFS URL
│               (gateway URL in the refs, original IPFS CID in the notes)
│
├── NetCDF3 (no internal chunking)
│   └── kerchunk works but each variable = 1 giant chunk = inefficient for subsets
│       └── Better: rechunk to Zarr first (xarray + encoding param)
│           → then ipfs add -r --cid-version=1
│
└── GeoTIFF / COG (Cloud Optimized GeoTIFF)
    └── kerchunk has TIFF support via kerchunk.tiff
        └── OR: gdal_translate to Zarr → ipfs add
```

---

## The Filestore Gotcha (That Caught Me)

When I ran this experiment, the sequence was:

```bash
ipfs config --json Experimental.FilestoreEnabled true
ipfs add -r --cid-version=1 --nocopy /tmp/test_small.zarr
# Returns: bafybeidos4hmiybeu22jj6sq7arhyom2d7t5y6gc6togoz6pkyexxlghhy (same CID as standard add!)
```

The `--nocopy` flag works before daemon restart, but it **silently falls back to copying blocks** if the filestore isn't active yet. The CID is identical (same data = same CID), so you don't immediately notice. Only after restart does `ipfs filestore ls` show your file as a reference.

**Verification:** After enabling filestore and restarting:
```bash
ipfs filestore ls
# STATUS  CID                              PATH
# ok      bafkrei...                       /path/to/dataset.zarr/0/0/0
# ok      bafkrei...                       /path/to/dataset.zarr/0/0/1
```

If you see `ERR` status entries, your source files have moved.

---

## Putting It Together: The Kerchunk+IPFS Pattern in Practice

Here's the pattern I'd recommend for institutional data providers who want to expose data via IPFS without moving anything:

### 1. Batch-generate manifests

```python
import kerchunk.hdf as kh
import json, subprocess
from pathlib import Path

files = [
    "https://www.ncei.noaa.gov/.../oisst-avhrr-v02r01.20240101.nc",
    "https://www.ncei.noaa.gov/.../oisst-avhrr-v02r01.20240102.nc",
    # ...
]

manifest_cids = {}
for url in files:
    date = url.split(".")[-3][-8:]  # extract YYYYMMDD
    refs = kh.SingleHdf5ToZarr(url, url).translate()
    
    path = f"/tmp/manifest_{date}.json"
    with open(path, "w") as f:
        json.dump(refs, f)
    
    cid = subprocess.check_output(
        ["ipfs", "add", "-Q", "--cid-version=1", path]
    ).decode().strip()
    
    manifest_cids[date] = cid
    print(f"{date}: {cid}")
```

### 2. Create a combined reference (MultiZarrToZarr)

```python
from kerchunk.combine import MultiZarrToZarr

# Open all single-file refs
refs_list = []
for url in files:
    refs_list.append(kh.SingleHdf5ToZarr(url, url).translate())

# Combine into a time-series virtual store
mzz = MultiZarrToZarr(
    refs_list,
    remote_protocol="https",
    concat_dims=["time"],
    identical_dims=["lat", "lon", "zlev"]
)
combined_refs = mzz.translate()

# Pin the combined manifest
with open("/tmp/oisst_jan2024_combined.json", "w") as f:
    json.dump(combined_refs, f)

combined_cid = subprocess.check_output(
    ["ipfs", "add", "-Q", "--cid-version=1", "/tmp/oisst_jan2024_combined.json"]
).decode().strip()

print(f"Combined manifest CID: {combined_cid}")
# This CID is a content-addressed pointer to 31 days of SST data
# with data still on NOAA's servers
```

### 3. Publish the manifest CID alongside your DOI

```bibtex
@dataset{oisst2024,
  title = {NOAA OISST v2.1, January 2024},
  doi = {10.25921/xxxxxxxx},
  note = {IPFS manifest CID: bafkrei...}
}
```

Clients can now verify they have the right data structure using the CID, even if NOAA's URL structure changes.

---

## Copy Semantics Summary

| Method | Storage overhead | Source file needed? | Data on IPFS? | Good for |
|--------|-----------------|-------------------|---------------|---------|
| `ipfs add` | 100% (full copy) | No | Yes | Self-hosting, portability |
| `ipfs add --nocopy` | ~0% (index only) | Yes (same path!) | Technically yes | Large stable archives |
| kerchunk JSON pin | <0.01% (8 KB!) | Yes (original URL) | No (pointer only) | Institutional data |
| S3 datastore plugin | 0% (S3 is store) | No (S3 is store) | Yes (via S3) | Enterprise, large scale |

---

## Gotchas Catalog

**1. `engine='zarr'` breaks with reference filesystems in zarr v3**
```python
# WRONG (zarr v3 async/sync incompatibility):
xr.open_dataset(mapper, engine="zarr", consolidated=False)

# CORRECT:
xr.open_dataset(path_to_json, engine="kerchunk", 
                backend_kwargs={"storage_options": {"remote_protocol": "https"}})
```

**2. Filestore requires daemon restart**
```bash
ipfs config --json Experimental.FilestoreEnabled true
# MUST restart before --nocopy actually stores references:
sudo systemctl restart ipfs
```

**3. `--cid-version=1` is not the default**
```bash
# Without flag → CIDv0 (Qm...) — doesn't work as HTTP subdomain
# With flag → CIDv1 (bafy...) — base32, case-insensitive, gateway-friendly
ipfs add --cid-version=1 mydata.nc
```

**4. `w3 up --car` not `w3 up`**
```bash
# w3 up dataset.car → wraps as opaque blob, NEW CID (breaks!)
# w3 up --car dataset.car → uploads as CAR, preserves original CID (correct!)
```

**5. VirtualiZarr 2.5.1 API changed**
```python
# OLD (< 2.0):
vds = vz.open_virtual_dataset("file.nc", indexes={})

# NEW (2.5.1):
registry = ObjectStoreRegistry()
registry.register("file:///path/", LocalStore("/path"))
vds = vz.open_virtual_dataset("file:///path/file.nc", registry=registry, parser=HDFParser())
```

---

## When Kerchunk Fails You

Kerchunk is great for HDF5/NetCDF4 with internal chunking. But:

- **NetCDF3**: No internal chunks. Each variable is one contiguous array. Kerchunk "works" but every query fetches the entire variable. Rechunk to Zarr first.
- **Badly chunked HDF5**: If the original HDF5 was written with large chunks (e.g., full time series × full lat/lon), kerchunk inherits those chunks. Point queries will over-fetch. Check with `ncdump -h` before investing in a manifest.
- **Compressed NetCDF4 with filters**: Kerchunk can handle it, but the filter chain (HDF5 filters → NumPy codec) must be available on the client side.

For badly structured NetCDF files, the rechunk path is worth it:

```python
import xarray as xr

# Rechunk to Zarr (one-time operation)
ds = xr.open_dataset("poorly_chunked.nc")
ds.to_zarr(
    "well_chunked.zarr",
    encoding={"sst": {"chunks": (30, 180, 360)}}  # 30 time steps × lat slice × lon slice
)

# Then ipfs add the Zarr store
# ipfs add -r --cid-version=1 well_chunked.zarr
```

From [prior benchmarks](./2026-03-07_a_chunk-your-time.md): 30-day time chunks cut time-series reads 3.5x on IPFS (224ms → 64ms). The rechunk investment pays off immediately.

---

## The Bottom Line

**For data you own and can host:**
→ `ipfs add -r --cid-version=1` + `ipfs dag export | w3 up --car`

**For data you reference (NOAA, Copernicus, your institution's archive):**
→ kerchunk manifest + `ipfs add -Q --cid-version=1 manifest.json`

**For huge data already on stable local disk:**
→ filestore `--nocopy` (after daemon restart, stable paths only)

**For multi-file time series:**
→ kerchunk `MultiZarrToZarr` → combined manifest on IPFS

The beauty of the kerchunk path is that it turns IPFS into a **content-addressed index** over data that lives wherever it was already living. You get the CID determinism and permanence of IPFS without moving a single byte of actual data.

But be clear-eyed about what that buys you: **integrity verification**, not data survival. The manifest CID proves the dataset structure hasn't changed; it does nothing to keep the underlying bytes available if the original server disappears. For CODED's resilience goals, you need the data bytes on IPFS and pinned on Storacha — the manifest alone is just a fancy bookmark.

---

*All experiments run on EC2 us-west-2 (ip-172-31-30-18), Kubo 0.33.0, kerchunk 0.2.10, VirtualiZarr 2.5.1, April 2026.*

*OISST data: NOAA NCEI OISST v2.1. CID of manifest for Jan 1 2024: `bafkreiebc55an5yztuwnxd7dlo7cuc7vrbp7eccieoivyi6uzlaj2b7lfa`*
