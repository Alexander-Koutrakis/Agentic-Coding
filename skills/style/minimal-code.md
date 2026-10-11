# Minimal code (the Ponytail ladder)

Adapted from github.com/dietrichgebert/ponytail (idea only, plugin not installed). Loaded by: Director, both coders, reviewers.

Stop at the first rung that solves the problem:
1. Does it need to exist? If the brief or card does not need it, do not write it.
2. Does the codebase already have it? Reuse.
3. Does the C# or HLSL standard library have it?
4. Does Unity or URP provide it?
5. Does an installed package provide it?
6. Can it be one line?
7. Only then write the minimum that works, and one small test if the logic is risky.

Never cut: input validation in `Create`, error handling, resource release, security.
Priority: the plan and the style guides decide the structure (`CreateInfo`, data structs, ownership). This ladder decides how much code goes inside it. It never removes a structure the style guide requires.
Do not re-decide scope: if rung 1 says a task is not needed, tell the Director, do not skip it silently.
