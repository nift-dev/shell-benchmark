#!/bin/bash
set -euo pipefail
# Execute only on the disposable Ubuntu 24.04 benchmark node, as root.
ROOT=/opt/campaign
TOOLS=$ROOT/tools
mkdir -p "$TOOLS/bin" "$TOOLS/downloads"
export DEBIAN_FRONTEND=noninteractive
systemctl stop apt-daily.timer apt-daily-upgrade.timer unattended-upgrades || true
apt-get -o DPkg::Lock::Timeout=180 update -qq
apt-get -o DPkg::Lock::Timeout=180 install -y -qq build-essential git curl xz-utils python3 ruby lua5.4 luajit bash zsh ca-certificates
systemctl stop apt-daily.timer apt-daily-upgrade.timer unattended-upgrades || true
cd "$TOOLS/downloads"
fetch() { curl -fL --retry 3 --max-time 300 "$1" -o "$2"; }
fetch https://nodejs.org/dist/v24.21.0/node-v24.21.0-linux-x64.tar.xz node.tar.xz
fetch https://nodejs.org/dist/v24.21.0/SHASUMS256.txt node-checksums.txt
node_sum=$(awk '$2=="node-v24.21.0-linux-x64.tar.xz" {print $1}' node-checksums.txt)
printf '%s  node.tar.xz\n' "$node_sum" | sha256sum -c -
tar -xf node.tar.xz -C "$TOOLS"
ln -sf "$TOOLS/node-v24.21.0-linux-x64/bin/node" "$TOOLS/bin/node"
ln -sf "$TOOLS/node-v24.21.0-linux-x64/bin/npm" "$TOOLS/bin/npm"
fetch https://github.com/nushell/nushell/releases/download/0.116.1/nu-0.116.1-x86_64-unknown-linux-gnu.tar.gz nu.tar.gz
printf 'd6d8ace4be491ed8abba4026e73b60c0470b4671d7039307e7d772282ef863da  nu.tar.gz\n' | sha256sum -c -
tar -xf nu.tar.gz -C "$TOOLS"
ln -sf "$TOOLS/nu-0.116.1-x86_64-unknown-linux-gnu/nu" "$TOOLS/bin/nu"
fetch https://github.com/fish-shell/fish-shell/releases/download/4.9.3/fish-4.9.3-linux-x86_64.tar.xz fish.tar.xz
printf '8f643d10ad1abb0ef7072764c01ceb5cf61b2d373fda400cf60f0bad69b7e095  fish.tar.xz\n' | sha256sum -c -
mkdir -p "$TOOLS/fish"; tar -xf fish.tar.xz -C "$TOOLS/fish"
ln -sf "$TOOLS/fish/fish" "$TOOLS/bin/fish"
NIFT_VERSION=4.7.2 NIFT_INSTALL_DIR="$TOOLS/bin" sh "$ROOT/nift-installer.sh"
fetch https://github.com/gohugoio/hugo/releases/download/v0.167.0/hugo_0.167.0_linux-amd64.tar.gz hugo.tar.gz
fetch https://github.com/gohugoio/hugo/releases/download/v0.167.0/hugo_0.167.0_checksums.txt hugo-checksums.txt
hugo_sum=$(awk '$2=="hugo_0.167.0_linux-amd64.tar.gz" {print $1}' hugo-checksums.txt)
printf '%s  hugo.tar.gz\n' "$hugo_sum" | sha256sum -c -
tar -xf hugo.tar.gz -C "$TOOLS/bin" hugo
export PATH="$TOOLS/bin:/usr/local/bin:/usr/bin:/bin"
cd "$ROOT/website-generator-benchmark"
npm ci --ignore-scripts --no-audit --no-fund
mkdir -p "$ROOT/evidence"
dpkg-query -W -f='${Package}\t${Version}\n' > "$ROOT/evidence/dpkg-versions.tsv"
sha256sum "$ROOT/nift-installer.sh" "$TOOLS/downloads/"*.tar.* > "$ROOT/evidence/download-sha256.txt"
cc --version > "$ROOT/evidence/compiler.txt"
