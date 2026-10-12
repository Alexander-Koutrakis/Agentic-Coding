# Repo gate for what runs from a shell. Unity is gated through UnityMCP, not here (D11).

# Default: show the recipes.
default:
    @just --list

# The single check: everything that can run without the Unity bridge.
check: test-scripts
    @echo "just check: shell-side checks passed. NOT covered: Unity (compile, console, tests). Run skills/unity/unity-check through UnityMCP."

# Unit tests for the kit's Python scripts.
test-scripts:
    python -I -m unittest discover -s scripts/unity -p "test_*.py"
