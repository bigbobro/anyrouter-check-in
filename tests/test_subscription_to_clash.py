import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from subscription_to_clash import convert, emit_yaml, to_clash_yaml


def test_parse_ss_sip002_link():
	link = 'ss://YWVzLTEyOC1nY206cGFzc3dvcmQ@1.2.3.4:8388#hk-node'
	proxies = convert(link)

	assert proxies == [
		{
			'name': 'hk-node',
			'type': 'ss',
			'server': '1.2.3.4',
			'port': 8388,
			'cipher': 'aes-128-gcm',
			'password': 'password',
		}
	]


def test_parse_ss_legacy_fully_base64_link():
	raw = base64.b64encode(b'aes-256-gcm:secret@5.6.7.8:443').decode()
	proxies = convert(f'ss://{raw}#legacy')

	assert proxies[0]['cipher'] == 'aes-256-gcm'
	assert proxies[0]['password'] == 'secret'
	assert proxies[0]['server'] == '5.6.7.8'
	assert proxies[0]['port'] == 443


def test_parse_vmess_ws_tls_link():
	payload = base64.b64encode(
		json.dumps(
			{
				'ps': 'vmess-node',
				'add': 'vm.example.com',
				'port': '443',
				'id': 'b831381d-6324-4d53-ad4f-8cda48b30811',
				'aid': '0',
				'net': 'ws',
				'tls': 'tls',
				'host': 'cdn.example.com',
				'path': '/ray',
			}
		).encode()
	).decode()
	proxies = convert(f'vmess://{payload}')

	proxy = proxies[0]
	assert proxy['name'] == 'vmess-node'
	assert proxy['type'] == 'vmess'
	assert proxy['tls'] is True
	assert proxy['servername'] == 'cdn.example.com'
	assert proxy['network'] == 'ws'
	assert proxy['ws-opts'] == {'path': '/ray', 'headers': {'Host': 'cdn.example.com'}}


def test_parse_vless_link():
	link = 'vless://b831381d-6324-4d53-ad4f-8cda48b30811@vl.example.com:443?security=tls&sni=vl.example.com&type=ws&path=%2Fchat#vless-node'
	proxies = convert(link)

	proxy = proxies[0]
	assert proxy['name'] == 'vless-node'
	assert proxy['type'] == 'vless'
	assert proxy['uuid'] == 'b831381d-6324-4d53-ad4f-8cda48b30811'
	assert proxy['tls'] is True
	assert proxy['servername'] == 'vl.example.com'


def test_parse_trojan_link():
	link = 'trojan://p%40ss@tj.example.com:443?sni=tj.example.com#trojan-node'
	proxies = convert(link)

	proxy = proxies[0]
	assert proxy['type'] == 'trojan'
	assert proxy['password'] == 'p@ss'
	assert proxy['sni'] == 'tj.example.com'


def test_parse_hysteria2_alias_link():
	link = 'hy2://secret@hy.example.com:8443?sni=hy.example.com&insecure=1#hy-node'
	proxies = convert(link)

	proxy = proxies[0]
	assert proxy['name'] == 'hy-node'
	assert proxy['type'] == 'hysteria2'
	assert proxy['password'] == 'secret'
	assert proxy['sni'] == 'hy.example.com'
	assert proxy['skip-cert-verify'] is True


def test_parse_base64_subscription_blob():
	lines = 'ss://YWVzLTEyOC1nY206cGFzc3dvcmQ@1.2.3.4:8388#node1\ntrojan://pw@2.3.4.5:443#node2\n'
	blob = base64.b64encode(lines.encode()).decode()
	proxies = convert(blob)

	assert [p['name'] for p in proxies] == ['node1', 'node2']


def test_preserve_base64_wrapped_clash_yaml():
	yaml_text = 'proxies:\n  - name: node1\n    type: ss\n'
	blob = base64.b64encode(yaml_text.encode()).decode()

	assert to_clash_yaml(blob) == yaml_text


def test_convert_skips_and_reports_unknown_schemes_and_bad_lines(capsys):
	text = 'http://not-a-proxy\nss://broken\nnot a link at all\n'
	proxies = convert(text)

	assert proxies == []
	assert 'unsupported schemes: http=1' in capsys.readouterr().err


def test_emit_yaml_produces_clash_compatible_block():
	proxies = [
		{'name': 'n1', 'type': 'ss', 'server': '1.2.3.4', 'port': 8388, 'cipher': 'aes-128-gcm', 'password': 'p'},
		{'name': 'n2', 'type': 'vless', 'server': 'h', 'port': 443, 'uuid': 'u', 'udp': True, 'tls': True},
	]
	yaml_text = emit_yaml(proxies)

	assert yaml_text.startswith('proxies:\n')
	assert '  - name: "n1"' in yaml_text
	assert '    udp: true' in yaml_text
	assert '    tls: true' in yaml_text
