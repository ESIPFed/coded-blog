# CODED ESIP Summer Meeting 2026 Posters

IPFS as a resilience layer for cloud-optimized geoscience data (Zarr · Icechunk · xarray).

- **v1** *(archived — `esip_ipfs_poster_v1.png` only; HTML/PDF removed)* — original "Singapore Test" framing: full 2.08 GB
  ERA5 cold read from Singapore against three back-ends (IPFS HTTP gateway, Icechunk on
  S3, local IPFS daemon over Bitswap).
- **v2** (`esip_ipfs_poster_v2.*`) — refreshed after the Session 51/52 work. Reframes the
  story around *decomposing* the cost of decentralized access: discovery vs transfer
  (distance dominates, not the DHT), the caching win (up to 6.3× cross-region cold→warm,
  ~190 MB/s warm floor), an Icechunk-on-S3 control, and reading Icechunk straight from
  IPFS via `http_storage` with zero adapter code.
- **v3** *(archived — `esip_ipfs_poster_v3.png` only; HTML/PDF removed)* — "Read & Preserve" framing, built around the
  runnable `read_real_era5_from_ipfs.ipynb` notebook. Left column shows the *actual*
  rendered notebook: opening a real 2 GB ERA5 Icechunk dataset by its CID over HTTP
  (with a two-gateway `try/except` fallback: CODED node → `ipfs.io`), the live map, and
  the bit-for-bit global-mean result. Right column shows how anyone can *preserve* their
  own Zarr/Icechunk dataset by writing a CID to a Filecoin-backed pinning service
  (Storacha at the time; Filebase today), including the `coded-pin` one-liner.
- **v4** *(archived — `esip_ipfs_poster_v4.png` only; HTML/PDF removed)* — intermediate revision superseded by v5/v6.
- **v5 / v6** (`esip_ipfs_poster_v5.*`, `esip_ipfs_poster_v6.*`) — current posters; v6 is the latest. Full `.html` + `.pdf` + `.png` sources retained.
- `poster_comparison_old_vs_new.png` — v1 and v2 side by side.
- `poster_v2_vs_v3.png` — v2 and v3 side by side.

Current versions (v5, v6) ship as `.html` (source), `.pdf` (print, 36" × 48" portrait), and `.png`
(3456 × 4608 raster), rendered with WeasyPrint → pdftoppm. Earlier versions (v1, v3, v4) are kept as `.png` archives only — their HTML/PDF sources have been removed to keep the repo lean.

**Build note — pin WeasyPrint to 63.1.** The poster is a fixed-height canvas
(`html,body` and `.poster` are `3456×4608px`; `.body` fills the remainder with
`flex:1`). WeasyPrint ≥ 64 changed how it fragments this layout: the left
column's "Step 1" block spills onto a phantom second page, orphaning content.
WeasyPrint 62.x renders one page but silently drops the top-right Telegram
sticky-note and the IPFS logo. **63.1 is the last version that renders this
poster correctly** (single page, all elements present). Render with:

```bash
python3 -m venv /tmp/wp63 && /tmp/wp63/bin/pip install 'weasyprint==63.1'
/tmp/wp63/bin/weasyprint esip_ipfs_poster_v6.html esip_ipfs_poster_v6.pdf
pdftoppm -r 96 -png esip_ipfs_poster_v6.pdf out && mv out-1.png esip_ipfs_poster_v6.png
```
