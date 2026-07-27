package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/alerta-web:rolling")

	helpers.RequireFileExists(t, image, "/venv/bin/alerta")
	helpers.RequireCommandSucceeds(t, image, nil, "/venv/bin/python", "-c", "import alerta_prometheus_cluster")
}
