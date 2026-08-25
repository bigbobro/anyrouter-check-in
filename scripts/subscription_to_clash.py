#!/usr/bin/env python3
"""把 base64 / 分享链接格式的订阅内容转换为 Clash proxies YAML。

mihomo 的 http proxy-provider 无法解析部分机场下发的 base64 分享链接
（报 "file must have a `proxies` field"），需要在写入 mihomo 配置前自行转换。

用法: subscription_to_clash.py <订阅原始文件> > subscription.yaml
"""

from __future__ import annotations

import base64
import json
import re
import sys
from collections import Counter
from urllib.parse import parse_qs, unquote, urlparse


def b64decode(data: str) -> bytes:
	"""兼容 URL-safe、换行与缺失 padding 的 base64。"""
	data = ''.join(data.split()).replace('-', '+').replace('_', '/')
	return base64.b64decode(data + '=' * (-len(data) % 4), validate=True)


def parse_ss(line: str) -> dict:
	rest = line[len('ss://') :]
	name = ''
	if '#' in rest:
		rest, frag = rest.rsplit('#', 1)
		name = unquote(frag)
	rest = rest.split('?')[0].rstrip('/')
	if '@' in rest:
		userinfo_b64, server = rest.rsplit('@', 1)
		userinfo = b64decode(userinfo_b64).decode('utf-8', errors='replace')
	else:
		decoded = b64decode(rest).decode('utf-8', errors='replace')
		userinfo, server = decoded.rsplit('@', 1)
	method, password = userinfo.split(':', 1)
	host, port = server.rsplit(':', 1)
	return {
		'name': name or host,
		'type': 'ss',
		'server': host,
		'port': int(port),
		'cipher': method,
		'password': password,
	}


def parse_vmess(line: str) -> dict:
	data = json.loads(b64decode(line[len('vmess://') :]).decode('utf-8', errors='replace'))
	proxy = {
		'name': data.get('ps') or data.get('add'),
		'type': 'vmess',
		'server': data['add'],
		'port': int(data['port']),
		'uuid': data['id'],
		'alterId': int(data.get('aid') or 0),
		'cipher': 'auto',
	}
	tls = data.get('tls')
	if tls and tls != 'none':
		proxy['tls'] = True
		servername = data.get('sni') or data.get('host')
		if servername:
			proxy['servername'] = servername
	network = data.get('net')
	if network:
		proxy['network'] = network
	if network == 'ws':
		ws_opts: dict = {}
		if data.get('path'):
			ws_opts['path'] = data['path']
		if data.get('host'):
			ws_opts['headers'] = {'Host': data['host']}
		if ws_opts:
			proxy['ws-opts'] = ws_opts
	return proxy


def parse_vless(line: str) -> dict:
	url = urlparse(line)
	query = parse_qs(url.query)
	proxy = {
		'name': unquote(url.fragment) or url.hostname,
		'type': 'vless',
		'server': url.hostname,
		'port': url.port,
		'uuid': url.username,
		'udp': True,
	}
	security = query.get('security', [''])[0]
	if security in ('tls', 'reality'):
		proxy['tls'] = True
	if query.get('sni'):
		proxy['servername'] = query['sni'][0]
	network = query.get('type', [''])[0]
	if network:
		proxy['network'] = network
	if network == 'ws':
		ws_opts = {}
		if query.get('path'):
			ws_opts['path'] = query['path'][0]
		if query.get('host'):
			ws_opts['headers'] = {'Host': query['host'][0]}
		if ws_opts:
			proxy['ws-opts'] = ws_opts
	if query.get('flow'):
		proxy['flow'] = query['flow'][0]
	return proxy


def parse_trojan(line: str) -> dict:
	url = urlparse(line)
	query = parse_qs(url.query)
	proxy = {
		'name': unquote(url.fragment) or url.hostname,
		'type': 'trojan',
		'server': url.hostname,
		'port': url.port,
		'password': unquote(url.username or ''),
	}
	if query.get('sni'):
		proxy['sni'] = query['sni'][0]
	if query.get('allowInsecure', ['0'])[0] in ('1', 'true'):
		proxy['skip-cert-verify'] = True
	return proxy


def parse_hysteria2(line: str) -> dict:
	line = line.replace('hy2://', 'hysteria2://', 1)
	url = urlparse(line)
	query = parse_qs(url.query)
	proxy = {
		'name': unquote(url.fragment) or url.hostname,
		'type': 'hysteria2',
		'server': url.hostname,
		'port': url.port,
		'password': unquote(url.username or ''),
	}
	if query.get('sni'):
		proxy['sni'] = query['sni'][0]
	if query.get('insecure', ['0'])[0] in ('1', 'true'):
		proxy['skip-cert-verify'] = True
	return proxy


PARSERS = {
	'ss': parse_ss,
	'vmess': parse_vmess,
	'vless': parse_vless,
	'trojan': parse_trojan,
	'hy2': parse_hysteria2,
	'hysteria2': parse_hysteria2,
}

CLASH_PROXIES_RE = re.compile(r'(?m)^[ \t]*proxies[ \t]*:')


def decode_subscription(raw: str) -> str:
	"""解码可能包裹了一层 base64 的订阅正文。"""
	text = raw.strip().lstrip('\ufeff')
	if '://' in text or CLASH_PROXIES_RE.search(text):
		return text
	return b64decode(text).decode('utf-8').lstrip('\ufeff')


def content_summary(text: str) -> str:
	"""返回不含订阅正文、节点或凭据的格式摘要。"""
	stripped = text.strip().lstrip('\ufeff')
	lower = stripped.lower()
	if not stripped:
		kind = 'empty'
	elif stripped.startswith('<'):
		kind = 'html'
	elif stripped.startswith(('{', '[')):
		kind = 'json'
	elif CLASH_PROXIES_RE.search(stripped):
		kind = 'clash-yaml'
	elif '[proxy]' in lower:
		kind = 'surge-config'
	elif any(marker in lower for marker in ('unauthorized', 'forbidden', 'invalid', 'expired', 'not found')):
		kind = 'error-text'
	else:
		kind = 'text'
	return f'kind={kind}, chars={len(stripped)}, lines={len(stripped.splitlines())}'


def _convert_text(text: str) -> list[dict]:
	"""转换已解码的分享链接文本。"""
	proxies = []
	errors = 0
	unsupported: Counter[str] = Counter()
	for line in text.splitlines():
		line = line.strip()
		if not line or '://' not in line:
			continue
		scheme = line.split('://', 1)[0].lower()
		parser = PARSERS.get(scheme)
		if parser is None:
			if re.fullmatch(r'[a-z][a-z0-9+.-]{0,31}', scheme):
				unsupported[scheme] += 1
			continue
		try:
			proxies.append(parser(line))
		except Exception:
			errors += 1
	if unsupported:
		details = ', '.join(f'{scheme}={count}' for scheme, count in sorted(unsupported.items())[:8])
		print(f'[WARN] subscription_to_clash: unsupported schemes: {details}', file=sys.stderr)
	if errors:
		print(f'[WARN] subscription_to_clash: skipped {errors} unparseable link(s)', file=sys.stderr)
	if not proxies and not unsupported and not errors:
		print(f'[WARN] subscription_to_clash: no share-link schemes found ({content_summary(text)})', file=sys.stderr)
	return proxies


def convert(raw: str) -> list[dict]:
	"""把订阅原文转换为 Clash proxy 列表，无法识别的行跳过。"""
	try:
		text = decode_subscription(raw)
	except Exception:
		print(
			f'[WARN] subscription_to_clash: content is neither share links nor base64 ({content_summary(raw)})',
			file=sys.stderr,
		)
		return []
	return _convert_text(text)


def emit_yaml(proxies: list[dict]) -> str:
	"""输出 block 风格 YAML（字符串用 JSON 双引号转义，兼容 YAML 1.2）。"""
	lines = ['proxies:']
	for proxy in proxies:
		items = list(proxy.items())
		for i, (key, value) in enumerate(items):
			prefix = '  - ' if i == 0 else '    '
			lines.append(f'{prefix}{key}: {json.dumps(value, ensure_ascii=False)}')
	return '\n'.join(lines) + '\n'


def to_clash_yaml(raw: str) -> str | None:
	"""输出可供 mihomo 使用的 Clash YAML，已有配置则保留原文。"""
	try:
		text = decode_subscription(raw)
	except Exception:
		print(
			f'[WARN] subscription_to_clash: content is neither share links nor base64 ({content_summary(raw)})',
			file=sys.stderr,
		)
		return None
	if CLASH_PROXIES_RE.search(text):
		return text.rstrip() + '\n'
	proxies = _convert_text(text)
	return emit_yaml(proxies) if proxies else None


def main() -> int:
	if len(sys.argv) != 2:
		print('usage: subscription_to_clash.py <raw subscription file>', file=sys.stderr)
		return 2
	with open(sys.argv[1], encoding='utf-8', errors='replace') as f:
		raw = f.read()
	yaml_text = to_clash_yaml(raw)
	if yaml_text is None:
		print('[WARN] subscription_to_clash: no proxies parsed', file=sys.stderr)
		return 1
	print(yaml_text, end='')
	return 0


if __name__ == '__main__':
	sys.exit(main())
