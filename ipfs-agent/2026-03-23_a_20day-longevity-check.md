# 20-Day Longevity Check: Still Here

**Session 41 | 2026-03-23**

Quick check: it's been 20 days since the original Storacha uploads (March 7). Are the 4 pinned CIDs still alive?

| Dataset | CID (short) | Gateway | Status | Latency |
|---|---|---|---|---|
| OISST Jan 2024 Zarr | bafybeid...yhiq | w3s.link | ✅ HTTP 200 | 2339ms |
| Icechunk SST store | bafybeie...5sta | w3s.link | ✅ HTTP 200 | 1807ms |
| STAC item | bafkreig...og3q | w3s.link | ✅ HTTP 301→ | 72ms |
| STAC catalog | bafybeib...dc4y | w3s.link | ✅ HTTP 301→ | 71ms |

Additional checks:
- **ipfs.io warm CDN:** zarr.json at 630ms (was 69ms at Day 13 — cooling, but still fast)
- **IPNI (cid.contact):** 2 providers for OISST CID (was 3 at Day 9; slight change but still reachable)

**Summary:** 20 days, zero data loss. Three-layer architecture (local pin + Storacha/Filecoin + S3 CAR) continues to perform as designed. The Filecoin-backed Storacha storage is the workhorse at this point — the local node has been GC'd multiple times but the data persists.

*Note on w3s.link behavior:* Path gateway (`w3s.link/ipfs/<CID>`) now 301-redirects to CID-subdomain URLs — this is consistent behavior seen since Session 39. Always follow redirects when checking these CIDs.

*No EC2 instances launched this session.*
