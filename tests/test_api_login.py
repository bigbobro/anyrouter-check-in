import json

import httpx

import checkin
from utils.config import AppConfig, ProviderConfig


def _make_provider(**overrides) -> ProviderConfig:
	config = ProviderConfig(
		name='agentrouter',
		domain='https://example.com',
		sign_in_path=None,
		api_login=True,
	)
	for key, value in overrides.items():
		setattr(config, key, value)
	return config


def _patch_client(monkeypatch, handler):
	"""把 checkin 里的 httpx.Client 换成 MockTransport 版本。"""
	monkeypatch.delenv('CHECKIN_PROXY_URL', raising=False)
	transport = httpx.MockTransport(handler)
	real_client = httpx.Client
	monkeypatch.setattr(httpx, 'Client', lambda **kwargs: real_client(transport=transport, **kwargs))


def test_builtin_agentrouter_prefers_api_login(monkeypatch):
	monkeypatch.delenv('PROVIDERS', raising=False)

	config = AppConfig.load_from_env()

	assert config.providers['agentrouter'].api_login is True
	assert config.providers['anyrouter'].api_login is False


def test_provider_api_login_can_override_builtin(monkeypatch):
	monkeypatch.setenv(
		'PROVIDERS',
		json.dumps({'agentrouter': {'domain': 'https://agentrouter.org', 'api_login': False}}),
	)

	config = AppConfig.load_from_env()

	assert config.providers['agentrouter'].api_login is False


def test_api_login_success_returns_session_cookies_and_user_id(monkeypatch):
	def handler(request: httpx.Request) -> httpx.Response:
		assert request.url.path == '/api/user/login'
		assert request.url.params.get('turnstile') == ''
		payload = json.loads(request.content)
		assert payload == {'username': 'user@example.com', 'password': 'secret'}
		return httpx.Response(
			200,
			json={'success': True, 'message': '', 'data': {'id': 42, 'checked_in': True}},
			headers={'set-cookie': 'session=session-value; Path=/; HttpOnly'},
		)

	_patch_client(monkeypatch, handler)

	result, fallback = checkin.login_via_api('AG', _make_provider(), 'user@example.com', 'secret')

	assert fallback is False
	assert result is not None
	assert result.cookies.get('session') == 'session-value'
	assert result.api_user == '42'


def test_api_login_rejected_credentials_disables_browser_fallback(monkeypatch):
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, json={'success': False, 'message': '用户名或密码错误'})

	_patch_client(monkeypatch, handler)

	result, fallback = checkin.login_via_api('AG', _make_provider(), 'user@example.com', 'wrong')

	assert result is None
	assert fallback is False


def test_api_login_waf_html_triggers_browser_fallback(monkeypatch):
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, text='<html>Access Verification</html>', headers={'content-type': 'text/html'})

	_patch_client(monkeypatch, handler)

	result, fallback = checkin.login_via_api('AG', _make_provider(), 'user@example.com', 'secret')

	assert result is None
	assert fallback is True


def test_api_login_http_error_triggers_browser_fallback(monkeypatch):
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(403, text='Forbidden')

	_patch_client(monkeypatch, handler)

	result, fallback = checkin.login_via_api('AG', _make_provider(), 'user@example.com', 'secret')

	assert result is None
	assert fallback is True


def test_api_login_turnstile_required_triggers_browser_fallback(monkeypatch):
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, json={'success': False, 'message': 'Turnstile 校验失败'})

	_patch_client(monkeypatch, handler)

	result, fallback = checkin.login_via_api('AG', _make_provider(), 'user@example.com', 'secret')

	assert result is None
	assert fallback is True


def test_api_login_without_session_cookie_triggers_browser_fallback(monkeypatch):
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(
			200,
			json={'success': True, 'message': '', 'data': {'id': 42, 'checked_in': True}},
		)

	_patch_client(monkeypatch, handler)

	result, fallback = checkin.login_via_api('AG', _make_provider(), 'user@example.com', 'secret')

	assert result is None
	assert fallback is True


def test_api_login_network_error_triggers_browser_fallback(monkeypatch):
	def handler(request: httpx.Request) -> httpx.Response:
		raise httpx.ConnectError('connection refused')

	_patch_client(monkeypatch, handler)

	result, fallback = checkin.login_via_api('AG', _make_provider(), 'user@example.com', 'secret')

	assert result is None
	assert fallback is True
