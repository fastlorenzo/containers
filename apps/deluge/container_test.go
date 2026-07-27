package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/deluge:rolling")

	// Default mode is the daemon, which listens on 58846 and speaks no HTTP.
	helpers.RequireListeningPort(t, image, "58846", nil)

	// DELUGE_BIN switches the entrypoint to the web UI, which does speak HTTP.
	helpers.RequireHTTPEndpoint(t, image, helpers.HTTPTestConfig{
		Port: "8112",
	}, &helpers.ContainerConfig{
		Env: map[string]string{
			"DELUGE_BIN": "deluge-web",
		},
	})

	helpers.RequireFileExists(t, image, "/usr/bin/python3")
	helpers.RequireFileExists(t, image, "/usr/bin/unrar")
}
