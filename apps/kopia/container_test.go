package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/kopia:rolling")
	helpers.RequireFileExists(t, image, "/bin/kopia")
	helpers.RequireFileExists(t, image, "/scripts/sleep.sh")
}
