#!/bin/sh
set -eu

setup_dir=${1:-/tmp/q1-l1-candidate-setup}
candidate_root=${HOME}/candidate

test ! -e "${candidate_root}"

sudo apt-get update
xargs sudo env DEBIAN_FRONTEND=noninteractive \
  apt-get install --yes --no-install-recommends < "${setup_dir}/candidate-apt-packages.txt"
sudo npm install --global @openai/codex@0.144.6
test "$(codex --version)" = "codex-cli 0.144.6"

sudo install -d -m 0755 /etc/codex
sudo install -m 0644 "${setup_dir}/candidate-codex-config.toml" /etc/codex/config.toml
sudo install -m 0644 \
  "${setup_dir}/candidate-codex-requirements.toml" \
  /etc/codex/requirements.toml
sudo install -m 0644 \
  "${setup_dir}/agent-completion.schema.json" \
  /etc/codex/q1-l1-agent-completion.schema.json
sudo install -d -m 0755 /usr/local/lib/q1-l1
sudo install -m 0644 \
  "${setup_dir}/candidate_transfer.py" \
  /usr/local/lib/q1-l1/candidate_transfer.py
sudo install -m 0644 \
  "${setup_dir}/candidate_snapshot.py" \
  /usr/local/lib/q1-l1/candidate_snapshot.py

mkdir -p "${candidate_root}/public"
cp -R "${setup_dir}/public/contract" "${candidate_root}/public/contract"
python3.14 -m venv "${candidate_root}/.venv"
"${candidate_root}/.venv/bin/python" -m pip install \
  --disable-pip-version-check \
  --no-deps \
  --requirement "${candidate_root}/public/contract/python-arm-requirements.v1.txt"
"${candidate_root}/.venv/bin/python" -m pip check

git -C "${candidate_root}" init --initial-branch=main
mkdir "${candidate_root}/.codex"
mkdir -p "${HOME}/.codex"
printf '%s\n' sealed > "${HOME}/.codex/auth-boundary-sentinel"
mkdir -p "${HOME}/outside-control"
printf '%s\n' sealed > "${HOME}/outside-control/secret.txt"
cp "${setup_dir}/candidate_boundary_probe.py" "${candidate_root}/.boundary_probe.py"

sudo chown -R root:root \
  "${candidate_root}/.git" \
  "${candidate_root}/.codex" \
  "${candidate_root}/.venv" \
  "${candidate_root}/public/contract"
sudo chmod -R a-w \
  "${candidate_root}/.git" \
  "${candidate_root}/.codex" \
  "${candidate_root}/.venv" \
  "${candidate_root}/public/contract"
