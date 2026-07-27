package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/openclaw:rolling")

	helpers.RequireCommandSucceeds(t, image, nil, "jq", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "python3", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "go", "version")
	helpers.RequireCommandSucceeds(t, image, nil, "git", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "curl", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "node", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "openclaw", "--version")
	helpers.RequireCommandSucceeds(t, image, nil, "ob", "--version")

	// ssh reports its version on stderr and exits 0.
	helpers.RequireCommandSucceeds(t, image, nil, "ssh", "-V")
	helpers.RequireCommandSucceeds(t, image, nil, "which", "unzip")
}
