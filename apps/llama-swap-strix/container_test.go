package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/llama-swap-strix:rolling")

	// The whole image is a graft: a patched llama-server plus the ggml backend
	// shared objects, copied over the stock llama-swap image. The failure mode
	// worth testing for is a PARTIAL graft — the patched Vulkan flash-attention
	// code lives in libggml-vulkan.so, not in the binary, so an image with only
	// the binary replaced boots fine, serves fine, and benchmarks exactly like
	// stock. That is indistinguishable from "the patch did nothing" unless the
	// libraries are checked to be present.
	//
	// The runner has no GPU, so nothing here exercises Vulkan; these assert the
	// image is assembled correctly, and the on-box `ai-bench sweep
	// coder-fa-patch` decides whether it is any good.
	helpers.RequireCommandSucceeds(t, image, nil, "/bin/sh", "-c",
		"ls -1 /app/libggml-vulkan.so* /app/libggml-base.so*")

	// Written by the build stage from `git diff --stat` after applying
	// patches/, so a non-empty file proves the patches actually landed rather
	// than being skipped by a glob that matched nothing.
	helpers.RequireCommandSucceeds(t, image, nil, "/bin/sh", "-c",
		"test -s /app/patches-applied.txt && cat /app/patches-applied.txt")

	// The base image must survive the graft: llama-swap orchestrates, and
	// ai-box's llama-swap config execs /app/llama-server per route.
	helpers.RequireFileExists(t, image, "/app/llama-swap")
	helpers.RequireFileExists(t, image, "/app/llama-server")

	helpers.RequireCommandSucceeds(t, image, nil, "/app/llama-server", "--version")
}
