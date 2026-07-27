package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/postgres-init:rolling")

	// The four clients entrypoint.sh actually invokes. Asserted via /usr/bin, which the
	// postgresqlNN-client package symlinks, so these survive a major-version bump -- the previous
	// test pinned /usr/libexec/postgresql17/psql while the image ships 14, and had gone stale.
	helpers.RequireFileExists(t, image, "/usr/bin/psql")
	helpers.RequireFileExists(t, image, "/usr/bin/createdb")
	helpers.RequireFileExists(t, image, "/usr/bin/createuser")
	helpers.RequireFileExists(t, image, "/usr/bin/pg_isready")
}
