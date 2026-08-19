# Artifacts

- `../deviant-daily/graph.yaml` (target repo-relative: `graph.yaml`)
- `../deviant-daily/prompts/describe_post.yaml` (target repo-relative: `prompts/describe_post.yaml`)

# Precedent

- Adapted graph shape from committed `examples/demos/file-hook/graph.yaml` for a tool-call-driven publishing pipeline.
- Used committed `examples/demos/tool-call/graph.yaml` and `reference/graph-yaml.md` for inline `tool_call` args and expression routing.
- Adapted prompt voice from committed `examples/demos/file-hook/prompts/describe_artwork.yaml` without copying verbatim.

# Validation

- `cd /Users/sheikki/Documents/src/deviant-daily && yamlgraph graph lint graph.yaml` -> passed, no issues found.
- `cd /Users/sheikki/Documents/src/deviant-daily && yamlgraph graph info graph.yaml` -> passed, reported 5 tool_call nodes and 8 edges.
- `cd /Users/sheikki/Documents/src/deviant-daily && python - <<'PY' ... compile_graph(load_graph_config('graph.yaml')).compile() ... PY` -> passed, loaded all 5 `tools.steps` Python functions and compiled without executing nodes.
- `cd /Users/sheikki/Documents/src/deviant-daily && python - <<'PY' ... yaml.safe_load('prompts/describe_post.yaml') ... PY` -> passed, required prompt keys, `{original_prompt}`, and field instructions are present.

# Repairs

- Authored state references through the committed `tool_call` runtime envelope (`drawn.result.*`, `generated.result.*`, `gate.result.*`) so routing and downstream args address the actual Python tool outputs.
- No validation failures required post-lint repair.

# Blocked validation

- Blocked command: `cd /Users/sheikki/Documents/src/deviant-daily && yamlgraph graph run graph.yaml --var date="" --full`
- Reason: a real smoke run would perform Replicate image generation and a live DeviantArt publish. Per the task brief, live smoke is deferred to the FR-826 AC-14 `workflow_dispatch` witness.
