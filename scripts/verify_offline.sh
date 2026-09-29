#!/usr/bin/env bash
# verify_offline.sh — run from inside the backend container to confirm INV-11.
#
# Checks:
#   1. DNS lookups for public hosts must fail.
#   2. TCP connects to public addresses must fail (using /dev/tcp).
#   3. Application health endpoint must pass.
#
# Writes a result file: /tmp/verify_offline_result.json
# Exit 0 = all checks pass. Exit 1 = any check failed.

set -euo pipefail

RESULT_FILE="${OFFLINE_VERIFY_OUT:-/tmp/verify_offline_result.json}"
HEALTH_URL="${PRAMANA_HEALTH_URL:-http://localhost:8000/health}"

pass() { echo "[PASS] $*"; }
fail() { echo "[FAIL] $*" >&2; }

DNS_OK=true
TCP_OK=true
HEALTH_OK=true

# ── 1. DNS must fail ──────────────────────────────────────────────────────────
PUBLIC_HOSTS=("google.com" "pypi.org" "huggingface.co" "ollama.ai")
for host in "${PUBLIC_HOSTS[@]}"; do
    if python3 -c "import socket; socket.getaddrinfo('${host}', 80)" 2>/dev/null; then
        fail "DNS resolved ${host} — network is NOT isolated!"
        DNS_OK=false
    else
        pass "DNS blocked for ${host}"
    fi
done

# ── 2. TCP connect must fail ──────────────────────────────────────────────────
PUBLIC_ADDRS=("8.8.8.8:53" "1.1.1.1:443" "151.101.1.63:443")
for addr in "${PUBLIC_ADDRS[@]}"; do
    host="${addr%%:*}"
    port="${addr##*:}"
    if python3 -c "
import socket, sys
try:
    s = socket.create_connection(('${host}', ${port}), timeout=3)
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        fail "TCP connected to ${addr} — network is NOT isolated!"
        TCP_OK=false
    else
        pass "TCP blocked for ${addr}"
    fi
done

# ── 3. App health must pass ───────────────────────────────────────────────────
if python3 -c "
import urllib.request, sys
try:
    r = urllib.request.urlopen('${HEALTH_URL}', timeout=10)
    sys.exit(0 if r.status == 200 else 1)
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)
" 2>&1; then
    pass "App health OK at ${HEALTH_URL}"
else
    fail "App health FAILED at ${HEALTH_URL}"
    HEALTH_OK=false
fi

# ── Write result ──────────────────────────────────────────────────────────────
python3 - <<PYEOF
import json, datetime

result = {
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "dns_blocked": ${DNS_OK},
    "tcp_blocked": ${TCP_OK},
    "health_ok": ${HEALTH_OK},
    "overall": ${DNS_OK} and ${TCP_OK} and ${HEALTH_OK},
}
with open("${RESULT_FILE}", "w") as f:
    json.dump(result, f, indent=2)
print(f"Result written to ${RESULT_FILE}")
print(json.dumps(result, indent=2))
PYEOF

if [[ "$DNS_OK" == "true" && "$TCP_OK" == "true" && "$HEALTH_OK" == "true" ]]; then
    echo ""
    echo "✓ All offline checks passed."
    exit 0
else
    echo ""
    echo "✗ One or more offline checks FAILED. See above." >&2
    exit 1
fi
