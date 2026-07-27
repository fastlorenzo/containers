package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/holmes-poller:rolling")

	app := &helpers.ContainerConfig{Env: map[string]string{"PYTHONPATH": "/app"}}

	helpers.RequireCommandSucceeds(t, image, app, "python", "-c", "import poller")
	helpers.RequireCommandSucceeds(t, image, nil, "python", "-c", "import requests, redis")
}
