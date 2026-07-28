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
- **v5** (`esip_ipfs_poster_v5.*`) — portrait, superseded. Full `.html` + `.pdf` + `.png` retained.
- **v6** (`esip_ipfs_poster_v6.*`) — portrait, superseded by the landscape rework. Full sources retained.
- **v6 landscape** (`esip_ipfs_poster_v6_landscape.*`) — first landscape (48" × 36") cut, superseded by v7.
- **v7 landscape** (`esip_ipfs_poster_v7_landscape.*`) — **current poster.** Landscape 48" × 36".
  Ships as `.html` (source), `.pdf` (print), and `.png` (4614 × 3462 raster, 96 dpi).
  A high-res `esip_ipfs_poster_v7_landscape_150.png` (7200 × 5400, 150 dpi) is also provided for large-format printing.
- `poster_comparison_old_vs_new.png` — v1 and v2 side by side.
- `poster_v2_vs_v3.png` — v2 and v3 side by side.

Earlier versions (v1, v3, v4) are kept as `.png` archives only — their HTML/PDF sources have been removed to keep the repo lean.

**Build note — landscape posters (v6 landscape, v7) render with headless Chromium, not WeasyPrint.**
The HTML canvas is authored at `4608 × 3456` CSS px (96 dpi). Render at higher DPI by bumping
the device scale factor (`150/96 = 1.5625` → 7200 × 5400). Example (Playwright):

```js
const page = await browser.newPage({
  viewport: { width: 4608, height: 3456 },
  deviceScaleFactor: 150 / 96,   // 96 dpi base → 150 dpi output
});
await page.goto('file://.../esip_ipfs_poster_v7_landscape.html', { waitUntil: 'networkidle' });
await page.screenshot({ path: 'out.png', clip: { x: 0, y: 0, width: 4608, height: 3456 } });
```

Then tag the DPI metadata so the print shop reads the physical size correctly:
`python3 -c "from PIL import Image; im=Image.open('out.png'); im.save('out.png', dpi=(150,150))"`.

**Legacy build note — the portrait posters (v5, v6) need WeasyPrint pinned to 63.1.** That canvas is a
fixed-height `3456×4608px` layout; WeasyPrint ≥ 64 spills the left column's "Step 1" block onto a phantom
second page, and 62.x silently drops the top-right sticky-note and IPFS logo. 63.1 is the last version
that renders it correctly. Render with:

```bash
python3 -m venv /tmp/wp63 && /tmp/wp63/bin/pip install 'weasyprint==63.1'
/tmp/wp63/bin/weasyprint esip_ipfs_poster_v6.html esip_ipfs_poster_v6.pdf
pdftoppm -r 96 -png esip_ipfs_poster_v6.pdf out && mv out-1.png esip_ipfs_poster_v6.png
```
