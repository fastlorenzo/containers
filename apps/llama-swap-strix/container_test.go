package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/llama-swap-strix:rolling")

	// The whole image is a graft: a custom llama-server plus the ggml backend
	// shared objects, copied over the stock llama-swap image. The failure mode
	// worth testing for is a PARTIAL graft — the Vulkan kernel work lives in
	// libggml-vulkan.so, not in the binary, so an image with only the binary
	// replaced boots fine, serves fine, and benchmarks exactly like stock. That
	// is indistinguishable from "the build did nothing" unless the libraries
	// are checked to be present.
	//
	// The runner has no GPU, so nothing here exercises Vulkan; these assert the
	// image is assembled correctly, and the on-box sweep decides whether it is
	// any good.
	helpers.RequireCommandSucceeds(t, image, nil, "/bin/sh", "-c",
		"ls -1 /app/libggml-vulkan.so* /app/libggml-base.so*")

	// Provenance: the exact repo/commit that was compiled. Recorded by the
	// build stage because VERSION is only a label — it cannot be trusted to say
	// what was actually checked out.
	helpers.RequireCommandSucceeds(t, image, nil, "/bin/sh", "-c",
		"test -s /app/llama-source.txt && cat /app/llama-source.txt")

	// Proves the FORK was compiled and not upstream. --spec-draft-adaptive
	// exists only in LaurentZuijdwijk/llama.cpp; building upstream by mistake
	// yields an image that runs perfectly and benchmarks as a null result,
	// which reads as "the fork does nothing" rather than as a build error.
	//
	// Guard, not a feature test: drop this assertion if this app is ever
	// pointed back at an upstream ref (see LLAMA_REPO in docker-bake.hcl).
	helpers.RequireCommandSucceeds(t, image, nil, "/bin/sh", "-c",
		"/app/llama-server --help 2>&1 | grep -q -- --spec-draft-adaptive")

	// The base image must survive the graft: llama-swap orchestrates, and
	// ai-box's llama-swap config execs /app/llama-server per route.
	helpers.RequireFileExists(t, image, "/app/llama-swap")
	helpers.RequireFileExists(t, image, "/app/llama-server")

	helpers.RequireCommandSucceeds(t, image, nil, "/app/llama-server", "--version")
}
