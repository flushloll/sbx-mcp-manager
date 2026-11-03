# SBX MCP Manager

A lightweight, open-source **macOS dashboard** for adding MCP servers to multiple [Docker Sandboxes](https://docs.docker.com/ai/sandboxes/) without repeatedly typing CLI commands.

> Community project; not affiliated with or endorsed by Docker. **Early preview:** test the application with your Docker version before relying on it.

## Features

- Discover sandboxes using `sbx ls -q`
- View MCP servers registered with `sbx mcp ls -q`
- Register curated or custom MCP servers (remote HTTPS or local stdio)
- Attach and detach MCP servers across multiple selected sandboxes
- Launch a local, authenticated browser dashboard by double-clicking a macOS `.command` file
- No third-party Python dependencies

## Install

Requirements: **macOS**, **Python 3**, Docker Desktop / `sbx` CLI, and `uvx` or `npx` for relevant local integrations.

```sh
git clone https://github.com/flushloll/sbx-mcp-manager.git
cd sbx-mcp-manager
chmod +x 'scripts/Launch SBX MCP Manager.command'
./scripts/'Launch SBX MCP Manager.command'
```

Alternatively, double-click the launcher in Finder and keep its Terminal window open. Make a Desktop alias for convenient access. The browser opens automatically. If macOS Gatekeeper warns about a downloaded launcher, inspect the code and approve the file via System Settings > Privacy & Security; don't disable Gatekeeper globally.

## Usage

1. Start Docker Desktop and make sure `sbx ls` works in Terminal.
2. Run the launcher.
3. Register a preset or a custom MCP (HTTPS endpoint or executable + arguments).
4. Check one or more **sandboxes** and **registered MCP servers**.
5. Click **Attach** or **Detach**. Restart your agent if it doesn't see newly loaded tools.

For a Blender MCP integration, Blender and the Blender-side add-on still need to be running.

## Security

**Local stdio MCP servers may run directly on your Mac with your user's permissions, outside the sandbox.** Only register commands you trust. Remote servers may require OAuth and consume paid API credits.

- HTTP listener binds to `127.0.0.1` and uses an ephemeral port.
- One-time unlock link, per-process random authentication token, HttpOnly SameSite cookie, and token-protected POST requests.
- Host and Origin validation and subprocess argument arrays (never shell injection).
- No hosted backend or analytics. The app invokes your locally installed `sbx` executable.
- This is not a security boundary against compromised local apps, malicious browser extensions, or untrusted MCP servers.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 src/server.py
```

## Known limitations

- Not signed/notarized and not tested against every `sbx` release.
- A curated catalog, not an automatically verified universal MCP registry.
- Local MCP argument strings cannot include commas when passed through Docker's comma-separated `--args`.
- Server registration and successful MCP connection are different from successful access to the underlying app (such as Blender).
- `sbx` gateway configurations are independent of Docker Desktop MCP Toolkit.

## License

MIT. See [LICENSE](LICENSE).
