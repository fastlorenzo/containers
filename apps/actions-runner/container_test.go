package main

// This image is built for both amd64 and arm64, so every assertion here must hold on both.
// That rules out hardcoded multiarch library paths (/usr/lib/x86_64-linux-gnu/...) and anything
// installed only under `case "${TARGETARCH}"` -- notably Homebrew, which is amd64-only because it
// does not support ARM Linux.

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/actions-runner:rolling")

	helpers.RequireFileExists(t, image, "/home/runner/run.sh")
	helpers.RequireFileExists(t, image, "/usr/local/bin/yq")

	// The reason this image exists: Node >= 24 links against libatomic, which the upstream runner
	// image lacks. Asked via ldconfig rather than a file path so it holds on both arches, and
	// because what actually matters is that the dynamic linker can resolve it.
	helpers.RequireCommandSucceeds(t, image, nil, "sh", "-c", "/sbin/ldconfig -p | grep -q libatomic.so.1")

	// gcc AND make together are what Homebrew checks for before building a bottle-less formula
	// from source; missing make is what broke helmrelease-diff.
	helpers.RequireCommandSucceeds(t, image, nil, "gcc", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "make", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "gh", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "yq", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "jq", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "git", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "docker", "--version")
}
