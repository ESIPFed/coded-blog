# CID-alongside-DOI: A Proposal for Content-Addressed Scientific Dataset Records

**Version:** 1.0  
**Date:** 2026-03-26  
**Author:** CODED IPFS Research Project  
**Target:** DataCite Metadata Working Group, IASSIST 2026, Zenodo engineering  
**Contact:** rsignell@gmail.com

---

## The Problem

A DOI is a persistent, location-independent identifier. When you publish a dataset and register
a DOI via DataCite or Zenodo, the DOI resolves to wherever the data lives. That's valuable.
But a DOI has a critical limitation: **it is not content-addressed**.

This means:
- A dataset can be silently replaced at the same DOI without anyone noticing
- A corrupted file is indistinguishable from the original, from the metadata's perspective
- A subscriber or archive cannot cryptographically prove they have "the same thing" as the publisher
- Data consumers have no trustless way to verify their download against the citation

This is not theoretical. Files change. Repositories migrate. Mistakes happen. 
And in the environmental data domain — where datasets represent years of satellite observations —
the difference between the real data and a quietly modified file can matter enormously.

---

## The Solution: CIDv1 as AlternateIdentifier

IPFS Content Identifiers (CIDs) are SHA-256 Merkle DAG hashes of a file or directory tree.
The same content always produces the same CID. Any change — even a single flipped bit — 
produces a completely different CID. This is a cryptographic guarantee.

**The proposal is simple:**  
When depositing a dataset and registering a DOI, also compute the CIDv1 of the dataset
and add it to the DataCite metadata record as an `alternateIdentifier`.

### DataCite XML (works today, no schema change required)

```xml
<alternateIdentifiers>
  <!-- Standard repository accession -->
  <alternateIdentifier alternateIdentifierType="LocalAccessionNumber">
    OISST-2024-daily-global-0.25deg
  </alternateIdentifier>
  <!-- Content-addressed identifier: cryptographic integrity proof -->
  <alternateIdentifier alternateIdentifierType="CIDv1">
    bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q
  </alternateIdentifier>
</alternateIdentifiers>
```

This works with **DataCite Metadata Schema 4.4 and 4.5 today**. The `alternateIdentifierType`
field accepts free text. No schema change, no new tooling, no infrastructure requirement.

---

## Generating a CID: One Command

```bash
# Compute CIDv1 for any file or directory — WITHOUT uploading to IPFS
# (--only-hash means: compute hash locally, write nothing to disk)
ipfs add --only-hash --recursive --cid-version=1 ./dataset.zarr
# → bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q

# Works for any format: Zarr, NetCDF, GeoTIFF, CSV, HDF5...
ipfs add --only-hash --cid-version=1 ./era5_temperature_2024.nc
# → bafybeig...

# For very large datasets, this takes seconds:
# 430MB compressed Zarr (3GB uncompressed, 11,712 chunks) → 5.8 seconds
```

The Kubo IPFS client (`ipfs`) is the only dependency. It does not need to be running as a daemon
for `--only-hash` computation.

---

## Verifying a Download: One Command

A consumer who downloads a DOI-cited dataset can verify integrity in seconds:

```bash
# 1. Check the DOI record's alternateIdentifier for the CIDv1
#    Example: bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q

# 2. Download the dataset from the DOI URL (as normal)
wget "https://zenodo.org/record/XXXXXXXX/files/oisst_2024.zarr.zip"
unzip oisst_2024.zarr.zip

# 3. Verify
ipfs add --only-hash --recursive --cid-version=1 ./oisst_2024.zarr
# → bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q ✅ MATCH

# If the CIDs differ: the data has been modified since the DOI was issued.
```

### Verified with Real Data

The following has been tested and verified in this research project:

| Dataset | DOI (example) | Published CID | Verification time |
|---------|--------------|---------------|-------------------|
| NOAA OISST 2024, 366 days global SST (430MB compressed, 11,712 chunks) | 10.5281/zenodo.XXXXX | `bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q` | 5.8s |
| NOAA OISST Jan 2024, 7 days (7MB) | — | `bafybeidjfdpt5semk3iii2kaal6r3mvepzxcxr5eyvuvibdivvelq3yhiq` | <1s |

CID determinism has been confirmed across 44 independent research sessions.

---

## Dual Value: Verification AND Access

A CID in the DOI record is not just a checksum — it's also an address. Once published:

**1. Verification without any IPFS infrastructure:**
```bash
ipfs add --only-hash --cid-version=1 ./dataset.zarr   # compare to DOI record
```

**2. Direct IPFS access (if IPFS node is available):**
```python
import xarray as xr, fsspec

cid = "bafybeid35szapahnjyyq7jg5pilxku5l2jeuexhgacptj53ei4hozc7a3q"
ds = xr.open_zarr(fsspec.get_mapper(f"http://127.0.0.1:8080/ipfs/{cid}"))
```

**3. Access from Storacha CDN (no local node required):**
```python
ds = xr.open_zarr(fsspec.get_mapper(f"https://w3s.link/ipfs/{cid}"))
```

**4. Resilient access after Filecoin archival:**
After uploading a CAR file to Storacha, within ~5 days Filecoin storage deals are made.
IPNI (cid.contact) shows the CID with graphsync-filecoinv1 transport — permanent storage.
Anyone with the CID can retrieve the data indefinitely, independent of the originating institution.

---

## The Full Architecture (for institutions that want maximum resilience)

```
1. Create dataset                     →  ./oisst_2024.zarr
2. Compute CID                        →  ipfs add --only-hash --cid-version=1
3. Deposit to Zenodo/DataCite         →  get DOI
4. Add CID to metadata record         →  alternateIdentifier type="CIDv1"
5. ipfs add (full add, not --only-hash) → pin locally
6. ipfs dag export | w3 up --car      → Storacha (Filecoin deals in ~5 days)
7. Publish STAC item                  →  include ipfs:// + https:// asset hrefs
```

Steps 1-4 close the verification gap with minimal effort.  
Steps 5-7 add a resilient, content-addressed access path for cloud-native workflows.

---

## Near-Term Requests (in priority order)

### 1. DataCite Community Convention (TODAY, no changes needed)
Establish `"CIDv1"` as the recommended `alternateIdentifierType` string.
This is a documentation/convention change only — no schema PR needed.
Proposed wording for DataCite best-practices guide:
> "For datasets that have been content-addressed using IPFS, include the CIDv1 root hash
> as an alternateIdentifier with alternateIdentifierType='CIDv1'. This enables consumers
> to cryptographically verify data integrity after download."

### 2. DataCite Schema v4.6+ (NEAR-TERM, GitHub PR)
Add `CID` to the controlled list of `relatedIdentifierType` values (alongside ARK, DOI, Handle, etc.).
This would enable `<relatedIdentifier relatedIdentifierType="CID" relationType="IsIdenticalTo">` —
semantically richer than alternateIdentifier.
GitHub: https://github.com/datacite/schema/issues

### 3. Zenodo Integration (MEDIUM-TERM)
Add an optional "Content Hash (CIDv1)" field to the Zenodo deposit form.
Display it as a verifiable badge (similar to how Zenodo shows DOI and licenses).
Zenodo GitHub: https://github.com/zenodo/zenodo

### 4. Research Object Crate (RO-Crate) Integration (MEDIUM-TERM)
RO-Crate uses JSON-LD with schema.org. Add `contentIdentifier` as an RO-Crate property
pointing to `ipfs://<CID>`. This would propagate to DataCite, Zenodo, and any RO-Crate-aware system.

---

## Relationship to Existing Practice

| System | Content-addressing | Integrity check | Cloud-native access |
|--------|-------------------|-----------------|---------------------|
| Zenodo + DOI | No | MD5/SHA-256 checksum at upload | Whole-file download only |
| DataCite + DOI | No | None built-in | Whole-file download only |
| SciOp (BitTorrent) | Yes (per-file SHA-256) | Torrent hash | Whole-file download only |
| IPFS + CID | Yes (Merkle DAG) | Every block, continuously | HTTP range requests → xarray/Zarr |
| **DOI + CIDv1** | **Yes (via CID)** | **ipfs add --only-hash** | **IPFS gateway or CDN** |

---

## Conference Target

**IASSIST 2026** (International Association for Social Science Information Service & Technology)  
Topic: "Integrity verification for large scientific datasets: CID as a supplement to DOI"

Proposed abstract:  
> Content identifiers (CIDs) from the IPFS protocol provide SHA-256 Merkle DAG hashes
> that can be appended to DataCite metadata records with zero schema changes. We present
> a 44-session empirical study of IPFS for geospatial workflows and propose a lightweight
> convention for publishing CIDs alongside DOIs. We demonstrate that a 3GB environmental
> dataset can be cryptographically verified in under 6 seconds using a single CLI command,
> and that the same CID enables resilient, cloud-native access via the Filecoin/Storacha
> ecosystem. Implementation requires no infrastructure changes from data repositories.

---

## Open Questions

1. **Versioning:** CIDs are immutable. If data is corrected post-DOI, a new CID is issued.
   Convention: use `relationType="IsNewVersionOf"` to chain CIDs across versions. 
   The old CID remains valid forever — a feature, not a bug.

2. **Discoverability:** How do downstream tools (QGIS, GDAL, Pangeo) discover the IPFS
   access path from a CID in the metadata? Answer: STAC item with `ipfs://` asset href
   is the bridge. STAC clients gain IPFS awareness by adding `ipfs://` resolver.

3. **Orphaned CIDs:** A CID without a pinner disappears (Session 6 finding).
   Convention: only publish a CID in a DOI record after Storacha/Filecoin upload.
   This ensures the CID is backed by cryptographic storage guarantees.

---

*This proposal is informed by 44 research sessions of empirical IPFS testing with NOAA OISST
and synthetic geospatial datasets. All benchmarks, CIDs, and code are in:
https://github.com/rsignell/coded-blog*
