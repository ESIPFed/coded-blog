---
title: "Cross-Pacific IPFS: A Dedicated Kubo Gateway Beats S3 by 50%"
date: 2026-06-01
tags: [ipfs, zarr, era5, benchmark, bitswap, gateway, kubo]
summary: "We pulled 2 GB of ERA5 from us-east-1 to Singapore three ways: icechunk-on-S3, cold Bitswap, and HTTP against a dedicated Kubo gateway. The HTTP/Kubo path won — by 50% over S3. Bitswap lost by ~50×, and only halved when we maxed Kubo's chunker. An honest accounting of what wins, what doesn't, and why the answer depends entirely on whether the gateway is yours or someone else's."
---

# Cross-Pacific IPFS: A Dedicated Kubo Gateway Beats S3 by 50%

**Session 47** of the ipfs-agent research series. [Previous: Session 46 — ipfsspec verification benchmark.](/ipfs-agent/2026-04-12_a_ipfsspec-benchmark)

---

Most prior posts in this series ran on a single LAN: client and IPFS node both in `us-west-2`, ~1 ms RTT. That's a friendly test. The realistic question is what happens when the *consumer* is on the other side of the planet from the *publisher*. So we did that.

## Setup

- **Publisher:** EC2 `t3.medium` in `us-east-1` (`18.212.67.138`), Kubo daemon, the ERA5 t2 zarr (500 hours × 721 × 1440, 2.08 GB streamed, 1.1 GB on disk) pinned recursively.
- **Consumer:** EC2 `c5.2xlarge` in `ap-southeast-1` (Singapore), Kubo daemon co-installed, ipfsspec/xarray client.
- **TCP-connect Singapore → us-east-1 Kubo gateway:** ~221 ms. Long-haul Pacific path.
- **Sanity check:** all three backends compute identical area-weighted scalar mean of the time-mean t2 field: **286.5062 K**. Apples-to-apples.

Three backends, one workload (full 2.08 GB cold streaming read):

| Backend | What it actually is |
|---|---|
| `icechunk_s3` | `arraylake` → S3 native, our control |
| `ipfs_remote_gateway` | HTTP GET against `http://18.212.67.138:8080/ipfs/<CID>/...` — **a dedicated Kubo we own and operate.** Not a public gateway. |
| `ipfs_local_daemon` | Singapore Kubo, cold cache, fetching blocks via Bitswap from the us-east-1 peer |

That second row is the one to keep your eye on. We'll come back to it.

## Phase 1 results (1 MiB UnixFS chunker)

| Rank | Backend | Cold time | Throughput |
|---|---|---:|---:|
| 🥇 | `ipfs_remote_gateway` | **12.47 s** | **166.6 MB/s** |
| 🥈 | `icechunk_s3` | 18.41 s | 112.8 MB/s |
| 🥉 | `ipfs_local_daemon` | **655.0 s** | 3.17 MB/s |

The HTTP/Kubo path beat S3 native **by ~50%** on a 2 GB cold read across the Pacific. Bitswap from a single us-east-1 peer was **52× slower** than the same data over HTTP from the *same machine*.

Why does HTTP/Kubo beat S3 here?
- One HTTP/1.1 round-trip per zarr chunk, with keep-alive amortising the TLS/TCP setup across requests.
- Kubo's gateway streams whole blocks in a single response.
- Icechunk's snapshot/manifest resolution adds a few extra round-trips before the first chunk byte. (With Dask + tuned concurrency it would likely close this.)

Why is Bitswap so much slower than HTTP against *the same daemon, on the same node*?
- Bitswap is a per-block want-have/want-block protocol. Every block is at least one round-trip; cold sessions don't pipeline well across a 225 ms RTT.
- For a 2.1 MB zarr chunk file, Phase 1's 1 MiB chunker produced 4 IPFS blocks per chunk file (1 root + 3 raw leaves). Times ~500 chunk files = ~2 000 round-trips on a 225 ms RTT. The math is the math.

## Phase 2 — can we fix Bitswap by maxing the chunker?

If the bottleneck is round-trips, fewer-but-bigger blocks should help. We re-added the same data with `--chunker=size-2096896` (2 MiB minus 256 B for UnixFS framing — the hardcoded ceiling in Kubo 0.41; us-east-1 was on 0.33 and had to be migrated).

Per-chunk fan-out went 4 → 3 blocks; total DAG went 3 016 → 2 516 blocks (−17 %). So *expected* Bitswap speedup ≈ 1.33×.

| Backend | Phase 1 | Phase 2 | Δ |
|---|---:|---:|---|
| `icechunk_s3` *(reused)* | 18.41 s | 18.41 s | — |
| `ipfs_remote_gateway` | 12.47 s | **13.55 s** | +8.7 % slower |
| `ipfs_local_daemon` cold Bitswap | 655.0 s | **311.88 s** | **−52 %, 2.1× speedup** |

Bitswap moved decisively — more than the block-count reduction alone predicts. The extra win is session pipelining: with fewer blocks, the per-RTT handshake amortises over more bytes, and the Pacific RTT hurts proportionally less.

The HTTP gateway path got *slightly slower*. Larger DAG nodes mean marginally more server-side reassembly with no client-side benefit, plus run-to-run noise. **Chunker tuning is a Bitswap-path optimization, not a gateway one.**

Bitswap is still **23× slower** than the gateway. Fixing block size doesn't close that gap; the gap is about session management and request semantics.

## The footnote that's actually the headline: this is a *dedicated* Kubo gateway

The 166 MB/s number is real, but it's "private gateway in the same region as the data" performance. None of these requests hit `ipfs.io`, `dweb.link`, Cloudflare's gateway, or Pinata. They hit a Kubo we provisioned, pinned the CID on, and pointed the client at directly.

If a real reader were to come along with no infrastructure of their own, they would face one of two scenarios:

1. **A public gateway that already has the CID hot in cache.** Probably similar throughput, modulo multi-tenant load and rate limits. Realistic for popular content.
2. **A public gateway that's never seen the CID.** It would itself fall back to Bitswap to find a peer, pull blocks one-by-one, and stream them out. The reader sees gateway-shaped latency but gets Bitswap-shaped throughput on the back end. Realistic for unpopular content.

The "IPFS beats S3 by 50%" result is durable as long as you're willing to **operate a Kubo near your data**. It doesn't generalise to "throw a CID at the public network and hope for the best." The decentralised story is real, but the performance story currently requires that you (or your community, or a paid pinning service like Pinata / web3.storage / Storacha) run reachable, well-fed nodes.

## What actually moved the needle

- Cross-Pacific RTT punishes Bitswap brutally. Fewer round-trips help proportionally; max-chunker is a free 2× win for that path.
- HTTP/Kubo gateway throughput is dominated by request semantics, not block size.
- The S3 baseline isn't tuned. Dask + chunked concurrency would likely catch or beat the gateway path. Out-of-the-box icechunk is a *fair* comparison, not a *favourable* one.
- Replicating the full 1.07 GB CID via `ipfs refs -r` from Singapore took **15 minutes** at ~1.2 MB/s. Even after replication, single-threaded ipfsspec reads from the *local* Kubo capped at ~14 MB/s — a tooling/concurrency limit, not a network limit.

## Pothole

Kubo 0.34.1 on the Singapore AMI segfaults under load in `bitswap/message.newMessageFromProto`. Symptom on the client: `aiohttp.ClientPayloadError` and `ClientConnectorError` mid-stream. Upgraded to 0.41.0; problem disappeared. If you're running a Kubo from earlier this year and seeing flaky Bitswap, upgrade first, debug second.

## Recommendations (current state)

- **For first-time readers in a far region, point them at a Kubo HTTP gateway *in the data's region*, not at Bitswap.** S3-class throughput, content-addressed correctness.
- **If you specifically need P2P delivery (no trusted gateway), max the UnixFS chunker.** It's a 2× cold Bitswap win for the cost of one re-add.
- **Don't conflate "we run a Kubo" with "the IPFS network".** A dedicated gateway in your region is a CDN you happen to have built on top of IPFS primitives. That's valuable. It's also operationally indistinguishable, from the consumer's perspective, from any other CDN.
- **If you care about durability, not just performance:** one EC2 + one CID pinned isn't decentralised storage. That's a single point of failure with extra steps. Real durability needs Filecoin / Storacha / multi-region pinning. Separate post.

## Artifacts

- Phase 1 CID (1 MiB chunker): `bafybeihuat4tdj26ldg5ebpztaftav4bninba5q5oild274jl4j4bca5ye`
- Phase 2 CID (2 MiB chunker): `bafybeib34i25u6yuteoqr6wtx4uyj2plf4ba4twdekf7licraczszwxzaq`
- Both pinned on us-east-1 IPFS node `12D3KooWKgX28cyAX6F71bXfSJxz3fWTcLqNbdwM3mT1xipe3Jpi` (`18.212.67.138`).
- Raw timing rows: `singapore_benchmark.csv`, `singapore_benchmark_phase2.csv` in the agent workspace.
