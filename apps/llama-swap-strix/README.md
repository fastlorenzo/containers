# llama-swap-strix

`llama-swap` with an out-of-tree llama.cpp patch for **Strix Halo / gfx1151**,
built for exactly one machine: `ai-box` (Framework Desktop, Ryzen AI Max+ 395,
122 GiB unified memory, Vulkan/RADV backend). It is not a general-purpose image.

## What it carries

**ggml-org/llama.cpp[#25494](https://github.com/ggml-org/llama.cpp/pull/25494)**
— *"vulkan: dequant q8_0 KV once in coopmat1"*, open upstream as of 2026-08.
The Vulkan coopmat1 flash-attention path dequantises the q8_0 KV cache once per
workgroup (32×); the patch does it once into scratch, in per-head-contiguous
form, so the memory-bound read at prefill is cheaper.

That matters here because **every generative route on ai-box runs `kv: q8_0`
with `-fa 1`**, which is precisely the configuration the patch targets. Author's
measurements on a Qwen3-MoE-30B-A3B with q8_0 KV — essentially ai-box's `coder`
route:

| | pp512 @32k | pp512 @65k | tg32 @32k | tg32 @65k |
|---|---|---|---|---|
| stock | 200.2 t/s | 99.1 t/s | 36.71 | 26.27 |
| patched | **282.0 t/s** | **166.2 t/s** | 36.73 | 27.50 |

Greedy output is reported byte-identical; the cost is a scratch buffer that
scales with KV size (~268 MB @128k), which is why the on-box A/B watches GTT
peak and not only tokens/s.

The PR's `tests/test-backend-ops.cpp` hunk is **not** vendored: it does not
apply to b10331 (the surrounding flash-attention test block moved) and the image
builds with `LLAMA_BUILD_TESTS=OFF`. Everything under `ggml/` — the actual
runtime change — applies with offsets.

## How it is built

Two build stages reproduce upstream's own `.devops/vulkan.Dockerfile` (same
Ubuntu base, package list and cmake flags, plus the web UI stage llama-server
embeds at compile time), with `patches/*.patch` applied to the checked out
release tag first. The final stage then **grafts** the result onto the stock
llama-swap image ai-box already runs, replacing only `/app/llama-server` and the
ggml backend shared objects.

The graft is what makes this useful: llama-swap, the entrypoint, the runtime
libraries and every path stay byte-identical to production, so benchmarking this
image against `BASE_IMAGE` changes one variable.

⚠ **`VERSION` and `BASE_IMAGE` move together or not at all.** `VERSION` is the
llama.cpp release tag to compile; `BASE_IMAGE` must be the llama-swap image
built from that same llama.cpp build. Bumping one alone silently turns the A/B
into "patch + version bump vs stock" and the numbers stop meaning anything.
Renovate is disabled for this app (see `.renovaterc.json5`) for that reason —
updates here are manual and deliberate.

⚠ The patched Vulkan code lives in `libggml-vulkan.so`, **not** in the
`llama-server` binary. An image with only the binary replaced runs perfectly and
benchmarks exactly like stock — which reads as "the patch does nothing" rather
than as a build error. `container_test.go` asserts the libraries are there.

## Using it

Consumed by `ai-box` via `aibox_images.llama_swap_patched` (digest-pinned, in
`k8s-home/ansible/group_vars/ai_box/main.yml` of the infra repo). It is wired in
as an extra **benchmark backend** first, not as the serving image:

```
ai-bench sweep coder-fa-patch    # backend dim: vulkan vs vulkan-patched
```

Promote it to `aibox_images.llama_swap` only if it wins prompt processing at
two or more depths, does not regress token generation, and leaves GTT headroom
for the largest resident tier.

## Retire it when the PR merges

This image exists only because #25494 is unmerged. Once it lands in an upstream
llama.cpp release, point ai-box back at the stock `mostlygeek/llama-swap` image
and delete this app.
