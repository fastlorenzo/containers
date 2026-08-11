target "docker-metadata-action" {}

variable "APP" {
  default = "llama-swap-strix"
}

// Upstream llama.cpp release tag to build, NOT a semver — llama.cpp tags are
// bNNNNN. Deliberately carries no `// renovate:` annotation: it MUST move in
// lockstep with BASE_IMAGE below (same llama.cpp build), and an independent
// bump of either one turns the whole point of this image — a one-variable A/B
// against stock — into a meaningless comparison. .renovaterc.json5 disables
// this app for the same reason.
variable "VERSION" {
  default = "b10331"
}

// The stock llama-swap image the patch is grafted onto and compared against —
// the digest that tag v248-vulkan-b10331 (VERSION above, b10331) currently
// resolves to. Not a free choice: it must be the build named by VERSION. Bump
// both together or not at all, and re-run `ai-bench sweep coder-fa-patch`.
//
// NOTE this is NOT the digest ai-box's group_vars pins for llama_swap
// (sha256:f3f7d5ec...). That older digest was dropped from the registry
// (mostlygeek re-pushed the tag) and no longer pulls — the box only still runs
// it from local cache. For the A/B to stay one-variable, ai-box should re-pin
// llama_swap to this same digest; see the PR discussion.
variable "BASE_IMAGE" {
  default = "ghcr.io/mostlygeek/llama-swap@sha256:23b44d01e07a3c0c0c2dc270a9faac21b666d7e99324c5190982f5d504008d80"
}

variable "SOURCE" {
  default = "https://github.com/ggml-org/llama.cpp"
}

group "default" {
  targets = ["image-local"]
}

target "image" {
  inherits = ["docker-metadata-action"]
  args = {
    VERSION    = "${VERSION}"
    BASE_IMAGE = "${BASE_IMAGE}"
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

// amd64 only: this exists for one gfx1151 APU. An arm64 build would be a long
// Vulkan compile producing an image nothing will ever pull.
target "image-all" {
  inherits = ["image"]
  platforms = [
    "linux/amd64"
  ]
}
