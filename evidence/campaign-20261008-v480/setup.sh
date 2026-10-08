#!/bin/bash
set -euo pipefail
suite=$1
export DEBIAN_FRONTEND=noninteractive
systemctl stop apt-daily.timer apt-daily-upgrade.timer unattended-upgrades || true
apt-get -o DPkg::Lock::Timeout=180 update -qq
apt-get -o DPkg::Lock::Timeout=180 install -y -qq build-essential autoconf automake libtool git curl xz-utils ca-certificates python3 ruby lua5.4 luajit bash zsh > /tmp/benchmark-packages.log
systemctl stop apt-daily.timer apt-daily-upgrade.timer unattended-upgrades || true
mkdir -p /opt/campaign/tools/bin /opt/campaign/tools/downloads /opt/campaign/evidence
for repo in nift "$suite"-benchmark; do
 mkdir /opt/campaign/"$repo"
 git -C /opt/campaign/"$repo" init -q
 bundle=nift; if [ "$repo" != nift ]; then bundle=$suite; fi
 git -C /opt/campaign/"$repo" fetch -q /tmp/"$bundle".bundle HEAD
 git -C /opt/campaign/"$repo" checkout -q --detach FETCH_HEAD
done
cd /opt/campaign/nift
make -j2 > /tmp/nift-build.log 2>&1
make install PREFIX=/opt/campaign/tools > /tmp/nift-install.log 2>&1
/opt/campaign/tools/bin/nift version
git rev-parse HEAD > /opt/campaign/evidence/nift-revision.txt
sha256sum /opt/campaign/tools/bin/nift > /opt/campaign/evidence/nift-binary.sha256
cd /opt/campaign/tools/downloads
if [ "$suite" = shell ]; then
 curl -fL --retry 3 --max-time 300 https://github.com/nushell/nushell/releases/download/0.116.1/nu-0.116.1-x86_64-unknown-linux-gnu.tar.gz -o nu.tar.gz
 printf 'd6d8ace4be491ed8abba4026e73b60c0470b4671d7039307e7d772282ef863da  nu.tar.gz\n' | sha256sum -c -
 tar -xf nu.tar.gz -C /opt/campaign/tools
 ln -s /opt/campaign/tools/nu-0.116.1-x86_64-unknown-linux-gnu/nu /opt/campaign/tools/bin/nu
 curl -fL --retry 3 --max-time 300 https://github.com/fish-shell/fish-shell/releases/download/4.9.3/fish-4.9.3-linux-x86_64.tar.xz -o fish.tar.xz
 printf '8f643d10ad1abb0ef7072764c01ceb5cf61b2d373fda400cf60f0bad69b7e095  fish.tar.xz\n' | sha256sum -c -
 mkdir /opt/campaign/tools/fish;tar -xf fish.tar.xz -C /opt/campaign/tools/fish
 ln -s /opt/campaign/tools/fish/fish /opt/campaign/tools/bin/fish
else
 curl -fL --retry 3 --max-time 300 https://nodejs.org/dist/v24.21.0/node-v24.21.0-linux-x64.tar.xz -o node.tar.xz
 curl -fL --retry 3 --max-time 300 https://nodejs.org/dist/v24.21.0/SHASUMS256.txt -o node-checksums.txt
 node_sum=$(awk '$2=="node-v24.21.0-linux-x64.tar.xz" {print $1}' node-checksums.txt)
 printf '%s  node.tar.xz\n' "$node_sum" | sha256sum -c -
 tar -xf node.tar.xz -C /opt/campaign/tools
 ln -s /opt/campaign/tools/node-v24.21.0-linux-x64/bin/node /opt/campaign/tools/bin/node
fi
export PATH=/opt/campaign/tools/bin:/usr/local/bin:/usr/bin:/bin
cd /opt/campaign/"$suite"-benchmark
python3 scripts/test_measurement.py
cc --version > /opt/campaign/evidence/compiler.txt
dpkg-query -W -f='${Package}\t${Version}\n' > /opt/campaign/evidence/dpkg-versions.tsv
findmnt -J / > /opt/campaign/evidence/filesystem.json
lsblk -J > /opt/campaign/evidence/storage.json
python3 - <<'PY'
import json,pathlib,os,subprocess
out={}
for root in ('/sys/devices/system/cpu/cpu0/cpufreq','/sys/fs/cgroup'):
 p=pathlib.Path(root);out[root]={n:(p/n).read_text().strip() for n in ('scaling_governor','scaling_min_freq','scaling_max_freq','scaling_cur_freq','cpu.max','cpu.stat','memory.max') if (p/n).is_file()}
out['affinity']=sorted(os.sched_getaffinity(0));out['utc']=subprocess.check_output(['date','-u','+%FT%TZ'],text=True).strip()
pathlib.Path('/opt/campaign/evidence/machine-extra.json').write_text(json.dumps(out,indent=2)+'\n')
files=[]
for parent in ('/etc/zsh','/etc/fish'):
 p=pathlib.Path(parent)
 if p.exists():files+=list(p.rglob('*'))
files += [pathlib.Path('/etc/profile'),pathlib.Path('/etc/bash.bashrc')]
import hashlib
pathlib.Path('/opt/campaign/evidence/system-startup-files.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},indent=2)+'\n')
PY
printf 'SETUP_PASS\n'
