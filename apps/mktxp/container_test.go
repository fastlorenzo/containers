package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/mktxp:rolling")
	helpers.RequireFileExists(t, image, "/usr/bin/mktxp")
}
