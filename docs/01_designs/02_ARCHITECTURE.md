# 🏗️ AgentShrimp 系統架構

**版本：** v1.2  
**最後更新：** 2026-04-16  
**適用對象：** 開發者、系統架構師

---

## 🎯 文件職責

**本文檔說明：**
- AgentShrimp 平台的整體系統架構
- 核心模組組成與職責
- 模組間的關係與數據流
- 技術選型與設計決策

**本文檔不包含：**
- API 格式規格（→ `03_specs/`）
- 配置說明（→ `02_guides/`）
- 產品理念（→ `01_VIRTUAL_HUMAN_PLATFORM_DESIGN.md`）

---

## 📊 系統概覽

### 7 大核心模組

```
┌─────────────────────────────────────────────────────────┐
│                    AgentShrimp 平台                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ 前端層    │  │ Agent 層  │  │ Persona 層│  │Session │ │
│  │Frontend  │─▶│ Agent    │─▶│ Persona  │  │Layer   │ │
│  │          │◀─│          │◀─│          │  │        │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│       │              │              │            │      │
│       │              ▼              │            │      │
│       │       ┌──────────────┐     │            │      │
│       │       │  知識庫層     │     │   ┌──────────┐   │
│       │       │ (Knowledge)  │     │   │ TOOL 層   │   │
│       │       └──────────────┘     │   │(Tools)   │   │
│       │              │             │   └──────────┘   │
│       ▼              ▼             ▼            ▼      │
│  ┌──────────────────────────────────────────────────┐  │
│  │              LLM Provider 層                      │  │
│  │          (openai / ubisage)                      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🏛️ 模組詳細說明

### 1. 前端層 (frontend/)

**職責：** 用戶界面、SSE 串流接收、會話管理

**核心文件：**
```
frontend/
├── chat.html          # 一般對話頁面
├── chat.js            # 一般對話邏輯
├── vh-chat.html       # 虛擬人對話頁面
└── vh-chat.js         # 虛擬人對話邏輯
```

**功能：**
- 用戶輸入與訊息顯示
- SSE 串流接收與渲染
- Session 創建/刪除/切換
- 虛擬人風格選擇

**技術棧：**
- 純 HTML + JavaScript（無框架）
- EventSource API（SSE）
- Fetch API（HTTP 請求）

---

### 2. Agent 層 (agent/)

**職責：** Workflow 執行、整合各模組

**核心文件：**
```
agent/
├── agent-api-streaming.py   # /chat 端點（一般對話）
├── stream_events.py         # SSE 事件定義
├── llm_providers.py         # LLM Provider 接口
├── llm_factory.py           # Provider 工廠
├── rag/                     # RAG 檢索模組
│   ├── meta_generator.py    # Meta 生成器
│   └── knowledge_retriever.py  # 知識檢索
└── virtual_human/           # 虛擬人 Workflow
    ├── api.py               # /vh/chat 端點
    ├── config_loader.py     # YAML 配置載入
    ├── spec_loader.py       # 輸出規格載入
    └── specs/               # 輸出規格文件
        └── virtual-human-output-spec.md
```

**核心功能（Workflow 特點）：**

#### 2.1 使用 Session
- 從 Session 層獲取對話歷史
- 將新訊息存儲回 Session
- 支援多 Session 切換

#### 2.2 為 Knowledge 特化（LLM1/LLM2 兩階段流程）
- **階段 1：** 讀取 meta.json，LLM1 判斷相關文件
- **階段 2：** 載入相關文件完整內容
- **優勢：** 節省 Token、語意理解

#### 2.3 快速回應（LLM1 STREAM 模式）
- **目標：** <1 秒內返回第一句話
- **限制：** <20 字，一句話
- **用途：** 安撫用戶、快速反饋
- **實現：** `chat_stream()` + 早期截斷

#### 2.4 Tool 使用
- **目前：** `/chat` 端點支援 Tool
- **未來：** `/vh/chat` 將加入 Tool
- **類型：** 知識庫管理、外部 API 等

#### 2.5 風格導入
- 從 Persona 層載入風格配置
- 應用於 `/vh/chat` 端點
- 透過 `_build_prompt()` 組建

---

### 3. Persona 層 (workspace/personas/)

**職責：** 角色設定與資源管理

**核心結構：**
```
workspace/personas/{persona_id}/
├── style.md           # 角色風格定義
└── config.yaml        # 資源配置
```

**核心功能：**

#### 3.1 角色設定（style.md）
- 定義角色個性
- 定義說話風格
- 定義口頭禪與用詞習慣

#### 3.2 資源配置（config.yaml）
```yaml
persona_id: ubichan
display_name: 優必醬

style:
  file: style.md

output_format: virtual_human

knowledge:
  enabled: true
  folders:
    - ubitus/

tools:
  enabled: false
  available: []
```

#### 3.3 知識庫授權
- `knowledge.folders` 指定可訪問的知識庫
- 支援多知識庫關聯
- 一對多、多對一關係

#### 3.4 Tool 授權
- `tools.available` 指定可用工具
- 保留擴充（未來功能）

#### 3.5 輸出格式
- `output_format` 選擇輸出規格
- `virtual_human`：情緒標籤 + 語言標籤 + 斷句
- `chat`：純文字回應

---

### 4. Session 層 (session/)

**職責：** 對話歷史管理、持久化存儲、HTTP API

**核心文件：**
```
session/
├── __init__.py              # 模組導出
├── session_store.py         # SQLite 存儲層（主版本）
├── session_api.py           # FastAPI Router
├── session_manager_backup.py # In-Memory 版本（備份）
└── tools/
    └── query_session.py     # Session 查詢工具
```

**功能：**
- Session 創建/刪除/查詢
- 訊息添加（含 emotion、lang 標籤）
- TTL 自動清理
- HTTP API 接口

**存儲：**
- **主版本：** SQLite（持久化）
- **備份：** In-Memory（參考用）

**API 端點：**
```
POST   /sessions          # 創建 Session
GET    /sessions          # 列出 Sessions
GET    /sessions/{id}     # 獲取 Session
DELETE /sessions/{id}     # 刪除 Session
```

---

### 5. 知識庫層 (knowledge/)

**職責：** 領域知識存儲、RAG 檢索來源

**結構：**
```
knowledge/
└── {knowledge_id}/
    ├── meta.json           # 【自動生成】文件索引
    ├── file1.txt           # 知識內容
    ├── file2.md
    └── ...
```

**Meta 格式：**
```json
{
  "version": "1.0",
  "generated_at": "2026-04-16",
  "knowledge_id": "ubitus",
  "files": [
    {
      "name": "company.txt",
      "summary": "公司介紹...",
      "keywords": ["公司", "優必達"],
      "size_bytes": 686,
      "line_count": 25
    }
  ]
}
```

**生成工具：**
```bash
python -m agent.rag.meta_generator knowledge/ubitus
```

---

### 6. TOOL 層 (agent/tools/)

**職責：** 擴展虛擬人能力，支持外部 API 調用與功能擴展

**核心文件：**
```
agent/tools/
├── __init__.py              # 模組導出
└── rebuild_knowledge_meta.py # 知識庫 Meta 重新生成
```

**功能：**
- 知識庫管理（rebuild_knowledge_meta）
- 外部 API 調用（未來擴展）
- 數據庫查詢（未來擴展）
- 文件處理（未來擴展）

**Persona 授權：**
```yaml
tools:
  enabled: true
  available:
    - rebuild_knowledge_meta
    - weather_api
    - database_query
```

**安全機制：**
- 通關密語保護敏感操作
- 每個虛擬人可配置不同的可用工具

---

### 6. LLM Provider 層

**職責：** 統一 LLM 接口、多 Provider 支援

**核心文件：**
```
agent/
├── llm_providers.py       # LLM Provider 接口
└── llm_factory.py         # Provider 工廠
```

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

## 🔄 數據流

### 對話流程（/vh/chat）

```
1. 用戶輸入
   │
   ▼
2. 前端 → Agent API (POST /vh/chat)
   │
   ▼
3. Agent → Session 獲取對話歷史
   │
   ▼
4. Agent → Persona 載入配置
   │
   ├─→ style.md（風格）
   ├─→ output_format（輸出格式）
   └─→ knowledge.folders（授權）
   │
   ▼
5. Agent → 知識庫 meta.json 檢索
   │
   ▼
6. Agent → 組建 Prompt（5 部分）
   │
   ├─→ System Prompt
   ├─→ Style Prompt
   ├─→ Output Spec
   ├─→ Knowledge
   └─→ Conversation History
   │
   ▼
7. LLM1 → 快速回應（STREAM, <20 字）
   │
   ▼
8. Agent → 前端 SSE 發送
   │
   ├─→ stream_start
   ├─→ stream_token (×N)
   ├─→ stream_end
   └─→ session_updated
   │
   ▼
9. Agent → Session 存儲訊息
   │
   ▼
10. LLM2 → 完整回應（背景）
   │
   ▼
11. Agent → Session 存儲完整回應
```

### RAG 檢索流程

```
1. 用戶問題
   │
   ▼
2. 讀取 meta.json（所有知識庫）
   │
   ▼
3. LLM1 判斷相關文件
   │
   ▼
4. 載入相關文件完整內容
   │
   ▼
5. 組建 Prompt（含知識）
   │
   ▼
6. LLM 基於知識庫回答
```

### Session 管理流程

```
1. 創建 Session
   │
   ├─→ 生成 Session ID ({PREFIX}_{uuid})
   ├─→ 存入 SQLite (sessions.db)
   └─→ 返回 {session_id, metadata}
   │
2. 添加訊息
   │
   ├─→ 寫入 messages 表
   ├─→ 包含 emotion、lang 標籤
   └─→ 更新 last_active
   │
3. 獲取歷史
   │
   ├─→ 查詢 messages 表
   ├─→ 限制最近 N 條
   └─→ 返回 List[Dict]
   │
4. TTL 清理
   │
   ├─→ 定期掃描過期 Session
   └─→ 自動刪除
```

---

## 🏗️ 目錄結構

### 完整專案結構

```
agent-shrimp/
├── agent/                          # Agent 層（Workflow 執行）
│   ├── agent-api-streaming.py      # /chat 端點
│   ├── stream_events.py            # SSE 事件
│   ├── llm_providers.py            # LLM 接口
│   ├── llm_factory.py              # Provider 工廠
│   ├── rag/                        # RAG 檢索
│   │   ├── meta_generator.py
│   │   └── knowledge_retriever.py
│   ├── virtual_human/              # 虛擬人 Workflow
│   │   ├── api.py
│   │   ├── config_loader.py
│   │   ├── spec_loader.py
│   │   └── specs/
│   │       └── virtual-human-output-spec.md
│   └── tools/                      # TOOL 層
│       ├── __init__.py
│       └── rebuild_knowledge_meta.py
│
├── session/                        # Session 層（平行）
│   ├── __init__.py
│   ├── session_store.py            # SQLite 存儲
│   ├── session_api.py              # FastAPI Router
│   ├── session_manager_backup.py   # In-Memory 備份
│   └── tools/
│       └── query_session.py
│
├── frontend/                       # 前端層（靜態）
│   ├── chat.html
│   ├── chat.js
│   ├── vh-chat.html
│   └── vh-chat.js
│
├── workspace/
│   └── personas/                   # Persona 層（角色設定）
│       ├── ubichan/
│       │   ├── style.md            # 角色風格
│       │   └── config.yaml         # 資源配置
│       ├── nurse/
│       │   ├── style.md
│       │   └── config.yaml
│       └── TEMPLATE/
│           ├── style.md
│           └── config.yaml
│
├── knowledge/                      # 知識庫層（外部掛載）
│   └── ubitus/
│       ├── meta.json
│       └── *.txt
│
├── setup/
│   ├── docker-compose.yml
│   └── Dockerfile
│
└── docs/                           # 文檔
    ├── 01_designs/
    │   ├── 01_VIRTUAL_HUMAN_PLATFORM_DESIGN.md
    │   └── 02_ARCHITECTURE.md      ← 本文件
    ├── 03_specs/
    ├── 02_guides/
    ├── 04_reference/
    ├── 05_archive/
    └── 06_study/
```

---

## 🔧 技術選型

### 後端
- **語言：** Python 3.10+
- **框架：** FastAPI
- **數據庫：** SQLite 3
- **LLM 接口：** OpenAI 兼容

### 前端
- **技術：** 純 HTML + JavaScript
- **通訊：** SSE (EventSource) + Fetch API
- **無框架：** 輕量、易維護

### 部署
- **容器：** Docker + Docker Compose
- **掛載：** 知識庫、Persona 配置

---

## 📊 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.2 | 2026-04-16 | Session 模組獨立、前端清理 |
| v1.1 | 2026-04-15 | STREAM 模式、SSE 修復 |
| v1.0 | 2026-04-01 | 初始版本 |

---

**相關文檔：**
- 產品理念：`01_VIRTUAL_HUMAN_PLATFORM_DESIGN.md`
- API 規格：`03_specs/01_AGENT_API_SPEC.md`
- 快速開始：`02_guides/01_QUICKSTART.md`
