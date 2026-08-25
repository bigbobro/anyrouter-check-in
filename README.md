# Any Router 多账号自动签到

[![GitHub Actions](https://github.com/bigbobro/anyrouter-check-in/actions/workflows/checkin.yml/badge.svg)](https://github.com/bigbobro/anyrouter-check-in/actions/workflows/checkin.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/github/license/bigbobro/anyrouter-check-in)](LICENSE)

支持 Any Router 与 Agent Router 多账号自动签到，也可通过 `PROVIDERS` 接入其他兼容的 NewAPI、OneAPI 平台。

推荐搭配使用 [Auo](https://github.com/millylee/auo)，支持任意 Claude Code Token 切换的工具。

**维护开源不易，如果本项目帮助到了你，请帮忙点个 Star，谢谢!**

[Any Router 注册入口](https://anyrouter.top/register?aff=gSsN)。

## 功能特性

- ✅ 多平台（兼容 NewAPI 与 OneAPI）
- ✅ 单个/多账号自动签到
- ✅ 多种机器人通知（可选）
- ✅ 绕过 WAF 限制

## 使用方法

### 1. Fork 本仓库

点击右上角的 "Fork" 按钮，将本仓库 fork 到你的账户。

### 2. 准备账号信息

推荐直接配置邮箱和密码：

- **Any Router**：支持邮箱密码登录，也兼容旧版 `session` cookies + `api_user` 配置。
- **Agent Router**：请使用邮箱密码。脚本优先调用登录 API，该接口会同时完成签到，无需填写 `api_user`。

如果 Any Router 仍使用旧版 session 配置，可按下面步骤获取信息（也可借助 [在线 Secrets 配置生成器](https://millylee.github.io/anyrouter-check-in/)）：

#### 获取 Any Router Cookies：

1. 打开浏览器，访问 https://anyrouter.top/
2. 登录你的账户
3. 打开开发者工具 (F12)
4. 切换到 "Application" 或 "存储" 选项卡
5. 找到 "Cookies" 选项
6. 复制所有 cookies

#### 获取 Any Router API User：

按照下方图片教程操作获得。

### 3. 设置 GitHub Environment Secret

1. 在你 fork 的仓库中，点击 "Settings" 选项卡
2. 在左侧菜单中找到 "Environments" -> "New environment"
3. 新建一个名为 `production` 的环境
4. 点击新建的 `production` 环境进入环境配置页
5. 点击 "Add environment secret" 创建 secret：
   - Name: `ANYROUTER_ACCOUNTS`
   - Value: 你的多账号配置数据

如果账号中包含 Agent Router，在 GitHub Actions 中通常还需要按下文“AgentRouter 代理配置”设置 `PROXY_SUBSCRIPTION_URL`。

### 4. 多账号配置格式

支持单个与多个账号配置，可选 `name` 和 `provider` 字段：

```json
[
  {
    "name": "我的主账号",
    "email": "account1@example.com",
    "password": "account1_password"
  },
  {
    "name": "备用账号",
    "provider": "agentrouter",
    "email": "account2@example.com",
    "password": "account2_password"
  }
]
```

**字段说明**：

- `email` + `password`：推荐的登录方式；Agent Router 会优先直接调用登录 API，必要时再回退浏览器登录
- `cookies`：兼容旧版的 session cookies 登录方式
- `api_user`：session cookies 登录时用于请求头的 new-api-user 参数；邮箱密码登录可省略
- `provider` (可选)：指定使用的服务商，默认为 `anyrouter`
- `name` (可选)：自定义账号显示名称，用于通知和日志中标识账号

**默认值说明**：

- 如果未提供 `provider` 字段，默认使用 `anyrouter`（向后兼容）
- 如果未提供 `name` 字段，会使用 `Account 1`、`Account 2` 等默认名称
- `anyrouter` 与 `agentrouter` 配置已内置，无需填写

如果 Any Router 使用 session cookies 登录，接下来获取 cookies 与 `api_user` 的值。

通过 F12 工具切到 Application 面板，获取 `session` 的值。session 失效并出现 401 后，请重新登录并获取。

![获取 cookies](./assets/request-session.png)

通过 F12 工具，切到 Network 面板，可以过滤下，只要 Fetch/XHR，找到带 `New-Api-User`，这个值正常是 5 位数，如果是负数或者个位数，正常是未登录。

![获取 api_user](./assets/request-api-user.png)

### 5. 启用 GitHub Actions

1. 在你的仓库中，点击 "Actions" 选项卡
2. 如果提示启用 Actions，请点击启用
3. 找到 "AnyRouter 自动签到" workflow
4. 点击 "Enable workflow"

### 6. 测试运行

你可以手动触发一次签到来测试：

1. 在 "Actions" 选项卡中，点击 "AnyRouter 自动签到"
2. 点击 "Run workflow" 按钮
3. 按需设置 `debug`（详细日志和截图）与 `browser_fallback`（API 登录失败后是否回退浏览器），然后确认运行

![运行结果](./assets/check-in.png)

## 执行时间

- GitHub Actions 每 12 小时触发一次；定时任务可能延迟，实际执行时间以 Actions 记录为准
- 你也可以随时手动触发签到

## 注意事项

- 请确保每个账号的邮箱密码，或旧版 cookies 与 API User 配置正确
- 可以在 Actions 页面查看详细的运行日志
- 只要至少一个账号成功，workflow 就可能显示绿色；完整成功必须以日志末尾的 `Success: 账号总数/账号总数` 和 `Failed: 0/账号总数` 为准
- 报 401 错误时，请重新登录并获取 cookies，相关记录见 [#6](https://github.com/millylee/anyrouter-check-in/issues/6)
- 请求为 200 但出现 `Error 1040 (08004): Too many connections` 时，通常是服务端数据库连接问题，可稍后重试，相关记录见 [#7](https://github.com/millylee/anyrouter-check-in/issues/7)

## 配置示例

### 基础配置（向后兼容）

假设你有两个账号需要签到，不指定 provider 时默认使用 anyrouter：

```json
[
  {
    "cookies": {
      "session": "abc123session"
    },
    "api_user": "user123"
  },
  {
    "cookies": {
      "session": "xyz789session"
    },
    "api_user": "user456"
  }
]
```

### 多服务商配置

如果你需要同时使用多个服务商（如 anyrouter 和 agentrouter）：

```json
[
  {
    "name": "AnyRouter 主账号",
    "provider": "anyrouter",
    "cookies": {
      "session": "abc123session"
    },
    "api_user": "user123"
  },
  {
    "name": "AgentRouter 备用",
    "provider": "agentrouter",
    "email": "agent@example.com",
    "password": "agent_password"
  }
]
```

## 自定义 Provider 配置（可选）

默认情况下，`anyrouter`、`agentrouter` 已内置配置，无需额外设置。如果你需要使用其他服务商，可以通过环境变量 `PROVIDERS` 配置：

### 基础配置（仅域名）

大多数情况下，只需提供 `domain` 即可，其他路径会自动使用默认值：

```json
{
  "customrouter": {
    "domain": "https://custom.example.com"
  }
}
```

### 完整配置（自定义路径）

如果服务商使用了不同的 API 路径、请求头或需要 WAF 绕过，可以额外指定：

```json
{
  "customrouter": {
    "domain": "https://custom.example.com",
    "login_path": "/auth/login",
    "sign_in_path": "/api/checkin",
    "user_info_path": "/api/profile",
    "api_user_key": "New-Api-User",
    "bypass_method": "waf_cookies",
    "waf_cookie_names": ["acw_tc", "cdn_sec_tc", "acw_sc__v2"]
  }
}
```

**关于 `bypass_method`**：

- 不设置或设置为 `null`：直接使用用户提供的 cookies 进行请求（适合无 WAF 保护的网站）
- 设置为 `"waf_cookies"`：使用 CloakBrowser 打开浏览器获取 WAF cookies 后再进行请求（适合有 WAF 保护的网站）

> 注：`anyrouter` 和 `agentrouter` 已内置默认配置，无需在 `PROVIDERS` 中配置

### 在 GitHub Actions 中配置

1. 进入你的仓库 Settings -> Environments -> production
2. 添加新的 secret：
   - Name: `PROVIDERS`
   - Value: 你的 provider 配置（JSON 格式）

**字段说明**：

- `domain` (必需)：服务商的域名
- `login_path` (可选)：登录页面路径，默认为 `/login`（仅在 `bypass_method` 为 `"waf_cookies"` 时使用）
- `sign_in_path` (可选)：签到 API 路径，默认为 `/api/user/sign_in`
- `user_info_path` (可选)：用户信息 API 路径，默认为 `/api/user/self`
- `api_user_key` (可选)：API 用户标识请求头名称，默认为 `new-api-user`
- `bypass_method` (可选)：WAF 绕过方法
  - `"waf_cookies"`：使用 CloakBrowser 打开浏览器获取 WAF cookies 后再执行签到
  - 不设置或 `null`：直接使用用户 cookies 执行签到（适合无 WAF 保护的网站）
- `waf_cookie_names` (可选)：绕过 WAF 所需 cookie 的名称列表，`bypass_method` 为 `waf_cookies` 时必须设置

**配置示例**（完整）：

```json
{
  "customrouter": {
    "domain": "https://custom.example.com",
    "login_path": "/auth/login",
    "sign_in_path": "/api/checkin",
    "user_info_path": "/api/profile",
    "api_user_key": "x-user-id",
    "bypass_method": "waf_cookies"
  }
}
```

**内置配置说明**：

- `anyrouter`：
  - `bypass_method: "waf_cookies"`（需要先获取 WAF cookies，然后执行签到）
  - `sign_in_path: "/api/user/sign_in"`
- `agentrouter`：
  - `api_login: true`（优先直接调用 `/api/user/login` 完成登录与签到，失败再回退浏览器登录）
  - `bypass_method: "waf_cookies"`（需要获取 `acw_tc`，仅浏览器回退路径使用）
  - `sign_in_path: null`（登录接口即签到）
  - `use_proxy: true`

**重要提示**：

- `PROVIDERS` 是可选的，不配置则使用内置的 `anyrouter` 和 `agentrouter`
- 自定义的 provider 配置会覆盖同名的默认配置

## AgentRouter 代理配置

内置的 `agentrouter` 默认 `use_proxy: true`。GitHub 托管 runner 的机房出口容易触发 AgentRouter WAF，因此在 Actions 中使用 AgentRouter 时通常需要配置代理订阅；本地网络若能直接访问，则不一定需要。

在仓库 Settings -> Environments -> production -> Environment secrets 中添加：

- `PROXY_SUBSCRIPTION_URL`：runner 可直接访问、正文非空的订阅链接。支持 Clash YAML，以及原文或 Base64 包裹的 `ss`、`vmess`、`vless`、`trojan`、`hy2` / `hysteria2` 分享链接列表。
- `PROXY_NODE_FILTER`（可选）：mihomo 节点名称过滤正则。不设置时脚本会逐个探测前 30 个节点，选择能通过 AgentRouter WAF 的节点；设置后会跳过自动逐节点探测，因此过滤结果本身必须可用。

workflow 会协商常见订阅 User-Agent、启动 mihomo，并把本地地址写入 `CHECKIN_PROXY_URL`。订阅链接属于敏感信息，不要粘贴到 issue 或公开日志中。

本地已有代理时，可以直接设置：

```bash
CHECKIN_PROXY_URL=http://127.0.0.1:7890 uv run checkin.py
```

订阅脚本默认使用 `https://www.google.com/generate_204` 检查代理连通性，可通过 `PROXY_TEST_URL` 覆盖；逐节点 WAF 探测地址可通过 `PROXY_PROBE_URL` 覆盖。

运行日志至少应确认：

- `Subscription candidate ... bytes ...` 中字节数大于 0。
- `Provider 'subscription': ... count = N` 中 `N` 大于 0。
- 未设置 `PROXY_NODE_FILTER` 时，出现 `Selected node that bypasses AgentRouter WAF`；否则检查所选节点实际可用。
- 最终统计为 `Success: 账号总数/账号总数`、`Failed: 0/账号总数`。

如果订阅响应 `bytes 0`、provider 节点数为 0，或没有节点能绕过 WAF，请更新订阅链接或调整节点过滤；不能只依据 workflow 的绿色图标判断全部账号成功。

## 开启通知

脚本支持多种通知方式，可以通过配置以下环境变量开启，如果 `webhook` 有要求安全设置，例如钉钉，可以在新建机器人时选择自定义关键词，填写 `AnyRouter`。

### 邮箱通知(STMP)

- `EMAIL_USER`: 发件人邮箱地址/STMP 登录地址
- `EMAIL_PASS`: 发件人邮箱密码/授权码
- `EMAIL_SENDER`: 邮件显示的发件人地址(可选，默认: EMAIL_USER)
- `CUSTOM_SMTP_SERVER`: 自定义发件人 SMTP 服务器(可选)
- `EMAIL_TO`: 收件人邮箱地址

### 钉钉机器人

- `DINGDING_WEBHOOK`: 钉钉机器人的 Webhook 地址

### 飞书机器人

- `FEISHU_WEBHOOK`: 飞书机器人的 Webhook 地址

### 企业微信机器人

- `WEIXIN_WEBHOOK`: 企业微信机器人的 Webhook 地址

### PushPlus 推送

- `PUSHPLUS_TOKEN`: PushPlus 的 Token

### Server 酱

- `SERVERPUSHKEY`: Server 酱的 SendKey

### Telegram Bot

- `TELEGRAM_BOT_TOKEN`: Telegram Bot 的 Token
- `TELEGRAM_CHAT_ID`: Telegram Chat ID

### Gotify 推送

- `GOTIFY_URL`: Gotify 服务的 URL 地址（例如: https://your-gotify-server/message）
- `GOTIFY_TOKEN`: Gotify 应用的访问令牌
- `GOTIFY_PRIORITY`: Gotify 消息优先级 (1-10, 默认为 9)

### Bark 推送

- `BARK_KEY`: Bark 应用的 Key（APP 打开时即可看到）
- `BARK_SERVER`: 自建 Bark 服务器地址 (可选，默认: https://api.day.app)

配置步骤：

1. 在仓库的 Settings -> Environments -> production -> Environment secrets 中添加上述环境变量
2. 每个通知方式都是独立的，可以只配置你需要的推送方式
3. 如果某个通知方式配置不正确或未配置，脚本会自动跳过该通知方式

## 故障排除

如果签到失败，请检查：

1. 邮箱密码是否正确；Any Router 使用旧版 session 时，cookies 是否过期、`api_user` 是否匹配
2. AgentRouter 的订阅响应是否非空，provider 节点数是否大于 0
3. 代理节点是否通过 WAF 探测；若全部失败，更新订阅或调整 `PROXY_NODE_FILTER`
4. 自定义平台的域名与签到接口是否发生变化
5. 查看 Actions 末尾的成功/失败统计，不要只看 workflow 是否为绿色

## 本地开发环境设置

如果你需要在本地测试或开发，请按照以下步骤设置：

```bash
# 安装所有依赖
uv sync --dev

# 安装 CloakBrowser 浏览器
uv run python -m cloakbrowser install
# 如需使用本地浏览器，可设置 CLOAKBROWSER_BINARY_PATH=/path/to/browser

# 创建 .env 文件并配置（注意：JSON 必须是单行格式）
# 示例：
# ANYROUTER_ACCOUNTS=[{"name":"账号1","email":"your@email.com","password":"your_password"}]
# PROXY_SUBSCRIPTION_URL=https://example.com/sub?token=xxx
# PROXY_NODE_FILTER=香港|日本
# CHECKIN_PROXY_URL=http://127.0.0.1:7890

# 运行签到脚本
uv run checkin.py
```

## 测试

```bash
uv sync --dev

# 浏览器相关测试或本地登录可安装 CloakBrowser，或设置 CLOAKBROWSER_BINARY_PATH 指向本地浏览器
uv run python -m cloakbrowser install

# 运行测试
uv run pytest tests/

# 查看测试覆盖率
uv run pytest tests/ --cov=. --cov-report=html
```

## 贡献指南

欢迎贡献代码！在提交 Pull Request 之前，请阅读[贡献指南](CONTRIBUTING.md)。

### 代码质量

本项目使用以下工具确保代码质量：

- **Ruff**: 代码风格检查和格式化
- **MyPy**: 静态类型检查
- **Bandit**: 安全漏洞扫描
- **Pytest**: 自动化测试
- **pre-commit**: Git 提交前自动检查

所有 Pull Request 会自动运行以下检查：

- ✅ 代码风格检查（Ruff Lint & Format）
- ✅ 类型检查（MyPy）
- ✅ 安全扫描（Bandit）
- ✅ 测试运行（Pytest）
- ✅ 测试覆盖率报告（Codecov）

### 本地开发

```bash
# 安装开发依赖
uv sync --dev

# 安装 pre-commit 钩子
uv run pre-commit install

# 运行代码检查
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run bandit -r . -c pyproject.toml

# 运行测试
uv run pytest tests/ --cov=.
```

## 免责声明

本脚本仅用于学习和研究目的，使用前请确保遵守相关网站的使用条款.
