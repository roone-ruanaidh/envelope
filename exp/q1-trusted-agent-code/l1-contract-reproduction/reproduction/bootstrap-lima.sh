#!/bin/sh
set -eu

# Run inside ct-ev. apt-packages.txt is the single package-version authority.
sudo apt-get update
xargs sudo env DEBIAN_FRONTEND=noninteractive \
  apt-get install --yes --no-install-recommends < reproduction/apt-packages.txt
