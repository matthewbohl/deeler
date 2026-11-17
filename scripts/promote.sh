#!/bin/bash
set -euo pipefail
image="ghcr.io/${GITHUB_REPOSITORY_OWNER,,}/deeler"
release_tag="$image:release-$RELEASE_ID"
sources=()
for arch in amd64 arm64; do
    ref=$(cat "digests/$arch.txt")
    [[ "$ref" =~ ^ghcr\.io/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$ ]]
    sources+=("$ref")
done
# Assemble the exact digests that passed on native hardware; never rebuild here.
docker buildx imagetools create -t "$release_tag" "${sources[@]}"
docker buildx imagetools inspect --raw "$release_tag" > /tmp/release-index.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/release-index.json'))
actual={(m['platform']['os'],m['platform']['architecture']) for m in d['manifests']}
assert {('linux','amd64'),('linux','arm64')} <= actual, 'Missing tested platform'
PY
digest=$(docker buildx imagetools inspect "$release_tag" --format '{{json .Manifest}}' | jq -er '.digest')
[[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]]
export DEELER_RELEASE_IMAGE="$image@$digest"
python3 - <<'PY'
import json, os
from pathlib import Path
record={'image':os.environ['DEELER_RELEASE_IMAGE'],'release':os.environ['RELEASE_ID'],
        'source_sha':os.environ['GITHUB_SHA'],'native_platforms':['linux/amd64','linux/arm64'],
        'authenticated_canaries':os.environ['CANARY_RESULT']}
Path('release/release.json').write_text(json.dumps(record,indent=2)+'\n')
PY
python3 scripts/privacy_check.py
if [[ -n "${PREVIOUS_IMAGE:-}" ]]; then
    docker buildx imagetools create -t "$image:previous" "$PREVIOUS_IMAGE"
fi
# Move the deployment alias last. Runtime containers are never restarted here.
docker buildx imagetools create -t "$image:latest" "$DEELER_RELEASE_IMAGE"
