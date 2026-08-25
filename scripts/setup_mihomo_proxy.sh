#!/usr/bin/env bash
# 通过 mihomo 拉取订阅、启动本地代理并探测可用节点。
# 环境变量:
#   PROXY_SUBSCRIPTION_URL  订阅链接（必填才启用）
#   PROXY_TEST_URL          探测目标，默认 https://www.google.com/generate_204
#   PROXY_REQUIRED          true 时探测失败则退出 1
#   PROXY_PORT              本地 mixed-port，默认 7890

set -euo pipefail

if [[ -z "${PROXY_SUBSCRIPTION_URL:-}" ]]; then
	echo "[INFO] PROXY_SUBSCRIPTION_URL not set, skip proxy setup"
	exit 0
fi

PROXY_DIR="${RUNNER_TEMP:-/tmp}/checkin-proxy"
PROXY_PORT="${PROXY_PORT:-7890}"
PROXY_TEST_URL="${PROXY_TEST_URL:-https://www.google.com/generate_204}"
MIHOMO_VERSION="${MIHOMO_VERSION:-v1.19.0}"
PROXY_REQUIRED="${PROXY_REQUIRED:-false}"

mkdir -p "${PROXY_DIR}"
cd "${PROXY_DIR}"

echo "[INFO] Downloading mihomo ${MIHOMO_VERSION}..."
ARCHIVE="mihomo-linux-amd64-${MIHOMO_VERSION}.gz"
if ! curl --retry 3 --retry-delay 5 --retry-all-errors -fsSL -o "${ARCHIVE}" \
	"https://github.com/MetaCubeX/mihomo/releases/download/${MIHOMO_VERSION}/${ARCHIVE}"; then
	echo "[WARN] Failed to download mihomo ${MIHOMO_VERSION}, skip proxy setup"
	if [[ "${PROXY_REQUIRED}" == "true" ]]; then
		exit 1
	fi
	exit 0
fi
gunzip -f "${ARCHIVE}"
chmod +x "mihomo-linux-amd64-${MIHOMO_VERSION}"
MIHOMO_BIN="${PROXY_DIR}/mihomo-linux-amd64-${MIHOMO_VERSION}"

FILTER_CONFIG=""
if [[ -n "${PROXY_NODE_FILTER:-}" ]]; then
	FILTER_CONFIG="    filter: '${PROXY_NODE_FILTER}'"
fi

cat > config.yaml <<EOF
mixed-port: ${PROXY_PORT}
allow-lan: false
ipv6: false
mode: rule
log-level: warning
unified-delay: true
external-controller: 127.0.0.1:9100

proxy-providers:
  subscription:
    type: http
    url: "${PROXY_SUBSCRIPTION_URL}"
    interval: 3600
    path: ./subscription.yaml
    health-check:
      enable: true
      interval: 300
      url: https://www.gstatic.com/generate_204

proxy-groups:
  - name: CHECKIN
    type: url-test
    url: "${PROXY_TEST_URL}"
    interval: 3600
    tolerance: 150
    lazy: false
${FILTER_CONFIG}
    use:
      - subscription

rules:
  - MATCH,CHECKIN
EOF

echo "[INFO] Starting mihomo on 127.0.0.1:${PROXY_PORT}..."
nohup "${MIHOMO_BIN}" -d "${PROXY_DIR}" -f config.yaml > mihomo.log 2>&1 &
echo $! > mihomo.pid

PROXY_URL="http://127.0.0.1:${PROXY_PORT}"
READY=false
for attempt in $(seq 1 45); do
	if curl -fsS -x "${PROXY_URL}" --max-time 20 "${PROXY_TEST_URL}" -o /dev/null 2>/dev/null; then
		READY=true
		break
	fi
	echo "[INFO] Waiting for proxy health check (${attempt}/45)..."
	sleep 2
done

if [[ "${READY}" != "true" ]]; then
	echo "[FAILED] Proxy health check failed for ${PROXY_TEST_URL}"
	tail -n 30 mihomo.log || true
	if [[ -f mihomo.pid ]]; then
		kill "$(cat mihomo.pid)" 2>/dev/null || true
	fi
	if [[ "${PROXY_REQUIRED}" == "true" ]]; then
		exit 1
	fi
	exit 0
fi

echo "[SUCCESS] Proxy is ready: ${PROXY_URL}"
echo "[INFO] Proxy is scoped to CHECKIN_PROXY_URL (browser/python only, not global HTTP_PROXY)"

# 自动挑选能通过 AgentRouter WAF 的节点（机房 IP 会被滑块拦截，需逐个探测）
MIHOMO_API="http://127.0.0.1:9100"
PROBE_URL="${PROXY_PROBE_URL:-https://ps.air-outer.com/api/status}"
if [[ -z "${PROXY_NODE_FILTER:-}" ]]; then
	echo "[INFO] Probing subscription nodes against ${PROBE_URL} ..."
	NODES=$(curl -fsS --max-time 5 "${MIHOMO_API}/proxies/CHECKIN" 2>/dev/null \
		| python3 -c "import sys, json; print('\n'.join(json.load(sys.stdin).get('all') or []))" 2>/dev/null || true)
	TOTAL=$(grep -c . <<<"${NODES}" || true)
	echo "[INFO] Subscription provides ${TOTAL} node(s)"
	CHOSEN=""
	COUNT=0
	while IFS= read -r node; do
		[[ -z "${node}" ]] && continue
		COUNT=$((COUNT + 1))
		if (( COUNT > 30 )); then
			echo "[INFO] Probe limit reached (30 nodes)"
			break
		fi
		if ! curl -fsS --max-time 5 -X PUT -H 'Content-Type: application/json' \
			-d "{\"name\":\"${node}\"}" "${MIHOMO_API}/proxies/CHECKIN" >/dev/null 2>&1; then
			continue
		fi
		BODY=$(curl -fsS -x "${PROXY_URL}" --max-time 8 "${PROBE_URL}" 2>/dev/null || true)
		if [[ -n "${BODY}" ]] && ! grep -q 'aliyun_waf' <<<"${BODY}" && grep -q '"success":true' <<<"${BODY}"; then
			CHOSEN="${node}"
			echo "[SUCCESS] Selected node that bypasses AgentRouter WAF: ${node}"
			break
		fi
		echo "[INFO] Node ${COUNT}/${TOTAL} failed WAF probe: ${node}"
	done <<<"${NODES}"
	if [[ -z "${CHOSEN}" ]]; then
		echo "[WARN] No subscription node bypassed AgentRouter WAF; keeping default selection"
	fi
else
	echo "[INFO] PROXY_NODE_FILTER is set, skipping auto probe"
fi

# 诊断订阅是否真正加载成功（COMPATIBLE 单节点 = 订阅解析失败直连兜底）
SUB_CODE=$(curl -fsS -o /dev/null -w '%{http_code}' --max-time 20 "${PROXY_SUBSCRIPTION_URL}" 2>/dev/null || echo 'ERR')
echo "[INFO] Subscription URL HTTP status (direct): ${SUB_CODE}"
PROVIDER_INFO=$(curl -fsS --max-time 5 "${MIHOMO_API}/providers/proxies/subscription" 2>/dev/null \
	| python3 -c "import sys, json; d = json.load(sys.stdin); print(d.get('vehicleType'), 'count =', len(d.get('proxies') or []))" 2>/dev/null || true)
echo "[INFO] Provider 'subscription': ${PROVIDER_INFO:-unavailable}"
if [[ -f mihomo.log ]]; then
	grep -iE 'error|fail|panic' mihomo.log | head -5 | sed "s#${PROXY_SUBSCRIPTION_URL}#***#g" || true
fi

# 打印出口 IP 归属（判断是否家宽），便于人工核对
if EGRESS=$(curl -fsS -x "${PROXY_URL}" --max-time 15 "https://ipinfo.io/json" 2>/dev/null); then
	echo "[INFO] Proxy egress info: ${EGRESS}"
else
	echo "[WARN] Failed to fetch proxy egress info"
fi

if [[ -n "${GITHUB_ENV:-}" ]]; then
	echo "CHECKIN_PROXY_URL=${PROXY_URL}" >> "${GITHUB_ENV}"
fi
