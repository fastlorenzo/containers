package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/xigmanas-backup:rolling")

	app := &helpers.ContainerConfig{Env: map[string]string{"PYTHONPATH": "/app"}}

	helpers.RequireCommandSucceeds(t, image, app, "python", "-c", "import xigmanas_backup")
	helpers.RequireCommandSucceeds(t, image, nil, "python", "-c",
		"import requests, boto3; from cryptography.hazmat.primitives.ciphers import Cipher")

	// Refuses to run unconfigured rather than silently doing nothing.
	helpers.RequireCommandExitCode(t, image, nil, 2, "python", "-u", "/app/xigmanas_backup.py")

	helpers.RequireImageUser(t, image, "65534:65534")
}
