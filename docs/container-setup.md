# Container Setup Guide

This project supports both Docker and Podman for containerized development.

## Quick Start

The Makefile automatically detects your container engine:

```bash
# Automatic detection (prefers Podman if available)
make dev-env

# Explicit engine selection
CONTAINER_ENGINE=docker make dev-env
CONTAINER_ENGINE=podman make dev-env
```

## Podman vs Docker

### Key Differences

| Feature | Docker | Podman |
|---------|--------|--------|
| Root privileges | Runs as root by default | Rootless by default |
| Daemon | Requires dockerd daemon | Daemonless |
| Security | Good with proper setup | Better default security |
| Compose support | Native | Via podman-compose |

### When to Use Which

**Use Docker when:**
- It's your team's standard
- You need Docker Desktop features
- You're using Docker-specific tooling

**Use Podman when:**
- Security is a top priority
- You can't/don't want to run a daemon
- You're in a restricted environment

## Troubleshooting

### Permission Issues

If you encounter permission issues with mounted volumes:

1. **For Podman**: Should work automatically with rootless mode
2. **For Docker**: Set your UID/GID in `docker/.env`:
   ```bash
   echo "UID=$(id -u)" >> docker/.env
   echo "GID=$(id -g)" >> docker/.env
   ```

### Socket Issues

If Podman can't find the Docker socket:

```bash
# Set the socket path in your .env
echo "DOCKER_SOCK=${XDG_RUNTIME_DIR}/podman/podman.sock" >> docker/.env
```

### Compose Command Not Found

For Podman, you need to install podman-compose:

```bash
# macOS
brew install podman-compose

# Linux
pip install podman-compose
```

### Podman Machine Not Running (macOS/Windows)

Podman needs a Linux VM to run containers. The Makefile will automatically start it, but you can also manage it manually:

```bash
# Initialize a new machine
podman machine init

# Start the machine
podman machine start

# Check machine status
podman machine list

# Stop the machine
podman machine stop
```

### Auto-Setup with Make

The project's Makefile handles most Podman setup automatically:

- Checks if Podman machine is running
- Starts it if needed
- Verifies podman-compose is installed
- Uses appropriate socket paths

Just run `make container-info` to see the current status.

## Compatibility with Project Initialization

The container setup is designed to work both before and after running `make init`:

### Before `make init`
- Source code is in `src/` directory
- Container mounts entire project as `/workspace`
- All development tools work normally

### After `make init` 
- Source code moves to your project module directory (e.g., `my_project/`)
- Container setup continues to work unchanged
- Volume mounts and dependencies remain intact

The `make init` command:
1. Renames `src/` to your project name
2. Updates import statements in tests
3. Modifies `pyproject.toml` and `Makefile`

**The Docker/Podman setup survives this transformation** because:
- The Dockerfile doesn't hardcode directory names
- Dependencies are installed from temporary copied files
- The entire project is mounted, regardless of internal structure

This means you can:
```bash
# Set up development environment
make dev-env

# Initialize your project later
make init

# Continue using the same development environment
make dev-env  # Still works!
```