package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/zguard:rolling")

	// `fastapi run` with no --port serves on 8000; the Dockerfile sets no PORT or EXPOSE.
	//
	// /docs rather than /healthz: healthz pings Redis and returns 500 when it is unreachable, and
	// every other route (/check, /allow, /disallow) needs Redis too. With no way to stand up a
	// companion container from this harness, /docs is the only endpoint that proves the image
	// boots and FastAPI is serving. The previous test asserted /healthz on 8080 and had gone
	// stale on both counts.
	helpers.RequireHTTPEndpoint(t, image, helpers.HTTPTestConfig{
		Port: "8000",
		Path: "/docs",
	}, nil)

	helpers.RequireFileExists(t, image, "/app/main.py")
}
