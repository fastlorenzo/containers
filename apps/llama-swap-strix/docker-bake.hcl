target "docker-metadata-action" {}

variable "APP" {
  default = "llama-swap-strix"
}

// Build label, not a semver and no longer necessarily a llama.cpp tag: it names
// what was compiled. `lz-<short-sha>` for the fork, `bNNNNN` for upstream.
// Deliberately carries no `// renovate:` annotation — see BASE_IMAGE and
// .renovaterc.json5.
variable "VERSION" {
  default = "lz-c28d538d"
}

// What to compile. Upstream by default; the fork for the current experiment.
variable "LLAMA_REPO" {
  default = "https://github.com/LaurentZuijdwijk/llama.cpp.git"
}

// Tag (bNNNNN) or full commit SHA. MUST be a SHA for anything that is not an
// immutable upstream tag: the fork's master moves, and a moving base silently
// invalidates every benchmark taken against it. Bump deliberately, then re-run
// the sweep.
//
// c28d538d = LaurentZuijdwijk/llama.cpp master @ 2026-08-25T23:49Z, whose
// upstream merge base is ggml-org 95b8e33e1 (2026-08-23).
variable "LLAMA_REF" {
  default = "c28d538df5c02643e701a8004db84dbf1bb0ffb2"
}

// The stock llama-swap image the build is grafted onto and compared against.
// Only llama-server and the ggml backends are replaced, so this supplies
// llama-swap itself and the runtime layout.
//
// This is the digest tag v248-vulkan-b10331 currently resolves to. NOTE it is
// NOT the digest ai-box's group_vars pins for llama_swap (sha256:f3f7d5ec...);
// that older digest was dropped from the registry when mostlygeek re-pushed the
// tag and no longer pulls — the box only still runs it from local cache.
variable "BASE_IMAGE" {
  default = "ghcr.io/mostlygeek/llama-swap@sha256:23b44d01e07a3c0c0c2dc270a9faac21b666d7e99324c5190982f5d504008d80"
}

variable "SOURCE" {
  default = "https://github.com/LaurentZuijdwijk/llama.cpp"
}

group "default" {
  targets = ["image-local"]
}

target "image" {
  inherits = ["docker-metadata-action"]
  args = {
    VERSION    = "${VERSION}"
    BASE_IMAGE = "${BASE_IMAGE}"
    LLAMA_REPO = "${LLAMA_REPO}"
    LLAMA_REF  = "${LLAMA_REF}"
  }
  labels = {
    "org.opencontainers.image.source" = "${SOURCE}"
  }
}

target "image-local" {
  inherits = ["image"]
  output = ["type=docker"]
  tags = ["${APP}:${VERSION}"]
}

// Upstream at the fork's own merge base, grafted identically.
//
// Without this the A/B is two variables: the fork's changes AND three weeks of
// upstream commits between the b10331 the box runs and the fork's 2026-08-23
// base. Building this target isolates the fork's actual contribution:
//   stock b10331  vs  upstream 95b8e33e1  vs  fork c28d538d
// Build with: docker buildx bake image-upstream-base
target "image-upstream-base" {
  inherits = ["image"]
  output = ["type=docker"]
  args = {
    VERSION    = "up-95b8e33e"
    BASE_IMAGE = "${BASE_IMAGE}"
    LLAMA_REPO = "https://github.com/ggml-org/llama.cpp.git"
    LLAMA_REF  = "95b8e33e1"
  }
  tags = ["${APP}:up-95b8e33e"]
}

// amd64 only: this exists for one gfx1151 APU. An arm64 build would be a long
// Vulkan compile producing an image nothing will ever pull.
target "image-all" {
  inherits = ["image"]
  platforms = [
    "linux/amd64"
  ]
}
