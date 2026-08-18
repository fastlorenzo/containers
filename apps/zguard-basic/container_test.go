package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/zguard-basic:rolling")

	// `fastapi run` with no --port serves on 8000; the Dockerfile sets no PORT or EXPOSE.
	// /docs proves the image boots and FastAPI is serving without needing the
	// credentials ConfigMap mounted.
	helpers.RequireHTTPEndpoint(t, image, helpers.HTTPTestConfig{
		Port: "8000",
		Path: "/docs",
	}, nil)

	helpers.RequireFileExists(t, image, "/app/main.py")
}
