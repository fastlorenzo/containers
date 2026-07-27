package helpers

// Fork-specific assertions that upstream's helpers.go does not provide.
//
// helpers.go is kept byte-identical to home-operations/containers so it can be
// re-synced without conflicts; anything this fork needs on top lives here.

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/wait"

	dockerclient "github.com/moby/moby/client"
)

// RequireCommandExitCode tests that a command exits with a specific code. Use RequireCommandSucceeds
// for the exit-zero case; this exists for images that are expected to fail in a defined way, e.g.
// a job that must refuse to run unconfigured.
func RequireCommandExitCode(t *testing.T, image string, config *ContainerConfig, want int, entrypoint string, args ...string) {
	t.Helper()

	opts := []testcontainers.ContainerCustomizer{
		testcontainers.WithEntrypoint(entrypoint),
		testcontainers.WithWaitStrategy(wait.ForExit()),
	}

	if len(args) > 0 {
		opts = append(opts, testcontainers.WithEntrypointArgs(args...))
	}

	opts = append(opts, applyContainerConfig(config)...)

	ctx := t.Context()
	container := runContainer(t, ctx, image, opts...)

	state, err := container.State(ctx)
	require.NoError(t, err)
	require.Equal(t, want, state.ExitCode, fmt.Sprintf("command '%s %v' should exit %d", entrypoint, args, want))
}

// RequireListeningPort tests that a container listens on a port, without requiring it to speak
// HTTP. Use RequireHTTPEndpoint when there is an HTTP endpoint to check -- it is the stronger
// assertion.
func RequireListeningPort(t *testing.T, image string, port string, config *ContainerConfig) {
	t.Helper()

	portStr := port + "/tcp"

	opts := []testcontainers.ContainerCustomizer{
		testcontainers.WithExposedPorts(portStr),
		testcontainers.WithWaitStrategy(wait.ForListeningPort(portStr)),
	}

	opts = append(opts, applyContainerConfig(config)...)

	_ = runContainer(t, t.Context(), image, opts...)
}

// RequireSymlink tests that a path exists in the image and is a symlink.
//
// This runs `test -L` inside the container rather than reusing RequireFileExists' stat approach:
// the Docker archive endpoint that ContainerStatPath calls dereferences symlinks, reporting the
// target's mode and an empty LinkTarget, so symlink-ness is not observable through it. That means
// -- unlike RequireFileExists -- this needs a POSIX shell in the image.
func RequireSymlink(t *testing.T, image string, filePath string) {
	t.Helper()

	// The path is passed as an argument rather than interpolated into the script, so paths with
	// spaces or shell metacharacters cannot alter the command.
	opts := []testcontainers.ContainerCustomizer{
		testcontainers.WithEntrypoint("sh"),
		testcontainers.WithEntrypointArgs("-c", `test -L "$1"`, "sh", filePath),
		testcontainers.WithWaitStrategy(wait.ForExit()),
	}

	ctx := t.Context()
	container := runContainer(t, ctx, image, opts...)

	state, err := container.State(ctx)
	require.NoError(t, err)
	require.Equal(t, 0, state.ExitCode, "file %q should be a symlink in image %q", filePath, image)
}

// RequireImageUser tests that the image's configured default user matches want, e.g. "65534:65534".
// This inspects the image config, so the image must be present locally -- true in CI, where the
// :sandbox tag is loaded into the daemon, and under `mise run local-build`.
func RequireImageUser(t *testing.T, image string, want string) {
	t.Helper()

	cli, err := dockerclient.New(dockerclient.FromEnv)
	require.NoError(t, err)
	defer cli.Close()

	res, err := cli.ImageInspect(t.Context(), image)
	require.NoError(t, err)
	require.NotNil(t, res.Config, "image %q should have a config", image)
	require.Equal(t, want, res.Config.User, "image %q should run as user %q", image, want)
}
