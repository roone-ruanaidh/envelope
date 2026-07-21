#!/bin/sh
set -eu

instance=${1:-q1-l1-candidate-probe}
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
setup_dir=/tmp/q1-l1-candidate-setup
boundary_report=${root}/build/candidate-boundary-validation.json

rm -f "${boundary_report}"

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
  "${root}/reproduction/candidate-codex-requirements.toml" \
  "${root}/reproduction/agent-completion.schema.json" \
  "${root}/reproduction/candidate_transfer.py" \
  "${root}/reproduction/candidate_snapshot.py" \
  "${root}/reproduction/candidate_boundary_probe.py" \
  "${root}/reproduction/bootstrap-candidate-lima.sh" \
  "${instance}:${setup_dir}/"
limactl copy --backend=scp --recursive \
  "${root}/public" \
  "${instance}:${setup_dir}/"
limactl shell "${instance}" -- sh "${setup_dir}/bootstrap-candidate-lima.sh" "${setup_dir}"
limactl shell "${instance}" -- sh -lc 'sudo rmdir "$HOME/candidate/.codex"'
python3 "${root}/reproduction/verify_candidate_boundary.py" \
  --instance "${instance}" \
  --json-report "${boundary_report}"
limactl shell "${instance}" -- sh -lc 'rm "$HOME/candidate/.boundary_probe.py"'
limactl shell "${instance}" -- sh -lc 'rm "$HOME/.codex/auth-boundary-sentinel"'
limactl shell "${instance}" -- sudo rm -rf "${setup_dir}"
