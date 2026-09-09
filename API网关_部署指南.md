# API 网关可执行部署文档（New API + 硅基流动兜底）

> 生成日期：2026-08-28 ｜ 类型：**可执行部署文档**
> 决策依据（孟轩确认）：服务器=**境外** ｜ 主体=**个人** ｜ 暴露=**内网/本机（仅自己两台设备）** ｜ 域名=**无**
> 适用：个人 / 小团队，Agent 学习路线的统一 LLM 调用网关

---

## 🔴 0. 合规红线（必读，先于一切操作）

**数据出境风险**：本路线 W6（HR 政策问答助手）处理的政策/问答**可能含员工个人信息**。你选择的网关服务器在**境外**，意味着：
- 一旦把**真实员工个人信息**发送到该境外服务器 → 触发《个人信息保护法》"个人信息出境"合规义务（需单独同意、个人信息保护影响评估、必要时安全评估/标准合同）。
- **个人主体**同样受 PIPL 约束，不因"个人"而豁免。

**缓解方案（强制）**：
1. **学习/调优期**：只灌**示例或合成数据**（`w6_sample_policy.txt`、自己编造的问答），绝不放真实员工资料到境外服务器。
2. **真要做员工政策问答**：改在**境内服务器 + 境内模型**（硅基流动/DeepSeek 国内节点）部署一套同样的网关，境外这套仅用于非 PII 的实验。
3. 本部署文档的境外方案，**仅限非个人信息场景**。

> 若你打算把真实 HR 数据接入，请先告诉我，我另出"境内合规版"部署文档。

---

## 1. 架构

```
MAX 设备（当前唯一在用；shy 旧机已于 2026-08 退役）
   │
   └─(HTTPS/隧道, 强令牌, 仅白名单IP)─►  境外 VPS: New API(3000)  │ 主用渠道
                                                  └─► 硅基流动(兜底)
业务脚本 w4.base_url = http://<VPS_IP>:3000/v1
```

- 无公网域名 → 用 **VPS 公网 IP 直连** 或 **Cloudflare Tunnel（免域名、不暴露端口）**
- 仅自己一台设备用 → 防火墙**白名单**只放行 MAX 的出口 IP，或全程走 Tunnel（更省事）

---

## 2. 前置准备（在你的 VPS 上）

1. 租一台境外 VPS（Ubuntu 22.04，1C1G 起，5–10 USD/月足够）
2. SSH 登录，更新系统：
   ```bash
   sudo apt update && sudo apt -y upgrade
   ```
3. 安装 Docker：
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER   # 退出重登生效
   ```

---

## 3. 部署 New API（Docker，主用网关）

```bash
# 建数据目录
mkdir -p ~/newapi/data

# 启动（端口 3000；首次运行会自动迁移库）
docker run -d --name newapi \
  --restart unless-stopped \
  -p 3000:3000 \
  -v ~/newapi/data:/data \
  -e TZ=Asia/Shanghai \
  cyanray/newapi:latest
```

- 等 10 秒，访问 `http://<VPS_IP>:3000` → 首次打开会让你**设管理员账号+密码**（记住，后续管渠道/令牌用）
- 登录后：左侧「渠道」→ 新建，**类型=硅基流动**，填你的 `<SILICONFLOW_API_KEY>`，模型填 `deepseek-chat` / `deepseek-vision`（按你订阅）
- 「用户」→ 新建一个**普通用户/令牌**，拿到 `<GATEWAY_TOKEN>`（业务脚本只用这把，绝不直接用上游 Key）

---

## 4. 安全加固（无域名也必须做）

**方案 A（推荐，最省事）：Cloudflare Tunnel 免端口暴露**
```bash
# VPS 上装 cloudflared，登录后建隧道
cloudflared tunnel --url http://localhost:3000
# 终端会给出 https://xxxx.trycloudflare.com 临时地址（无需自有域名）
# 业务侧 base_url 用该 https 地址即可，3000 端口可不必对外开放
```

**方案 B（白名单防火墙）**
```bash
# 仅放行 MAX 的出口 IP（shy 旧机已退役，无需再放行）
# 查当前出口 IP：curl ifconfig.me
sudo ufw allow from <MAX_IP> to any port 3000
sudo ufw enable
```

> 无论哪种，**不要用弱令牌、不要 0.0.0.0 对全网开放 3000**。个人主体下泄露=别人刷你的额度。

---

## 5. 业务侧接入（仅 MAX 一台）

改 `w4_chat_module.py` 顶部配置（或直接设环境变量）：
```python
BASE_URL = "http://<VPS_IP>:3000/v1"      # 方案A则改成 https://xxxx.trycloudflare.com/v1
API_KEY = os.getenv("DEEPSEEK_API_KEY")   # 改为网关令牌（仍在 .env，不上云）
```
- `.env` 里把 `DEEPSEEK_API_KEY` 的值换成 `<GATEWAY_TOKEN>`，原上游 Key 只存于 VPS 的 New API 渠道配置里
- 跑 `python w4_chat_module.py` 验证能通

---

## 6. 验证清单

- [ ] VPS 上 `docker ps` 见 newapi 运行中
- [ ] 浏览器开 `http://<VPS_IP>:3000` 能登录
- [ ] 渠道测试：New API 后台「渠道」→ 测试，返回模型列表
- [ ] 业务侧 `w4` 单轮问答成功，日志见令牌消耗（非上游 Key）
- [ ] 限流/预算：New API 后台设用户额度，超了被拒（与本路线 w4 预算护栏双保险）

---

## 7. 回滚与成本

- 回滚：`docker stop newapi && docker rm newapi` 即停；数据在 `~/newapi/data` 可保留
- 成本：VPS 租金 + 硅基流动按量；New API 本身开源免费
- 兜底：硅基流动渠道设低优先级/限额，主用额度耗尽自动切换

---

## 8. 触发真实部署的动作（迪莫不做，需你执行）

以下**由你在 VPS 上执行**，迪莫不持有你的 VPS、不代跑：
1. 租 VPS、装 Docker（第 2–3 节）
2. `docker run` 起 New API、建管理员/令牌/渠道（第 3 节）
3. 安全加固二选一（第 4 节）
4. 业务侧改 `base_url`+`.env`（第 5 节）

完成后把 `<VPS_IP>`/`<GATEWAY_TOKEN>` 填进 MAX 的 `.env` 即可。任何一步报错，把报错发我，我帮你看。

---

## 7. 部署状态

| 项 | 状态 |
|---|---|
| 本网关**是否已部署** | ❌ **尚未部署**（截至 2026-08-29） |
| 部署前需完成 | 先看 `api_gateway_deploy_template.md` 的「待拍板确认项」（服务器地区/主体/暴露方式/域名），拍板后再按本文档执行 |
| 执行顺序 | `template`（确认）→ 本文档（执行）→ 第 6 节验证清单（验收） |
