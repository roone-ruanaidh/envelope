#!/bin/sh
set -eu

instance=${1:-e1-agent-probe}
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
setup_dir=/tmp/e1-setup

if limactl list --json "${instance}" >/dev/null 2>&1; then
  echo "Lima instance already exists: ${instance}" >&2
  exit 2
fi

limactl create --name "${instance}" --tty=false "${root}/reproduction/candidate-lima.yaml"
limactl start "${instance}"
limactl shell "${instance}" -- mkdir -m 0700 "${setup_dir}"
limactl copy --backend=scp \
  "${root}/reproduction/candidate-apt-packages.txt" \
  "${root}/reproduction/candidate-codex-config.toml" \
  "${root}/reproduction/candidate_boundary_probe.py" \
  "${root}/reproduction/bootstrap-candidate-lima.sh" \
  "${instance}:${setup_dir}/"
limactl copy --backend=scp --recursive \
  "${root}/public" \
  "${instance}:${setup_dir}/"
limactl shell "${instance}" -- sh "${setup_dir}/bootstrap-candidate-lima.sh" "${setup_dir}"
limactl shell "${instance}" -- sh -lc \
  'cd "$HOME/candidate" && codex sandbox --permissions-profile e1 -- python3 .boundary_probe.py'
limactl shell "${instance}" -- sh -lc 'rm "$HOME/candidate/.boundary_probe.py"'
limactl shell "${instance}" -- sudo rm -rf "${setup_dir}"
limactl shell "${instance}" -- sh -lc 'find "$HOME/candidate" -maxdepth 3 -mindepth 1 -print'
