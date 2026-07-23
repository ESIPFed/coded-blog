# CODED ESIP Summer Meeting 2026 Posters

IPFS as a resilience layer for cloud-optimized geoscience data (Zarr · Icechunk · xarray).

- **v1** (`esip_ipfs_poster_v1.*`) — original "Singapore Test" framing: full 2.08 GB
  ERA5 cold read from Singapore against three back-ends (IPFS HTTP gateway, Icechunk on
  S3, local IPFS daemon over Bitswap).
- **v2** (`esip_ipfs_poster_v2.*`) — refreshed after the Session 51/52 work. Reframes the
  story around *decomposing* the cost of decentralized access: discovery vs transfer
  (distance dominates, not the DHT), the caching win (up to 6.3× cross-region cold→warm,
  ~190 MB/s warm floor), an Icechunk-on-S3 control, and reading Icechunk straight from
  IPFS via `http_storage` with zero adapter code.
- **v3** (`esip_ipfs_poster_v3.*`) — "Read & Preserve" framing, built around the
  runnable `read_real_era5_from_ipfs.ipynb` notebook. Left column shows the *actual*
  rendered notebook: opening a real 2 GB ERA5 Icechunk dataset by its CID over HTTP
  (with a two-gateway `try/except` fallback: CODED node → `ipfs.io`), the live map, and
  the bit-for-bit global-mean result. Right column shows how anyone can *preserve* their
  own Zarr/Icechunk dataset by writing a CID to Storacha/Filecoin (incl. the `coded-pin`
  one-liner).
- `poster_comparison_old_vs_new.png` — v1 and v2 side by side.
- `poster_v2_vs_v3.png` — v2 and v3 side by side.

Each version ships as `.html` (source), `.pdf` (print, 36" × 48" portrait), and `.png`
(3456 × 4608 raster). Rendered with WeasyPrint → pdftoppm.
