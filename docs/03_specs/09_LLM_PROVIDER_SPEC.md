# 🔌 LLM Provider 規格書

**版本：** v1.0  
**日期：** 2026-04-08  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- LLM Provider 抽象層架構與接口定義
- Provider 配置與環境變數設定

---

## 📋 概述

LLM Provider 抽象層支援多種 LLM Provider，讓系統可以靈活切換不同的 LLM 服務。

---

## 🏗️ 系統架構

### Provider 抽象層

```
┌─────────────────────────────────────────────────────────┐
│                    Agent API                             │
│                     (调用层)                              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  LLM Provider                            │
│                   (抽象层)                               │
└─────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌──────────────────┐                  ┌──────────────────┐
│   OpenAI         │                  │   Ubisage        │
│   Provider       │                  │   Provider       │
└──────────────────┘                  └──────────────────┘
```

---

## 🔌 支援的 Provider

| Provider | 說明 | 認證方式 | 適用場景 |
|----------|------|----------|----------|
| **OpenAI** | OpenAI 相容 API | API Key | 一般對話、虛擬人 |
| **Ubisage** | Ubisage 私有模型 | Token 交換 | 企業內部使用 |

---

## ⚙️ 環境變數配置

### 基礎配置

```bash
# 選擇 Provider
LLM_PROVIDER=openai

# 模型配置
LLM_MODEL=Qwen/Qwen3.5-397B-A17B-FP8
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
```

### Reasoning/Thinking 配置原則

**重要：** 為了快速回應，LLM1 和 LLM2 都**必須關掉 reasoning/thinking 功能**。

**原因：**
- 關閉 reasoning/thinking 可提升回應速度約 30-50%
- 安撫話語需要 < 1 秒內發送
- 一般對話不需要複雜推理

**注意：** 每個 LLM Provider 關掉 reasoning/thinking 的方式可能不同，請參考各 Provider 的文檔。

**配置範例（僅供參考）：**
```bash
# vLLM Provider 範例
LLM_ENABLE_THINKING=false

# 或其他 Provider 的對應配置
# （具體配置方式依 Provider 而異）
```

### OpenAI Provider

```bash
LLM_PROVIDER=openai
OPENAI_BASE_URL=http://116.50.47.234:8081/v1
OPENAI_API_KEY=your-api-key
```

**欄位說明：**
| 欄位 | 必填 | 說明 |
|------|------|------|
| `OPENAI_BASE_URL` | ✅ | OpenAI 相容 API 基礎 URL |
| `OPENAI_API_KEY` | ✅ | API 金鑰 |

### Ubisage Provider

```bash
LLM_PROVIDER=ubisage
UBISAGE_API_KEY=your-api-key
UBISAGE_GRANT_URL=https://sage-stg.ubitus.ai/ubillm/api/v1/resource/grant
UBISAGE_MODEL=qwen3-8b-fp8
```

**欄位說明：**
| 欄位 | 必填 | 說明 |
|------|------|------|
| `UBISAGE_API_KEY` | ✅ | Ubisage API Key（用於換 Token） |
| `UBISAGE_GRANT_URL` | ✅ | Token 交換 API URL |
| `UBISAGE_MODEL` | ✅ | 模型名稱（e.g., `qwen3-8b-fp8`） |

**認證流程：**
1. 使用 API Key 向 `/ubillm/api/v1/resource/grant` 請求 Token
2. 獲取 `api_token` 和 `api_endpoint`
3. 使用 Token 呼叫 `{api_endpoint}/v1/chat/completions`
4. Token 一次性使用，每次請求前都要重新獲取

---

## 🔄 Provider 切換流程

### 1. 修改環境變數

```bash
# 編輯 .env 檔案
vi .env

# 修改 Provider
LLM_PROVIDER=openai  # 或 ubisage
```

### 2. 重啟服務

```bash
# Docker Compose
docker compose restart agent

# 或重新部署
docker compose down
docker compose up -d
```

### 3. 驗證切換

```bash
curl http://localhost:8000/health

# 回應應包含 provider 資訊
{
  "provider": "openai",
  "model": "Qwen/Qwen3.5-397B-A17B-FP8"
}
```

---

## 🔐 認證機制

### OpenAI Provider

- **認證方式：** API Key
- **傳遞方式：** HTTP Header `Authorization: Bearer {API_KEY}`
- **有效期：** 永久（除非撤銷）

### Ubisage Provider

- **認證方式：** API Key + Token 交換
- **流程：**
  1. POST `/ubillm/api/v1/resource/grant` → 獲取 `api_token` 和 `api_endpoint`
  2. POST `{api_endpoint}/v1/chat/completions` → 使用 Token 呼叫 LLM API
  3. Token 一次性使用，每次請求前都要重新獲取
- **Token 有效期：** 一次性（每次請求前重新獲取）

---

## 📝 使用範例

### Python 調用

```python
from agent.llm.provider import get_provider

# 獲取 Provider 實例
provider = get_provider()

# 調用 LLM
response = provider.chat(
    messages=[{"role": "user", "content": "你好"}],
    temperature=0.7,
    max_tokens=500
)

print(response.content)
```

### 環境變數範例

```bash
# .env 檔案範例

# Provider 選擇
LLM_PROVIDER=openai

# OpenAI 配置
OPENAI_BASE_URL=http://116.50.47.234:8081/v1
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 模型配置
LLM_MODEL=Qwen/Qwen3.5-397B-A17B-FP8
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
```

### Ubisage Provider 範例

```bash
# .env 檔案範例（Ubisage）

# Provider 選擇
LLM_PROVIDER=ubisage

# Ubisage 配置
UBISAGE_API_KEY=your-ubisage-api-key
UBISAGE_GRANT_URL=https://sage-stg.ubitus.ai/ubillm/api/v1/resource/grant
UBISAGE_MODEL=qwen3-8b-fp8

# 模型配置
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
```

---

## ⚠️ 注意事項

1. **切換 Provider 需重啟服務**
2. **確保環境變數正確配置**
3. **API Key 需妥善保管，不要提交到版本控制**
4. **Ubisage Provider 需要網絡可訪問認證服務**

---

## 🧠 Reasoning/Thinking 配置

### vLLM Thinking 控制

vLLM 支援通過 `chat_template_kwargs` 控制 reasoning/thinking 功能：

```python
# 禁用 thinking（預設）
extra_body={"chat_template_kwargs": {"enable_thinking": False}}

# 啟用 thinking
extra_body={"chat_template_kwargs": {"enable_thinking": True}}
```

### 配置方式

**通過環境變數：**
```bash
LLM_ENABLE_THINKING=false  # 預設值
```

**代碼實作：**
```python
# llm_providers.py
response = client.chat.completions.create(
    model=model,
    messages=messages,
    extra_body={
        "chat_template_kwargs": {
            "enable_thinking": False  # 從環境變數讀取
        }
    }
)
```

### Thinking 的影響

| 配置 | 回應速度 | Token 用量 | 適用場景 |
|------|----------|------------|----------|
| `enable_thinking: false` | 快（< 5 秒） | 較少 | 一般對話、虛擬人 |
| `enable_thinking: true` | 慢（10-30 秒） | 較多 | 複雜推理、數學問題 |

### 推薦配置

**虛擬人場景：**
```bash
LLM_ENABLE_THINKING=false
```

**原因：**
- 虛擬人需要快速回應（< 1 秒安撫話語）
- 一般對話不需要複雜推理
- 節省 Token 用量

---

## 🔗 相關文件

- [部署指南](../02_guides/04_DEPLOYMENT_TROUBLESHOOTING.md) - 環境變數配置
- [Agent API 規格](01_AGENT_API_SPEC.md) - API 端點
- [Persona 規格](02_PERSONA_SPEC.md) - 虛擬人配置

---

---

**文檔結束**
