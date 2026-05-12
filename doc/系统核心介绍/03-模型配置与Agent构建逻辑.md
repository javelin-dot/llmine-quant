# 模型配置与 Agent 构建逻辑

## 1 概述

本文档描述 LLMine Quant 系统中 LLM 模型配置层与 Agent 构建体系的设计与实现。系统采用**Provider 模式**封装多模型供应商，向上统一下游 Agent 和策略生成服务的调用接口，支持 Anthropic（Claude）、OpenAI（GPT）和 Mock 三种运行时。

---

## 2 目录结构

```
backend/app/
├── core/
│   └── config.py                     # Settings（Pydantic BaseSettings）
├── integrations/llm/
│   ├── base.py                       # LLMProvider 抽象基类 + 数据类
│   ├── anthropic.py                  # AnthropicLLMProvider
│   ├── openai.py                     # OpenAILLMProvider
│   ├── mock.py                       # MockLLMProvider
│   ├── factory.py                    # get_llm_provider() 工厂函数
│   └── prompts.py                    # 策略生成 Prompt 模板
├── domains/agents/
│   └── models.py                     # AgentRegistry / AgentTask / AgentMessage / ToolRegistry
├── services/
│   ├── agent_orchestrator.py          # AgentOrchestrator（任务调度/消息传递）
│   └── strategy_generation.py         # StrategyGenerationService（6步Pipeline）
└── api/v1/
    └── agents.py                     # REST API 端点
```

---

## 3 模型配置体系

### 3.1 核心配置类 (`config.py`)

`Settings` 类（继承 Pydantic `BaseSettings`）是整个系统的配置中枢，所有 LLM 相关配置均在此定义并从环境变量或配置文件自动注入。

#### LLM 通用配置

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `llm_provider` | `str \| None` | `None` | 提供商名称，`anthropic` / `openai` / `mock` |
| `llm_timeout_seconds` | `int` | `120` | API 请求超时（秒） |
| `llm_max_tokens` | `int` | `4096` | 单次生成最大 Token 数 |

#### Anthropic 配置

| 字段 | 说明 |
|---|---|
| `anthropic_api_key` | 标准 API Key（`ANTHROPIC_API_KEY`） |
| `anthropic_auth_token` | Bearer 风格 Token，用于 Kimi 等兼容代理 |
| `anthropic_base_url` | 可选，自定义端点 |
| `anthropic_model` | 模型 ID，默认 `claude-sonnet-4-6` |

#### OpenAI 配置

| 字段 | 说明 |
|---|---|
| `openai_api_key` | 标准 API Key（`OPENAI_API_KEY`） |
| `openai_base_url` | 可选，自定义端点 |
| `openai_model` | 模型 ID，默认 `gpt-4o` |

#### 凭据自动注入

系统启动时从两个配置文件自动检测并注入凭据：

- `~/.claude/settings.json` → 优先，取 Bearer Token 或原生 Key
- `~/.codex/auth.json` → 次选，取 OpenAI API Key

注入结果记录在 `settings.llm_source`（`env` / `config_file` / `mock`）。

### 3.2 LLM Provider 抽象层 (`base.py`)

#### 数据类

```python
@dataclass
class LLMMessage:
    role: str           # "user" | "assistant"
    content: str

@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    usage: dict[str, int]    # {prompt_tokens, completion_tokens}
    raw: Any | None           # 原始 SDK 响应对象
```

#### 抽象基类签名

```python
class LLMProvider(ABC):
    name: str = "abstract"
    default_model: str = ""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 120,
        max_tokens: int = 4096,
    ) -> None: ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        history: list[LLMMessage] | None = None,
    ) -> LLMResponse: ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]: ...
```

两个抽象方法构成 Provider 的全部接口约束：

- `generate()` — 自由文本生成，返回 `LLMResponse`
- `generate_structured()` — JSON 结构化输出，直接返回 Python `dict`

---

## 4 Provider 实现

### 4.1 `AnthropicLLMProvider` (`anthropic.py`)

**默认模型**: `claude-sonnet-4-6`

**扩展构造参数**: `auth_token: str | None`、`base_url: str | None`

#### `_get_client()` 逻辑

1. 延迟导入 `anthropic` SDK（未安装则抛出 `LLMException`）
2. 检查 `api_key` 和 `auth_token` 至少有一个
3. 构建 `kwargs`：
   - `timeout` 必填
   - 若配置了 `base_url` → 加入 kwargs
   - 若配置了 `auth_token` → 作为 Bearer Token 使用（Kimi 兼容代理）
   - 否则 → 使用标准 `api_key`
4. 返回 `anthropic.AsyncAnthropic(**kwargs)`

#### `generate()` 实现

```python
# history 拼入 messages，system 通过专用 system 参数传入
kwargs = {
    "model": self.model,
    "max_tokens": self.max_tokens,
    "temperature": temperature,
    "messages": messages,          # [{"role": ..., "content": ...}, ...]
    "system": system_prompt,       # Anthropic 专用字段
}
resp = await client.messages.create(**kwargs)

# 遍历 content blocks，只取 text 类型（跳过 thinking / tool blocks）
for block in resp.content:
    if block.type == "text":
        text_parts.append(block.text)
```

#### `generate_structured()` 实现

1. 将 output schema 格式化为提示文本，追加到 system prompt 末尾：

   ```text
   Return ONLY a JSON object that conforms to this schema:
   {"name": "...", "family": "...", ...}
   Do not include markdown fences or commentary.
   ```

2. 调用 `self.generate()` 获取文本响应
3. 若响应以 markdown fences 包裹（` ``` `），自动剥离
4. `json.loads()` 解析返回 dict

#### Token 统计字段映射

| SDK 字段 | 返回字段 |
|---|---|
| `resp.usage.input_tokens` | `prompt_tokens` |
| `resp.usage.output_tokens` | `completion_tokens` |

---

### 4.2 `OpenAILLMProvider` (`openai.py`)

**默认模型**: `gpt-4o`

**扩展构造参数**: `base_url: str | None`

#### `_get_client()` 逻辑

1. 延迟导入 `openai` SDK
2. 检查 `api_key` 已配置
3. 构建 kwargs：`api_key`、`timeout`、`base_url`（可选）
4. 返回 `openai.AsyncOpenAI(**kwargs)`

#### `generate()` 实现

```python
# system 放在 messages[0]，与 Anthropic 方式不同
messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
for m in history or []:
    messages.append({"role": m.role, "content": m.content})
messages.append({"role": "user", "content": prompt})

resp = await client.chat.completions.create(
    model=self.model,
    temperature=temperature,
    max_tokens=self.max_tokens,
    messages=messages,
)
```

#### `generate_structured()` 实现

使用 OpenAI 原生 `response_format` 机制：

```python
resp = await client.chat.completions.create(
    ...
    response_format={"type": "json_object"},
)
```

无需在 prompt 中追加 schema hint，JSON mode 强制模型输出 JSON。若解析失败，抛出 `LLMException`（含原始文本截取）。

---

### 4.3 `MockLLMProvider` (`mock.py`)

**默认模型**: `mock-strategy-v1`

用于离线开发、CI、免费演示场景，完全不依赖外部 API。

#### `generate()`

返回固定的 A 股价值策略模板 `GeneratedValueStrategy`，包含：

- **选股逻辑**：ROE/PE 复合打分 + 20 日动量过滤
- **风控逻辑**：按 `risk_profile` 约束 `max_weight` / `max_leverage`
- **头寸分配**：等权配置头部分位（top quintile），clip 到单票上限

#### `generate_structured()`

返回硬编码元数据：

```python
{
    "name": "AI 价值精选 v1",
    "family": "value",
    "description": "ROE/PE 复合打分 + 20 日动量确认，等权配置头部分位",
    "universe": "沪深300",
    "frequency": "1d",
    "expected_sharpe": 1.35,
    "expected_max_dd": 0.18,
}
```

#### `generate_structured()` 实现细节

```python
# 忽略 schema 参数，直接深拷贝返回
return json.loads(json.dumps(_MOCK_METADATA))
```

---

### 4.4 工厂函数 (`factory.py`)

```python
def get_llm_provider(provider: str | None = None) -> LLMProvider:
    name = (provider or settings.llm_provider or "mock").lower()

    if name == "mock":
        return MockLLMProvider(...)
    if name == "anthropic":
        return AnthropicLLMProvider(
            api_key=settings.anthropic_api_key,
            auth_token=settings.anthropic_auth_token,
            base_url=settings.anthropic_base_url,
            model=settings.anthropic_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_tokens,
        )
    if name == "openai":
        return OpenAILLMProvider(...)
```

工厂函数将 `settings` 中的配置按 Provider 类型分发，所有实例共享 `timeout_seconds` / `max_tokens`。

---

## 5 Provider 实现差异对照

| 维度 | Anthropic | OpenAI | Mock |
|---|---|---|---|
| **默认模型** | `claude-sonnet-4-6` | `gpt-4o` | `mock-strategy-v1` |
| **结构化输出方式** | Prompt 追加 schema hint | `response_format` JSON mode | 硬编码返回 |
| **System 处理** | 专用 `system` 参数 | 放入 `messages[0]` | 忽略 |
| **历史消息** | 通过 `messages` 传入 | 通过 `messages` 传入 | 忽略 |
| **Markdown 清理** | 需手动 strip fences | 不需要 | 不需要 |
| **Token 字段映射** | `input_tokens` → `prompt_tokens` | `prompt_tokens` / `completion_tokens` | 估算值 |
| **特殊参数** | `auth_token`（Bearer） | `base_url` | — |
| **API 错误处理** | 统一包装为 `LLMException` | 统一包装为 `LLMException` | 不抛出 |

---

## 6 Agent 体系

### 6.1 领域模型 (`domains/agents/models.py`)

| 模型 | 字段概览 | 用途 |
|---|---|---|
| `AgentRegistry` | `name`, `role`, `status`（active/idle/error/paused）, `current_task`, `metric`, `heartbeat_at`, `config_json` | 记录所有 Agent 实例及其健康状态 |
| `AgentTask` | `agent_id`, `task_type`, `payload_json`, `priority`, `status`（pending/running/completed/failed）, `result_json`, `started_at`, `completed_at` | 任务全生命周期管理 |
| `AgentMessage` | `from_agent`, `to_agent`, `msg_type`（request/response/event/broadcast）, `topic`, `payload_json`, `correlation_id` | Agent 间通信消息 |
| `ToolRegistry` | `name`, `level`（low/medium/high）, `description`, `allowed_agents`, `schema_json`, `enabled` | 工具注册，含 L1-L6 分级 |

#### Agent 角色类型

| 角色 | 说明 |
|---|---|
| `research` | 研究 Agent，负责市场数据和分析 |
| `strategy` | 策略构建 Agent |
| `backtest` | 回测 Agent |
| `risk` | 风控 Agent |
| `execution` | 执行 Agent |
| `portfolio` | 组合管理 Agent |
| `explain` | 解释 Agent |
| `data` | 数据 Agent |

### 6.2 Agent 编排服务 (`services/agent_orchestrator.py`)

`AgentOrchestrator` 是 Agent 系统的核心编排器，提供以下能力：

| 方法 | 签名 | 说明 |
|---|---|---|
| `dispatch()` | `(role, task_type, payload, priority?)` → `AgentTask` | 向指定角色 Agent 下发任务，创建并持久化 `AgentTask` |
| `complete_task()` | `(task_id, result)` | 标记任务成功/失败，存储结果 JSON |
| `send_message()` | `(from_agent, to_agent, topic, msg_type, payload)` | Agent 间消息传递 |

关键设计：
- 任务通过 `correlation_id` 关联追踪
- 任务结果通过 `result_json` 存储，支持任意 JSON 序列化对象

### 6.3 REST API 端点 (`api/v1/agents.py`)

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/agents/overview` | 返回 agents + recent tasks + messages + tools 总览 |
| `POST` | `/agents/tasks` | 下发新任务（dispatch） |
| `GET` | `/agents/tasks/{task_id}` | 查询单个任务状态和结果 |
| `POST` | `/agents/messages` | Agent 间发送消息 |
| `GET` | `/agents/messages` | 查看消息列表 |

---

## 7 策略生成流水线

### 7.1 `StrategyGenerationService` (`services/strategy_generation.py`)

系统通过 6 步 Pipeline 将用户的自然语言描述转换为可执行策略：

```
用户NL描述 + risk_profile + market
        │
        ▼
Stage 1: research
        │  dispatch 给 "research" 角色 Agent
        ▼
Stage 2: code_gen
        │  get_llm_provider().generate()
        │  + STRATEGY_GENERATION_SYSTEM/USER_PROMPT
        ▼
Stage 3: static_check
        │  AST.parse() 语法验证
        ▼
Stage 4: backtest
        │  注入 task_id，执行 mock 回测
        ▼
Stage 5: risk_check
        │  max_dd <= profile_cap AND sharpe >= 0.8
        ▼
Stage 6: persist
        │  持久化策略 + 版本记录
```

### 7.2 Prompt 模板 (`integrations/llm/prompts.py`)

系统预置两套 Prompt 模板：

| 模板对 | 用途 | 目标输出 |
|---|---|---|
| `STRATEGY_GENERATION_*` | 生成策略代码 | `RuleBasedStrategy` Python 类代码 |
| `STRATEGY_METADATA_*` | 生成元数据 | JSON：name / family / description / universe / frequency / expected_sharpe / expected_max_dd |

两套模板均使用 **temperature=0.2**（低随机性，保证输出稳定）。

### 7.3 `run_pipeline()` 执行流程

```python
async def run_pipeline(self, market, risk_profile, prompt, task_id) -> dict:
    # Stage 1
    await self._dispatch_to_role("research", ...)

    # Stage 2
    provider = get_llm_provider()
    resp = await provider.generate(prompt, system_prompt=..., temperature=0.2)

    # Stage 3
    AST.parse(resp.text)

    # Stage 4
    mock_backtest_result = await self._mock_backtest(task_id, resp.text)

    # Stage 5
    risk_ok = (
        mock_backtest_result["max_dd"] <= CAPS[risk_profile] and
        mock_backtest_result["sharpe"] >= 0.8
    )

    # Stage 6
    return await self._persist_strategy(task_id, resp.text, metadata)
```

---

## 8 调用链路总览

```
config.py (Settings)
    │
    │  startup: inject credentials from env / config files
    │
    ▼
factory.py (get_llm_provider)
    │
    │  llm_provider setting
    │
    ├──→ AnthropicLLMProvider  ← anthropic_api_key / auth_token / base_url
    ├──→ OpenAILLMProvider    ← openai_api_key / base_url
    └──→ MockLLMProvider      ← (无外部依赖)

    │
    ▼
prompts.py (STRATEGY_GENERATION_* / STRATEGY_METADATA_*)
    │  user NL description + risk_profile + market
    │
    ▼
strategy_generation.py (StrategyGenerationService.run_pipeline)
    │
    ├──→ Stage 1: agent_orchestrator.dispatch("research")
    ├──→ Stage 2: provider.generate() / generate_structured()
    ├──→ Stage 3: AST.parse()
    ├──→ Stage 4: mock_backtest()
    ├──→ Stage 5: risk_check()
    └──→ Stage 6: persist()

agent_orchestrator.py (AgentOrchestrator)
    │
    ├──→ dispatch() → AgentTask（持久化）
    ├──→ complete_task()
    └──→ send_message() → AgentMessage
```

---

## 9 环境变量快速参考

| 变量 | 适用 Provider | 说明 |
|---|---|---|
| `LLM_PROVIDER` | 通用 | 提供商选择：`anthropic` / `openai` / `mock` |
| `ANTHROPIC_API_KEY` | Anthropic | 标准 API Key |
| `ANTHROPIC_AUTH_TOKEN` | Anthropic | Bearer Token（Kimi 代理） |
| `ANTHROPIC_BASE_URL` | Anthropic | 自定义端点 |
| `ANTHROPIC_MODEL` | Anthropic | 模型 ID（默认 claude-sonnet-4-6） |
| `OPENAI_API_KEY` | OpenAI | 标准 API Key |
| `OPENAI_BASE_URL` | OpenAI | 自定义端点 |
| `OPENAI_MODEL` | OpenAI | 模型 ID（默认 gpt-4o） |
| `LLM_TIMEOUT_SECONDS` | 通用 | 超时（默认 120s） |
| `LLM_MAX_TOKENS` | 通用 | 最大 Token 数（默认 4096） |
