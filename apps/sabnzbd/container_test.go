package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/sabnzbd:rolling")

	helpers.RequireHTTPEndpoint(t, image, helpers.HTTPTestConfig{
		Port: "8080",
		Path: "/sabnzbd",
	}, nil)

	helpers.RequireFileExists(t, image, "/usr/local/bin/python")
	helpers.RequireFileExists(t, image, "/usr/bin/unrar")
	helpers.RequireFileExists(t, image, "/usr/bin/par2")

	// par2 is expected to provide these as symlinks, not separate binaries.
	helpers.RequireSymlink(t, image, "/usr/bin/par2create")
	helpers.RequireSymlink(t, image, "/usr/bin/par2repair")
	helpers.RequireSymlink(t, image, "/usr/bin/par2verify")
}
