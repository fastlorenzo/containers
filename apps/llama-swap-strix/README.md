# llama-swap-strix

`llama-swap` with a custom llama.cpp build for **Strix Halo / gfx1151**, built
for exactly one machine: `ai-box` (Framework Desktop, Ryzen AI Max+ 395, 122 GiB
unified memory, Vulkan/RADV backend). It is not a general-purpose image.

## What it currently carries

[**LaurentZuijdwijk/llama.cpp**](https://github.com/LaurentZuijdwijk/llama.cpp)
`c28d538d` (2026-08-25), a fork whose upstream merge base is ggml-org
`95b8e33e1` (2026-08-23). Vulkan-only work, tested by its author on a Radeon
8060S with Mesa RADV 26.0.8 — the same GPU and driver ai-box runs.

| Change                                       | Author's claim                      |
| -------------------------------------------- | ----------------------------------- |
| LDS stride bank-conflict fix (**RADV only**) | +7–14% across devices               |
| Tiled concat-transpose for MoE               | +45% on Ornith                      |
| IQ3_S register-spill elimination             | 5.4× at batch 8                     |
| Dense prefill                                | +13.0% @ depth 0 → +4.6% @64K       |
| MoE prefill, Ornith-35B-A3B, **ubatch 2048** | pp2048 1648.5 vs 870.5 t/s mainline |
| MoE generation                               | parity                              |

Why this is interesting for ai-box specifically: the fork's MoE benchmark model
_is_ the `coder` route (Ornith-35B-A3B), the LDS fix is RADV-only and ai-box is
RADV, and ai-box's heaviest consumers (HolmesGPT, OpenClaw resending 50–130k
token transcripts) are **prefill-bound** — which is where these changes claim
their wins.

The fork also adds adaptive speculative decoding (`--spec-draft-adaptive`,
`--spec-type draft-dflash`) and ROCmFPx quantisation. Those need different
weights and a draft model, are a separate and much larger experiment, and are
**not** what this image is being evaluated for. `--spec-type draft-mtp` still
works, so ai-box's existing routes graft over unchanged.

⚠ **`-ub 2048` can hang this GPU.** The fork's own README: _"on this hardware,
`-ub 2048` with a context depth at or beyond 65536 reproducibly times out the
compute ring."_ The headline MoE prefill number requires exactly that. ai-box
runs `coder` at 262144 ctx and has livelocked twice on memory pressure already,
so bench `-ub 2048` at shallow depth only and never configure it on a route
above 64k.

## How it is built

Two build stages reproduce upstream's own `.devops/vulkan.Dockerfile` (same
Ubuntu base, package list and cmake flags, plus the web UI stage llama-server
embeds at compile time). The final stage **grafts** the result onto the stock
llama-swap image ai-box already runs, replacing only `/app/llama-server` and the
ggml backend shared objects.

The graft is what makes this useful: llama-swap, the entrypoint, the runtime
libraries and every path stay byte-identical to production, so benchmarking this
image against `BASE_IMAGE` changes one variable.

`LLAMA_REPO` / `LLAMA_REF` select what gets compiled — upstream at a `bNNNNN`
tag, or a fork at a pinned commit. `VERSION` is only a build label.

⚠ **`LLAMA_REF` must be an immutable ref.** A branch name silently invalidates
every benchmark taken against it. Renovate is disabled for this app
(`.renovaterc.json5`) for the same reason — updates are manual and deliberate.

⚠ The Vulkan kernel code lives in `libggml-vulkan.so`, **not** in the
`llama-server` binary. An image with only the binary replaced runs perfectly and
benchmarks exactly like stock — which reads as "the build does nothing" rather
than as a build error. `container_test.go` asserts the libraries are there, and
that the binary really is the fork (`--spec-draft-adaptive` is fork-only).

### Isolating the fork from upstream drift

ai-box runs b10331 (2026-08-08); the fork's base is 2026-08-23. A plain A/B
therefore measures _the fork plus three weeks of upstream commits_. To separate
them, build the extra target and bench three ways:

```
docker buildx bake image-upstream-base   # upstream @ 95b8e33e1, grafted identically
```

`stock b10331` vs `up-95b8e33e` vs `lz-c28d538d`.

## Using it

Consumed by ai-box via `aibox_llama_patched_image` (digest-pinned, top-level in
`k8s-home/ansible/group_vars/ai_box/main.yml`). It is wired in as an extra
**benchmark backend** first, not as the serving image — while that variable is
empty the whole thing is inert:

```
ai-bench sweep coder-fa-patch    # backend dim: vulkan vs vulkan-patched
```

Promote to `aibox_images.llama_swap` only if it wins prompt processing at two or
more depths, does not regress token generation, and leaves GTT headroom for the
largest resident tier.

## History

Originally built to carry ggml-org/llama.cpp#25494 (_"vulkan: dequant q8_0 KV
once in coopmat1"_) while it was unmerged. **That PR merged upstream
2026-08-19**, so the patch was retired and `patches/` is now empty — any base
newer than that date already includes it, this fork included. The app was kept
rather than deleted because the graft-and-A/B machinery is the reusable part.
