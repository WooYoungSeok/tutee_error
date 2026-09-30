#!/usr/bin/env bash
# Stop the vLLM servers started by launch_servers.sh / launch_eval_servers.sh (from newman_experiment/).
cd "$(dirname "$0")/.."
for name in rollout verifier_a verifier_b; do
  if [ -f "logs/$name.pid" ]; then
    pid=$(cat "logs/$name.pid")
    if kill -0 "$pid" 2> /dev/null; then kill "$pid" && echo "stopped $name ($pid)"; fi
    rm -f "logs/$name.pid"
  fi
done
