# 蝦米 Agent - 虛擬人產品線

> 🦐 基於蝦米 Agent v4.0.1 擴展，專注於虛擬人/虛擬客服/虛擬護士場景

**版本:** v4.0.1  
**日期:** 2026-04-17  
**Branch:** `agent-ubichan`

---

## 📋 概述

本專案在蝦米 Agent 基礎上擴展了 **虛擬人對話系統**，支援：

- ✅ **Persona 角色系統** - 每個虛擬人有獨特的個性與風格
- ✅ **KNOWLEDGE 知識庫** - 兩階段檢索（Meta 判斷 + 文件載入）
- ✅ **Session 會話管理** - 獨立會話追蹤對話歷史
- ✅ **Docker 部署** - 一鍵啟動

---

## 🚀 快速開始

### 1. 複製專案

```bash
git clone https://github.com/srjiang/agtshrimp.git
cd agtshrimp
git checkout agent-ubichan
```

### 2. 配置環境

```bash
cd setup
cp .env.example .env
# 編輯 .env，設定你的 API Key
```

### 3. 啟動服務

```bash
docker-compose up -d --build
```

### 4. 訪問

- **Web UI:** http://localhost:5000
- **API:** http://localhost:8000
- **Health:** http://localhost:8000/health

---

## 📁 專案結構

```
agtshrimp/
├── agent/                      # Agent 核心模組
│   ├── agent-api-streaming.py  # 主程式（/chat 端點）
│   ├── llm_providers.py        # LLM Provider 接口
│   ├── llm_factory.py          # Provider 工廠
│   ├── rag/                    # RAG 知識檢索
│   │   ├── meta_generator.py   # Meta 生成器
│   │   └── knowledge_retriever.py  # 知識檢索引擎
│   ├── virtual_human/          # 虛擬人端點
│   │   ├── api.py              # /vh/chat 端點
│   │   ├── config_loader.py    # YAML 配置載入
│   │   └── spec_loader.py      # 輸出規格載入
│   ├── static/                 # 靜態資源（CSS/JS）
│   └── templates/              # HTML 模板
│       ├── chat.html           # 一般對話頁面
│       └── vh-chat.html        # 虛擬人對話頁面
│
├── session/                    # Session 會話管理（獨立模組）
│   ├── __init__.py             # 模組導出
│   ├── session_store.py        # SQLite 存儲層
│   ├── session_api.py          # FastAPI Router
│   └── session_manager_backup.py  # In-Memory 備份
│
├── workspace/                  # 工作空間
│   └── personas/               # 角色配置
│       ├── ubichan/            # 優必醬角色
│       │   ├── config.yaml     # YAML v2.0 配置
│       │   └── style.md        # 風格定義
│       ├── nurse/              # 護士姐姐角色
│       └── TEMPLATE/           # 角色範本
│
├── knowledge/                  # 知識庫目錄
│   └── ubitus/                 # 範例知識庫
│
├── config/                     # 配置文件（舊版，保留相容性）
├── data/                       # 數據庫目錄
├── downloads/                  # 下載目錄
├── setup/                      # 部署配置
│   ├── docker-compose.yml      # Docker Compose 配置
│   ├── Dockerfile              # Docker 鏡像
│   └── .env.example            # 環境變數範例
│
├── docs/                       # 文檔目錄
│   ├── README.md               # 文檔地圖
│   ├── 01_designs/             # 設計文檔
│   │   ├── 01_VIRTUAL_HUMAN_PLATFORM_DESIGN.md
│   │   └── 02_ARCHITECTURE.md
│   ├── 02_guides/              # 使用指南（工作人員用）
│   │   ├── 01_QUICKSTART.md
│   │   ├── 02_PERSONA_GUIDE.md
│   │   ├── 03_KNOWLEDGE_GUIDE.md
│   │   └── 04_DEPLOYMENT_TROUBLESHOOTING.md
│   └── 03_specs/               # 技術規格（工程師用）
│       ├── 01_AGENT_API_SPEC.md
│       ├── 02_AGENT_WORKFLOW.md
│       ├── 02_PERSONA_SPEC.md
│       ├── 03_SESSION_API_SPEC.md
│       ├── 04_SESSION_SDK_SPEC.md
│       ├── 06_KNOWLEDGE_SPEC.md
│       ├── 07_OUTPUT_FORMAT.md
│       ├── 08_LLM_PROVIDER_SPEC.md
│       ├── 09_PERFORMANCE_SPEC.md
│       └── 09_TOOL_SPEC.md
│
├── TODO.md                     # 待辦事項
└── README.md                   # 本文件
```

---

## 📚 文檔導覽

### 快速開始
- **安裝與配置** → `docs/02_guides/01_QUICKSTART.md`
- **部署與故障排除** → `docs/02_guides/04_DEPLOYMENT_TROUBLESHOOTING.md`

### 角色配置
- **Persona 設計指南** → `docs/02_guides/02_PERSONA_GUIDE.md`
- **知識庫管理** → `docs/02_guides/03_KNOWLEDGE_GUIDE.md`

### 技術規格
- **完整文檔地圖** → `docs/README.md`

---

## 🔧 開發資訊

### 技術棧
- **後端:** Python 3.10+ / FastAPI
- **前端:** HTML / JavaScript (無框架)
- **數據庫:** SQLite 3
- **部署:** Docker / Docker Compose

### 主要依賴
- `fastapi` - Web 框架
- `uvicorn` - ASGI 服務器
- `openai` - LLM 接口
- `pyyaml` - YAML 配置解析
- `aiosqlite` - SQLite 異步驅動

---

## 📝 相關連結

- **專案 Repo:** https://github.com/srjiang/agtshrimp
- **文檔地圖:** `docs/README.md`
- **技術規格:** `docs/03_specs/`

---

**最後更新:** 2026-04-17
