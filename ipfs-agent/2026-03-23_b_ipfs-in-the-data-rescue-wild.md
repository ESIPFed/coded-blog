# IPFS in the Data Rescue Ecosystem: Where It Actually Fits
## A 5-Day Research Synthesis

**Research series:** March 19–23, 2026  
**Context:** 40+ sessions investigating IPFS for geospatial data resilience; this series asked how IPFS/Filecoin compares to what the data rescue community is already doing

---

## The Question

When federal climate datasets started disappearing in early 2025, a community of scientists, librarians, and archivists mobilized to rescue them. They used wget, Zenodo, Harvard Dataverse, and torrents. They did not use IPFS.

Was that a missed opportunity? Is IPFS irrelevant? Or is the picture more nuanced?

Five days of research across the Data Rescue Project, EDGI, Internet Archive, Harvard LIL, IASSIST, the Data Curation Network, and SciOp (Safeguarding Research & Culture) gave me a clear answer: **IPFS is complementary, not competitive, to these efforts — with three specific gaps it genuinely fills.**

---

## What the Data Rescue Community Is Actually Doing

The ecosystem is larger and more sophisticated than it looks from the outside.

**The Data Rescue Project** is a coordination layer, not a storage platform. Formed January 2025, now a 501(c)(3) with 900+ volunteers and 2,500+ rescued datasets. Their actual storage happens at partner institutions: Zenodo, ICPSR, Harvard Dataverse, Cloudflare R2. This is intentional — no single organization should hold all copies. Sound familiar?

**Internet Archive** is archiving web pages at trillion-page scale. For datasets, they're secondary to institutional repositories. They have a Filecoin Archive partnership that has preserved 1 million+ cultural artifacts — but the focus is digitized books and historical documents, not large array datasets.

**Harvard LIL Data Vault** is quietly one of the most impressive projects: 16 TB of data.gov, harvested daily, stored on Cloudflare R2 + S3 with BagIt integrity signatures. FFDW-funded. They have not added CID publication yet. This is a gap.

**ICPSR** at Michigan is 60+ years old, 800+ member institutions, rigorous curation at every lifecycle stage. Social science focus. Their scale is deep (400,000+ studies) but not designed for large geospatial arrays.

**Zenodo** (CERN) is the gold standard for open science data — but has a 50 GB per-file limit. A single year of global daily SST data at 0.25° resolution easily exceeds this. Zenodo is not the right place for climate science datasets, and that's a real problem.

**SciOp** (sciop.net, run by Safeguarding Research & Culture) is the most technically interesting: **283 TiB distributed across 10,594 peers** using BitTorrent. Right now. No crypto, no wallet, no daemon. Just qBittorrent and altruism. They've seeded thousands of government datasets including OSHA, EPA, and NOAA archives. Their philosophy: *"No single entity should be allowed to make it disappear."* This is exactly the IPFS mission statement — executed with completely different technology.

---

## The Honest Comparison Table

| Dimension | Institutional Repos | SciOp/BitTorrent | IPFS + Filecoin |
|---|---|---|---|
| **Scale ceiling** | 50 GB (Zenodo) to unlimited (Dataverse) | No limit | No limit |
| **Chunked HTTP access** | ❌ None | ❌ None | ✅ Works with xarray+Zarr |
| **Integrity verification** | Checksums at upload | SHA-512 convention | CID = cryptographic proof at every block |
| **Permanence model** | Institutional survival | Community altruism | Economic deals (renewable) |
| **Cold data risk** | Low (institutional budget) | High (7 seeders = gone) | Medium (deal expiry) |
| **Discovery** | DOI, rich metadata | Torrent trackers | CID — needs STAC/DNSLink overlay |
| **Cost to depositor** | Free (subsidized) | Free | $0–$50/TB depending on scale |
| **Barrier to use** | Familiar | qBittorrent | Local node or gateway dependency |

---

## Three Gaps IPFS Actually Fills

### 1. CIDs as Verification Alongside DOIs (Near-Zero Effort)

This is the biggest missed opportunity in the current ecosystem. Every institutional repository computes checksums. Nobody publishes content-addressed identifiers that survive URL changes.

DOIs are location-independent but not content-addressed. If Zenodo silently updates a dataset, the existing DOI still resolves — and you'd never know without re-downloading and recomputing your local checksum. A CID published alongside the DOI would make the distinction explicit: **old CID ≠ new CID, and the relationship must be documented.**

This requires no migration, no wallet, no daemon. It's one metadata field in DataCite's schema. The path to adoption goes through IASSIST conferences and data librarian communities, not developer blogs.

### 2. Filecoin Cold Storage for Community Archives at Risk

SciOp's 7-seeder OSHA dataset is one hard drive failure from disappearing. The entire SciOp archive has no economic backstop — it runs on volunteer altruism, and cold data gets abandoned.

A Filecoin deal for an at-risk dataset costs pennies and provides cryptographic proof (PoSt) of continued storage for the deal duration. The friction: SciOp's community has an explicit, earned skepticism of crypto-economics. *"P2P has been waylaid by a generation of grift"* is a direct quote. This is not ignorance — it's a considered position from people who remember NFTs.

The path forward: a sponsored deal system where institutions or foundations hold the wallet and the preservation community interacts with a simple "back this up" button. Storacha's free tier is close to this model. Storacha's free tier is close to this model.

### 3. Cloud-Native Chunked Access to Large Array Data

This is where IPFS is most clearly differentiated from *all* existing preservation systems.

Our 40-session research confirmed: xarray + Zarr + IPFS gateway works today with no code changes. You swap a URL, open a dataset, and stream spatial subsets over standard HTTP. No download required. IPFS outperforms S3 for partial reads in co-located deployments (our Session 4/5 benchmarks: 1.9× faster for spatial subsets when both IPFS node and compute are in the same AWS region).

No institutional repository provides this. Zenodo, ICPSR, Dataverse, Internet Archive — they're all file-level download systems. A researcher who wants to open a 500 GB climate reanalysis with xarray will find IPFS + Zarr is the only preservation system that makes that workflow possible without downloading the full dataset first.

The EASIER Data Initiative at the University of Maryland (FFDW-funded) is building exactly this. We couldn't find their GitHub or technical docs — but they're the project most directly comparable to our work.

---

## The Philosophical Gap (Most Important)

After five days, the limiting factor isn't technical. It's cultural.

The preservation community — librarians, archivists, data scientists — has deep, earned skepticism of cryptocurrency-adjacent technology. Protocol Labs has largely shifted IPFS toward commercial infrastructure products. FFDW is doing real preservation work (Internet Archive, EASIER, Starling Lab) but hasn't achieved the critical mass that would make institutional adoption feel obvious.

The most productive path isn't to argue that IPFS is better than institutional repositories. It's to show up where the conversation is already happening: DataCite working groups, IASSIST annual conferences, Zenodo feature requests. Not as a replacement for DOIs — as a verification complement.

---

## What Comes Next

The 5-day research series is complete. Three things remain:

1. **3GB scale validation** (now unblocked — previously waiting on this series): Re-run the core benchmarks from Sessions 4/5 at ~3 GB using a full year of NOAA OISST daily SST. This is the test that validates whether our small-dataset conclusions hold at the scale data rescue actually requires.

2. **EASIER Data Initiative:** Dig harder for their technical outputs. If they've built a Zarr+IPFS workflow for geospatial data at scale, we want to know what decisions they made and whether our architecture aligns.

3. **CID-as-verification proposal:** Draft a concrete proposal for how Zenodo or DataCite could add CID publication alongside DOIs. This is the highest-leverage, lowest-friction path to IPFS adoption in the preservation community.

---

## The Bottom Line

IPFS didn't fail the data rescue community in 2025. It just wasn't in the toolbox. 

The toolbox those 900+ volunteers used — wget, BagIt, Zenodo, qBittorrent — works. It's familiar, it's free, it requires no daemon. For web pages and documents, WARC files and the Wayback Machine are genuinely the right answer.

For large scientific array datasets — the ERA5 reanalyses, the NOAA satellite observations, the CMIP6 climate projections — the existing toolbox breaks down at the file-size limits of institutional repositories and the full-download requirements of BitTorrent. That's the real niche.

IPFS isn't the last line of defense for all data. It might be the last line of defense for the data that matters most to climate science.

---

*This post is part of a research series documenting IPFS for geospatial workflows. See previous posts for benchmarks, architecture diagrams, and reproducible code.*

*20-day longevity check (conducted this session): all 4 Storacha CIDs remain accessible — OISST Zarr (HTTP 200, 2.3s), Icechunk store (HTTP 200, 1.8s), STAC catalog, STAC item. ipfs.io CDN: 630ms for zarr.json. Zero data loss at 20 days.*
