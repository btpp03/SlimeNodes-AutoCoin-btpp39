# SlimeNodes AutoCoin (btpp39)

SlimeNodes 自动刷币 + 自动续期脚本。使用 `connect.sid` session cookie 认证，**session 过期时通过 Discord token 纯 HTTP 自动重登录**（免浏览器，绕开 hCaptcha）。

## 功能

- 🪙 **自动刷币** — 每次运行 20 个广告，每个 +12 币，共 +240 币
- 🔄 **自动续期** — 剩余 <24h 时自动续期服务器
- 🔐 **Session 自动恢复** — SID 失效/无法获取余额时，自动用 Discord token 走 OAuth 换新 session、更新 secret 并重试
- 📊 **余额检测** — 从 dashboard 实时获取余额
- ⏰ **到期检测** — 通过 `/lastrenew` API 获取服务器剩余时间
- 📢 **TG 通知** — 刷币结果、余额、剩余时间、续期状态推送到 Telegram
- 🚦 **真实退出码** — 失败时以非零码退出，GitHub Actions 如实反映状态并告警

## 运行机制

1. 使用 `connect.sid` session cookie 认证
2. 调用 `/lv/gen` → 解析 base64 `r` 参数 → 获取兑换 URL
3. 等待 16-20s 冷却 → 调用兑换 URL（Referer: linkvertise.com）→ +12 币
4. 重复 20 次，达到每日上限则停止
5. 检查 `/lastrenew?id=SERVER_ID` 获取到期时间，剩余 <24h 自动续期
6. **自动重登录**：若 `无法获取余额` 或请求返回过期（session 失效），自动走 Discord OAuth（`DISCORD_TOKEN` + client_id）换新 `connect.sid` → 用 `GH_TOKEN` 更新 `SLIME_SESSION` secret → 重新刷币

## GitHub Secrets 配置

| Secret | 说明 | 示例 |
|--------|------|------|
| `SLIME_SESSION` | `connect.sid` session cookie | `s%3A4qPg...` |
| `DISCORD_TOKEN` | Discord 账号 token（纯 HTTP OAuth 换 session 用） | `MTM5...` |
| `GH_TOKEN` | GitHub PAT（自动更新 SLIME_SESSION secret） | `ghp_...` |
| `SERVER_ID` | 数字格式服务器 ID | `10106` |
| `TG_BOT_TOKEN` | Telegram Bot Token | `7935239797:AAH...` |
| `TG_CHAT_ID` | Telegram Chat ID | `644320820` |
| `VLINK` | sing-box 代理链接 | `vlk://...` |
| `RENEW_THRESHOLD` | 续期所需最低余额（默认 50） | `50` |
| `RENEW_HOURS` | 剩余多少小时触发续期（默认 24） | `24` |

> ⚠️ `SERVER_ID` 必须是**数字格式**（如 `10106`），不是 hex 格式（如 `5b0322ed`）
> 🔑 `DISCORD_TOKEN` 获取：浏览器登录 Discord → DevTools → Network → 任一个 `discord.com/api` 请求 → Request Headers → `authorization` 字段的值

## Cron 定时

每天 2 次自动运行：
- `00:30 UTC` (北京时间 08:30)
- `12:30 UTC` (北京时间 20:30)

每日可获约 480 币（2 次 × 240 币）。

## TG 通知格式

```
🟢 SlimeNodes 刷币 2026-06-03 10:52 UTC
✅ 39btpp: +240币 | 余额15859
⏰ 剩余: 168小时 (7.0天)
🔄 续期: ⏭️ 暂不需要 (>24h)
💰 总计: +240币
```

session 失效且自动重登录成功时，通知会标注 `🔄 (本次已自动刷新 session 并重试)`。

## 文件结构

```
├── makecoins.py          # 主脚本（刷币 + 续期 + Discord OAuth 自动重登录 + 通知）
├── auto_login.py         # (备选) 浏览器版 Discord 登录 — hCaptcha 拦，不推荐使用
├── link_to_sb.py         # VLINK → sing-box 配置转换
├── .github/workflows/
│   └── autocoin.yml      # GitHub Actions 工作流
└── README.md
```

## 注意事项

- `SLIME_SESSION` 过期时**无需手动处理**：脚本会自动用 `DISCORD_TOKEN` 重登录并更新 secret（前提是配置了 `DISCORD_TOKEN` + `GH_TOKEN`）
- 若两者未配置，SID 失效后仍会失败，需手动刷新的 session 填入 `SLIME_SESSION`
- 续期消耗 50 币，确保余额充足
- 通过 sing-box 代理访问，需配置 `VLINK` secret
- 浏览器版 `auto_login.py` 曾被 Discord hCaptcha 拦截，已弃用；优先纯 HTTP token 方案
