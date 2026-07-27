package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/tang:rolling")
	helpers.RequireFileExists(t, image, "/usr/libexec/tangd")
	helpers.RequireFileExists(t, image, "/usr/libexec/tangd-keygen")
	helpers.RequireFileExists(t, image, "/bin/busybox")
	helpers.RequireFileExists(t, image, "/entrypoint.sh")
}
