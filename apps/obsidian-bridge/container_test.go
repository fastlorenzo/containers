package main

import (
	"testing"

	helpers "github.com/home-operations/containers/tests"
)

// configRequiresCredentials asserts load_config() exits rather than starting up unconfigured.
const configRequiresCredentials = `import bridge.config, sys
try:
 bridge.config.load_config()
except SystemExit:
 sys.exit(0)
sys.exit(1)`

// renderNoteStripsQueries asserts dataview blocks are stripped and wikilinks flattened, while
// frontmatter and trailing content survive. The fence markers are spliced in because a Go raw
// string cannot contain a backtick; the \n sequences are deliberately literal, for Python to
// interpret.
const renderNoteStripsQueries = `from bridge.markdown import render_note
out = render_note("6. Entities/People/Someone.md",
                  "---\ntype: person\n---\nSees [[Acme Corp|Acme]].\n"
                  "` + "```" + `dataview\nLIST\n` + "```" + `\ntail\n")
assert "dataview" not in out and "LIST" not in out, out
assert "Acme." in out and "[[" not in out, out
assert "type: person" in out, out
assert "tail" in out, out`

func Test(t *testing.T) {
	image := helpers.GetTestImage("ghcr.io/fastlorenzo/obsidian-bridge:rolling")

	app := &helpers.ContainerConfig{Env: map[string]string{"PYTHONPATH": "/app"}}

	helpers.RequireCommandSucceeds(t, image, app, "python", "-c",
		"import bridge.main, bridge.server, bridge.sync, bridge.chats")
	helpers.RequireCommandSucceeds(t, image, nil, "python", "-c",
		"import fastapi, uvicorn, httpx, yaml, mcp")
	helpers.RequireCommandSucceeds(t, image, app, "python", "-c", configRequiresCredentials)
	helpers.RequireCommandSucceeds(t, image, app, "python", "-c", renderNoteStripsQueries)
}
