# Repo gate for what runs from a shell. Unity is gated through UnityMCP, not here (D11).

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# Default: show the recipes.
default:
    @just --list

# The single check: everything that can run without the Unity bridge.
check: test-scripts
    @echo "just check: shell-side checks passed. NOT covered: Unity (compile, console, tests). Run skills/unity/unity-check through UnityMCP."

# Unit tests for the kit's Python scripts (pytest; about 70 s).
test-scripts:
    uv run --no-project --with pytest pytest scripts -q
