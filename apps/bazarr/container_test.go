package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/bazarr:rolling")
	helpers.RequireHTTPEndpoint(t, image, helpers.HTTPTestConfig{Port: "6767"}, nil)
	helpers.RequireFileExists(t, image, "/usr/local/bin/python")
	helpers.RequireFileExists(t, image, "/usr/bin/unrar")
}
