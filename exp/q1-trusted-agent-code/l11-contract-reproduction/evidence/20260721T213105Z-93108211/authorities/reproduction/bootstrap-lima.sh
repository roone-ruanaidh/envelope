#!/bin/sh
set -eu

# Run inside q1-l1-evaluator. apt-packages.txt is the single package-version authority.
sudo systemctl mask --now \
  apt-daily.service \
  apt-daily.timer \
  apt-daily-upgrade.service \
  apt-daily-upgrade.timer \
  unattended-upgrades.service
sudo apt-get update
xargs sudo env DEBIAN_FRONTEND=noninteractive \
  apt-get install --yes --no-install-recommends < reproduction/apt-packages.txt
