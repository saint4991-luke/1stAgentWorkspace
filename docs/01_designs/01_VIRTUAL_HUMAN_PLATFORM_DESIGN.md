# 🎭 虛擬人平台設計

**版本：** v2.0  
**日期：** 2026-04-16  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- 虛擬人平台的整體設計理念與架構
- 七大核心模組的職責與協作方式
- 模組間的數據流與互動關係

---

## 1. 平台概述

### 設計理念

虛擬人平台致力於打造**有溫度、有個性、有知識**的對話體驗，通過七大核心模組的緊密協作，實現：

- ✅ **快速回應** - 安撫話語 < 1 秒發送
- ✅ **個性化** - 每個虛擬人都有獨特風格
- ✅ **專業知識** - 知識庫支撐準確回答
- ✅ **會話管理** - 獨立 Session 追蹤對話歷史
- ✅ **擴展能力** - Tool 系統支持功能擴展
- ✅ **多端適配** - 前端模組支持多種 UI 場景
- ✅ **多 Provider** - 支持 LLM Provider 切換

### 七大核心模組

```
┌─────────────────────────────────────────────────────────┐
│                    虛擬人平台                            │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  AGENT   │  │ PERSONA  │  │ SESSION  │              │
│  │  代理    │  │  角色    │  │  會話    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │KNOWLEDGE │  │   TOOL   │  │  前端    │  │  LLM   │ │
│  │  知識庫  │  │   工具   │  │  Frontend│  │Provider│ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 七大模組詳解

### 2.1 AGENT（代理層）

**職責：** 執行對話 Workflow，整合 LLM1/LLM2、RAG 檢索、Persona 風格

**核心特點：**
- **雙 LLM 架構** - LLM1 負責快速回應 + RAG 判斷，LLM2 負責完整回答
- **風格支援** - LLM1/LLM2 都支援 Persona 風格和 VH 輸出格式
- **快速回應** - 安撫話語 < 1 秒發送，提升用戶體驗
- **RAG 特製** - 兩階段檢索（Meta 判斷 → 文件載入）→ **串行處理**
- **STREAM 模式** - 分段發送回答，支持 emotion/lang 標籤

**工作流程：**
```
用戶輸入
   │
   ▼
┌─────────────────┐
│ LLM1 判斷        │ ⏱️ 2-5 秒
│ - 是否需要 RAG   │
│ - 生成安撫話語   │
└─────────────────┘
   │
   ▼
⚡ 立即發送安撫話語  ← 關鍵！< 100ms
   │
   ▼ (串行)
┌─────────────────┐
│ 載入相關文件     │
│ (如果需要)       │
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ LLM2 生成回答    │
│ - 完整內容       │
│ - emotion/lang   │
└─────────────────┘
   │
   ▼
返回完整回答
```

**相關規格：**
- [03_specs/02_AGENT_WORKFLOW.md](../03_specs/02_AGENT_WORKFLOW.md) - Agent Workflow 規格
- [03_specs/07_OUTPUT_FORMAT.md](../03_specs/07_OUTPUT_FORMAT.md) - 輸出格式規格

---

### 2.2 PERSONA（角色設定）

**職責：** 定義虛擬人的個性、風格、語言特徵

**核心特點：**
- **風格 Prompt** - 通過 YAML 配置定義虛擬人個性
- **多角色支持** - 同時運行多個虛擬人
- **輸出格式** - 統一 SPEC v2.0 格式（含 emotion/lang 標籤）
- **綁定 Session** - 每個 Session 綁定一個 Persona ID

**配置結構：**
```
workspace/personas/
└── ubichan/
    ├── config.yaml       # YAML v2.0 配置
    └── style.md          # 風格 Prompt
```

**config.yaml 範例：**
```yaml
# 基本設定
persona_id: ubichan
display_name: 優必醬

# 風格定義
style:
  file: style.md

# 輸出格式
output_format: virtual_human

# 知識庫設定
knowledge:
  enabled: true
  folders:
    - ubitus/

# 工具設定
tools:
  enabled: false
  available: []

# Metadata
metadata:
  version: "2.0"
  persona_type: virtual_idol
  company: 優必達
  tone: cheerful friendly
```

**相關規格：**
- [03_specs/02_PERSONA_SPEC.md](../03_specs/02_PERSONA_SPEC.md) - Persona 配置規格
- [03_specs/07_OUTPUT_FORMAT.md](../03_specs/07_OUTPUT_FORMAT.md) - 輸出格式規格

---

### 2.3 SESSION（會話管理）

**職責：** 管理獨立對話會話，追蹤對話歷史與 Metadata

**核心特點：**
- **獨立 Session** - 每個對話擁有獨立 Session ID
- **TTL 過期** - 支持自動過期清理（背景任務）
- **Metadata 擴展** - 命名空間設計，支持自定義數據
- **持久化存儲** - SQLite 存儲，支持重啟恢復

**Session 結構：**
```json
{
  "session_id": "vh_abc123",
  "prefix": "vh",
  "metadata": {
    "persona_id": "ubichan",
    "vh_char_config": {
      "persona_id": "ubichan",
      "character_version": "v2.0"
    }
  },
  "created_at": "2026-04-16T08:00:00Z",
  "messages": [
    {"role": "user", "content": "你好", "timestamp": "2026-04-16T08:00:00Z"},
    {"role": "assistant", "content": "嗨～我是優必醬！", "timestamp": "2026-04-16T08:00:01Z"}
  ]
}
```

**API 端點：**
- `POST /sessions` - 創建 Session
- `GET /sessions/{session_id}` - 查詢 Session
- `DELETE /sessions/{session_id}` - 刪除 Session
- `GET /sessions/{session_id}/messages` - 查詢消息歷史

**相關規格：**
- [03_specs/03_SESSION_API_SPEC.md](../03_specs/03_SESSION_API_SPEC.md) - Session API 規格
- [03_specs/04_SESSION_SDK_SPEC.md](../03_specs/04_SESSION_SDK_SPEC.md) - Session SDK 規格

---

### 2.4 KNOWLEDGE（知識庫）

**職責：** 提供專業知識支撐，支持準確回答

**核心特點：**
- **兩階段檢索** - Meta 判斷（快）+ 文件載入（準）
- **通關密語** - 口語觸發知識庫管理（安全機制）
- **多格式支持** - TXT、Markdown、PDF（擴展中）
- **自動 Tool** - LLM 自動判斷何時呼叫知識庫

**知識庫結構：**
```
knowledge/
└── ubitus/
    ├── meta.json           # 自動生成，文件索引
    ├── company.txt         # 公司資訊
    ├── products.txt        # 產品介紹
    └── faq.txt             # 常見問題
```

**meta.json 範例：**
```json
{
  "version": "1.0",
  "generated_at": "2026-04-02T07:10:00Z",
  "knowledge_id": "ubitus",
  "files": [
    {
      "name": "products.txt",
      "summary": "優必達產品線完整介紹：UbiGPT、UbiAnchor、UbiArt、Ubi-chan、UbiONE",
      "keywords": ["產品", "UbiGPT", "UbiAnchor", "AI 對話", "雲端遊戲"],
      "size_bytes": 911,
      "line_count": 32
    },
    {
      "name": "company.txt",
      "summary": "優必達公司介紹：成立時間、總部地點、核心技術、聯絡資訊",
      "keywords": ["公司", "優必達", "Ubitus", "雲端串流"],
      "size_bytes": 686,
      "line_count": 25
    }
  ]
}
```

**檢索流程：**
```
用戶問題
   │
   ▼
階段 1：讀取 meta.json
LLM 判斷相關文件
   │
   ▼
階段 2：載入相關文件
完整內容檢索
   │
   ▼
LLM 基於知識庫回答
```

**相關規格：**
- [03_specs/06_KNOWLEDGE_SPEC.md](../03_specs/06_KNOWLEDGE_SPEC.md) - Knowledge 系統規格
- [02_guides/03_KNOWLEDGE_GUIDE.md](../02_guides/03_KNOWLEDGE_GUIDE.md) - 知識庫管理指南

---

### 2.5 TOOL（工具系統）

**職責：** 擴展虛擬人能力，支持外部 API 調用與功能擴展

**核心特點：**
- **Persona 授權** - 每個虛擬人可配置不同的可用工具
- **安全機制** - 通關密語保護敏感操作
- **可擴展** - 支持自定義 Tool 開發

**內建 Tool：**
| Tool 名稱 | 功能 | 說明 |
|-----------|------|------|
| `rebuild_knowledge_meta` | 重新生成知識庫 Meta | 需要通關密語保護 |

**未來擴展：**
- 外部 API 調用（天氣、新聞、股票）
- 數據庫查詢
- 文件處理（PDF、Excel）
- 自定義腳本執行

**Persona 配置：**
```yaml
tools:
  enabled: true
  available:
    - rebuild_knowledge_meta
    - weather_api
    - database_query
```

**相關規格：**
- [03_specs/06_KNOWLEDGE_SPEC.md](../03_specs/06_KNOWLEDGE_SPEC.md) - Knowledge 系統規格
- [03_specs/09_TOOL_SPEC.md](../03_specs/09_TOOL_SPEC.md) - Tool 系統規格

---

### 2.6 前端（Frontend）

**職責：** 提供用戶介面，支持多種場景適配

**核心特點：**
- **多端適配** - Web UI、管理員前端、虛擬人前端
- **STREAM 支持** - 實時顯示回答片段
- **emotion/lang 渲染** - 根據標籤調整 UI 表現
- **Session 管理** - 前端可創建/切換 Session

**前端類型：**
| 類型 | 場景 | 特點 |
|------|------|------|
| Web UI | 一般用戶對話 | 簡單易用，支持 STREAM |
| 管理員前端 | 內部測試/調試 | 完整功能，日誌查看 |
| 虛擬人前端 | 品牌場景 | 客製化 UI，頭像顯示 |

**STREAM 事件處理：**
```javascript
// 前端 STREAM 事件監聽
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'text_chunk') {
    if (data.is_comforting) {
      // 顯示安撫話語（立即）
      showComfortingWords(data.text);
    } else {
      // 追加回答片段
      appendAnswer(data.text);
    }
  }
  
  if (data.type === 'done') {
    // 顯示 emotion/lang 標籤
    applyEmotion(data.emotion);
    applyLang(data.lang);
  }
};
```

**相關規格：**
- [03_specs/01_AGENT_API_SPEC.md](../03_specs/01_AGENT_API_SPEC.md) - Agent API 規格（含 Virtual Human 端點）

---

### 2.7 LLM Provider（模型層）

**職責：** 統一 LLM 接口，支持多 Provider 切換

**核心特點：**
- **多 Provider 支援** - OpenAI 兼容接口、Ubisage 專屬接口
- **統一接口** - `chat()` 和 `chat_stream()` 方法
- **靈活配置** - 通過環境變數切換 Provider

**支援 Provider：**
| Provider | 說明 | 配置方式 |
|----------|------|----------|
| **openai** | OpenAI 兼容接口 | `OPENAI_BASE_URL`, `OPENAI_API_KEY` |
| **ubisage** | Ubisage 專屬接口 | `UBISAGE_API_KEY`, `UBISAGE_GRANT_URL` |

**常見部署配置：**
- UBITES DIRECT (VLLM) - 通過 `openai` Provider
- QWEN (VLLM) - 通過 `openai` Provider
- UBISAGE - 通過 `ubisage` Provider

**接口方法：**
```python
chat(messages)              # 非流式
chat_stream(messages)       # 流式
```

---

## 3. 模組協作流程

### 完整對話流程

```
┌─────────────────────────────────────────────────────────┐
│ 1. 用戶輸入                                              │
│    「優必達有哪些產品？」                                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 2. AGENT - LLM1 判斷                                     │
│    - 判斷需要 RAG（knowledge_ids: ["ubitus"]）          │
│    - 生成安撫話語：「我幫你查查優必達的產品資訊！」      │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ⚡ 立即發送安撫話語
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 3. KNOWLEDGE - 載入相關文件                              │
│    - products.txt                                       │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 4. PERSONA - 載入風格 Prompt                             │
│    - 親切、活潑語氣                                     │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 5. AGENT - LLM2 生成完整回答                             │
│    輸入：Persona 風格 + 知識庫內容 + 用戶問題            │
│    輸出：完整回答 + emotion/lang 標籤                    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 6. SESSION - 保存對話歷史                                │
│    - 保存用戶輸入                                        │
│    - 保存助手回答                                        │
│    - 更新 Metadata（如有需要）                           │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 7. 前端 - 顯示回答                                       │
│    - STREAM 分段顯示                                     │
│    - 應用 emotion/lang 樣式                              │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 技術架構

### Docker 容器架構

```
┌─────────────────────────────────────────────────────────┐
│              Agent API 容器 (Port 8000)                  │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  AGENT   │  │ PERSONA  │  │ SESSION  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │KNOWLEDGE │  │   TOOL   │  │   LLM    │              │
│  └──────────┘  └──────────┘  │ Provider │              │
│                              └──────────┘              │
│                                                         │
│  SQLite: /data/sessions.db                              │
│  Personas: /personas/*/                                 │
│  Knowledge: /knowledge/*                                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     前端 (Frontend)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ 虛擬人前端  │  │ 管理員前端  │  │  Web UI     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 目錄結構

```
agtshrimp/
├── agent/                      # Agent 層（Workflow 執行）
│   ├── agent-api-streaming.py  # 主程式
│   ├── virtual_human/          # 虛擬人端點
│   ├── rag/                    # KNOWLEDGE 模組
│   └── tools/                  # TOOL 模組
│       └── rebuild_knowledge_meta.py
├── session/                    # SESSION 模組（平行目錄）
│   ├── session_api.py
│   └── session_store.py
├── workspace/
│   └── personas/               # PERSONA 目錄
│       └── ubichan/
│           ├── config.yaml
│           └── style.md
├── knowledge/                  # KNOWLEDGE 目錄
│   └── ubitus/
│       └── meta.json
├── frontend/                   # Frontend 目錄
│   ├── chat.html
│   └── vh-chat.html
├── setup/                      # Docker 部署
└── docs/                       # 文檔
```

---

## 5. 設計決策與權衡

### 5.1 為什麼採用雙 LLM 架構？

**問題：** 單一 LLM 生成完整回答需要 10-30 秒，用戶體驗差。

**解決方案：** 雙 LLM 架構
- LLM1 專門生成安撫話語（2-5 秒）
- LLM2 專門生成完整回答（10-30 秒）
- 安撫話語立即發送，提升用戶體驗

**權衡：**
- ✅ 優點：用戶體驗大幅提升
- ⚠️ 缺點：增加 LLM 呼叫成本（2 次 vs 1 次）

### 5.2 為什麼採用兩階段 RAG？

**問題：** 直接載入所有文件會消耗大量 Token，增加延遲。

**解決方案：** 兩階段檢索
- 階段 1：只讀取 meta.json（小文件），LLM 判斷相關文件
- 階段 2：只載入相關文件的完整內容

**權衡：**
- ✅ 優點：節省 Token，提高檢索準確性
- ⚠️ 缺點：增加一次 LLM 呼叫（Meta 判斷）

---

## 📚 相關文檔

| 類別 | 文檔 | 說明 |
|------|------|------|
| **架構** | [02_ARCHITECTURE.md](02_ARCHITECTURE.md) | 系統架構說明 |
| **API** | [../03_specs/01_AGENT_API_SPEC.md](../03_specs/01_AGENT_API_SPEC.md) | Agent API 規格 |
| **部署** | [../02_guides/04_DEPLOYMENT_TROUBLESHOOTING.md](../02_guides/04_DEPLOYMENT_TROUBLESHOOTING.md) | Docker 部署指南 |

---

**🦐 Have fun with Virtual Human Platform!**
