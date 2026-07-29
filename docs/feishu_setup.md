# 飞书接入完整说明（企业自建应用 / 机器人）

本文说明：**回调是不是必须**、**各种 Token 分别是什么**（**不是** App Secret），以及用**飞书开放平台企业自建应用 + 机器人**接本仓库流水线的完整步骤。

---

## 一、先弄清：你要哪一种能力？

| 你的目标 | 要不要配置「事件订阅回调 URL」 | 需要配什么 |
|----------|-------------------------------|------------|
| **只在服务器上/脚本里一键跑策略流水线**（和飞书无关） | **不要** | 服务器设 `PIPELINE_TRIGGER_TOKEN`，调 `POST /api/pipeline/strategy_to_multi_debate` |
| **任务跑完后，往群里推一条「已启动 + job_id」** | **不要**（不是事件回调） | 群里建**自定义机器人**，拿 **Webhook URL** → 服务器设 `FEISHU_WEBHOOK_URL` |
| **在群里发一句话（含关键词）就自动跑流水线** | **要** | 开放平台里配置 **事件订阅**，请求 URL 指向 `https://你的域名/api/feishu/events`，并设 **`FEISHU_VERIFICATION_TOKEN`**（见下文） |

结论：

- **「回调」**指的是飞书**主动 POST 到你服务器**（事件订阅）。只有当你要 **收群消息、自动触发** 时才必须配。
- **群机器人 Webhook** 是你 **POST 到飞书**，方向相反，**不叫**事件回调，也**不需要**事件订阅 URL。

---

## 二、Token / 密钥对照表（重要）

很多人会把 **App Secret** 和 **事件校验 Token** 搞混，本仓库用法如下。

| 名称 | 在哪里看到 | 是不是 App Secret | 本仓库环境变量 |
|------|------------|-------------------|----------------|
| **Verification Token（校验 Token）** | 开放平台 → 你的应用 → **事件订阅** 页面里展示 | **不是** | **`FEISHU_VERIFICATION_TOKEN`**（仅当你启用事件订阅时必填） |
| **App Secret（应用密钥）** | 开放平台 → 应用 → **凭证与基础信息** | 就是「应用密钥」 | **当前代码未使用**；以后若要用开放平台 API **主动发消息、拉会话**，才需要用 App ID + App Secret 换 `tenant_access_token` |
| **App ID** | 同上「凭证与基础信息」 | — | 当前代码未使用 |
| **PIPELINE_TRIGGER_TOKEN** | **不是飞书发的**，你自己随机生成一串 | — | 仅用于 **`POST /api/pipeline/strategy_to_multi_debate`** 鉴权 |
| **自定义机器人 Webhook** | 飞书群 → 设置 → 群机器人 → 自定义机器人 → 复制地址 | — | **`FEISHU_WEBHOOK_URL`**（仅推送通知用） |

**直接回答你的问题：**

- 我说的 **`FEISHU_VERIFICATION_TOKEN` = 飞书「事件订阅」里的 Verification Token（校验 Token）**，**不是 App Secret**。
- **App Secret** 不要填进 `FEISHU_VERIFICATION_TOKEN`，否则校验会对不上。

---

## 三、企业自建应用 + 机器人：完整流程（群里发指令触发）

适用于：**已决定用开放平台里的企业自建应用机器人**，并希望 **群里发关键词就执行策略流水线**。

### 1. 创建应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app)（需企业管理员权限视租户而定）。
2. **创建企业自建应用**，填写名称、描述，创建完成。

### 2. 启用机器人

1. 进入该应用 → **应用能力** → 添加 **机器人**（或按向导开启）。
2. 保存。此时群里「添加机器人」时会出现你的应用机器人（需后续发布版本后可用）。

### 3. 权限管理（收消息必开）

1. **权限管理** → 搜索并勾选与 **即时消息 / 群消息** 相关的权限（例如接收消息、读取群信息等，**以当前控制台列表为准**，名称可能随版本变化）。
2. 保存权限配置。

### 4. 事件订阅（这里才要填「回调 URL」）

1. 打开 **事件订阅**。
2. **请求地址 URL** 填：  
   `https://你的域名/api/feishu/events`  
   例如：`https://stock_back.ygs.plus/api/feishu/events`  
   - 建议使用 **HTTPS**；纯 HTTP 可能被飞书拒绝或不稳定。
3. 点击保存后，飞书会向你填的地址发起 **URL 校验**（challenge），本仓库 `/api/feishu/events` 已处理，**服务必须已部署且公网可访问**。
4. 同一页面会显示 **Verification Token（校验 Token）** —— 复制到服务器环境变量：  
   `FEISHU_VERIFICATION_TOKEN=粘贴的内容`  
   **不要用 App Secret 代替。**
5. **添加事件**：订阅 **`im.message.receive_v1`**（或控制台中「接收消息 v2.0」等等价事件，以文档为准）。保存。

### 5. 加密（建议先关）

- 若事件订阅里开启了 **Encrypt Key / 消息加密**，本仓库当前按 **明文 JSON** 解析；**初次接入请先关闭加密**，否则需在代码里自行解密（未实现）。

### 6. 创建版本并发布

1. **版本管理与发布** → 创建版本 → 填写更新说明 → **申请发布**（或先「仅测试」给测试企业，按你租户规则）。
2. 未发布前，部分能力仅在开发环境生效，以飞书提示为准。

### 7. 把机器人拉进群

1. 在目标飞书群 → **设置** → **群机器人** → **添加机器人** → 选择你的 **企业自建应用机器人**。
2. 确保机器人在群内，且有权接收群消息（与权限、租户策略有关）。

### 8. 服务器环境变量（事件触发这一条线）

至少：

```bash
export FEISHU_VERIFICATION_TOKEN="事件订阅页里的 Verification Token"
```

可选（推送「任务已启动」到群，用的是**自定义机器人 Webhook**，可与上面同时使用）：

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx"
export PIPELINE_KEYWORD="策略辩论"   # 默认就是策略辩论，可改
```

**不需要**为飞书事件单独设 `PIPELINE_TRIGGER_TOKEN`（那是给手动 HTTP 调流水线用的）。

### 9. 触发方式

在群里发任意文字，**包含**环境变量里的关键词（默认 **「策略辩论」** 四个字），后端会在后台线程跑与 `POST /api/pipeline/strategy_to_multi_debate` 相同的流水线。

### 10. 查结果

辩论进度与报告仍用现有接口：

`GET https://你的域名/api/ai/debate/status/<job_id>`

（若前面 Webhook 已配置，群里会收到带 `job_id` 的简要提醒。）

---

## 四、只有「跑完往群里通知」，不要群里触发

1. 群里添加 **自定义机器人**，复制 **Webhook**。
2. 服务器只设：`FEISHU_WEBHOOK_URL=...`
3. 你用 **curl / 其它服务** 调 `POST /api/pipeline/strategy_to_multi_debate`（带 `PIPELINE_TRIGGER_TOKEN`），成功后服务器会往 Webhook **推一条文本**。

此路径 **不需要** 事件订阅，**不需要** `FEISHU_VERIFICATION_TOKEN`。

---

## 五、和 App Secret 的关系（扩展）

- **本仓库当前实现**：事件入口只校验 **Verification Token**；流水线跑在你自己服务器上。
- 若将来要在飞书里 **用开放平台 API 主动回复消息、发卡片**，才需要 **App ID + App Secret** 换 `tenant_access_token`，那是另一套调用，与 `FEISHU_VERIFICATION_TOKEN` **仍是不同概念**。

---

## 六、故障排查简表

| 现象 | 检查 |
|------|------|
| URL 校验失败 | HTTPS、路径 `/api/feishu/events`、服务已起、防火墙/反代 |
| 校验通过，发消息没反应 | 是否订阅 `im.message.receive_v1`、是否发布版本、机器人是否在群、消息是否含关键词 |
| 401/403 类错误 | `FEISHU_VERIFICATION_TOKEN` 是否与事件订阅页 **完全一致**（勿用 App Secret） |

---

## 七、本仓库接口一览

| 接口 | 用途 |
|------|------|
| `POST /api/feishu/events` | 飞书事件订阅回调（challenge + 收消息触发） |
| `POST /api/pipeline/strategy_to_multi_debate` | 手动/脚本一键跑流水线，需 `X-Pipeline-Token` |
| `GET /api/ai/debate/status/<job_id>` | 查辩论进度与报告 |

默认后端端口见 `api_server.py`（当前默认 **5010**），公网访问请以你 Nginx/Caddy 实际配置为准。
