#!/usr/bin/env python3
"""Render an ERA5 2m-temperature map opened DIRECTLY from the IPFS dataset
(rechunked Icechunk store via http_storage over ipfs.io). Poster figure."""
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import icechunk, xarray as xr

GATEWAY = "https://ipfs.io"
CID = "bafybeiecltl3mtags2i3jeumxe5c7zuvj2r76zxwxg6tfljiouvywqzbaq"

t0 = time.time()
storage = icechunk.http_storage(f"{GATEWAY}/ipfs/{CID}")
repo = icechunk.Repository.open(storage)
ds = xr.open_zarr(repo.readonly_session("main").store, consolidated=False, chunks={})
print("opened from IPFS in %.1fs; t2 %s" % (time.time()-t0, ds["t2"].shape))

# one timestep, convert K -> degC
t2 = ds["t2"].isel(time=0)
lat = ds["latitude"].values if "latitude" in ds else ds["lat"].values
lon = ds["longitude"].values if "longitude" in ds else ds["lon"].values
data = t2.values - 273.15
data = np.where(data > 60, np.nan, data)  # mask the lone 999.0 sentinel pixel
tstr = str(ds["time"].isel(time=0).values)[:16] if "time" in ds else ""
print("frame:", tstr, "range %.1f..%.1f C" % (np.nanmin(data), np.nanmax(data)))

# lon 0..360 -> -180..180 for nicer global view
if lon.max() > 180:
    order = np.argsort(((lon + 180) % 360) - 180)
    lon2 = ((lon + 180) % 360) - 180
    lon2 = lon2[order]; data = data[:, order]
else:
    lon2 = lon

fig = plt.figure(figsize=(14, 7.2), dpi=200)
ax = plt.axes(projection=ccrs.Robinson())
ax.set_global()
mesh = ax.pcolormesh(lon2, lat, data, transform=ccrs.PlateCarree(),
                     cmap="RdYlBu_r", shading="auto", vmin=-40, vmax=40)
ax.add_feature(cfeature.COASTLINE, linewidth=0.6, edgecolor="#222")
ax.add_feature(cfeature.BORDERS, linewidth=0.25, edgecolor="#555", alpha=0.4)
gl = ax.gridlines(linewidth=0.4, color="#888", alpha=0.35, linestyle=":")
cb = plt.colorbar(mesh, orientation="horizontal", pad=0.04, shrink=0.82, aspect=40,
                  extend="both")
cb.set_label("2\u2009m air temperature (\u00b0C)", fontsize=15)
cb.ax.tick_params(labelsize=12)
ax.set_title(f"ERA5 t2 \u2014 opened directly from IPFS (CID bafybeiecltl3\u2026)\n{tstr}Z",
             fontsize=16, fontweight="bold", pad=14)
plt.tight_layout()
out = "era5_from_ipfs_map.png"
plt.savefig(out, bbox_inches="tight", dpi=200, facecolor="white")
print("saved", out)
