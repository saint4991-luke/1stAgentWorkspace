# 📚 AgentShrimp 文檔地圖

**Branch:** `agent-ubichan`  
**最後更新:** 2026-04-16  
**版本:** v4.0.1 (Docker 修復)

---

## 📁 目錄結構

```
docs/
├── 01_designs/         # 設計（哲學/理念）
├── 02_specs/           # 規格（硬性規定）
├── 03_guides/          # 指南（操作手冊）
├── 04_reference/       # 參考資料（精簡為 Notes）
├── 05_archive/         # 歸檔（舊文檔）
└── 06_study/           # 研究筆記
```

---

## 📋 文檔清單

### 01_designs/ - 設計（哲學/理念）

| 檔案 | 說明 |
|------|------|
| [01_VIRTUAL_HUMAN_PLATFORM_DESIGN.md](01_designs/01_VIRTUAL_HUMAN_PLATFORM_DESIGN.md) | 虛擬人平台設計（主文檔） |
| [02_ARCHITECTURE.md](01_designs/02_ARCHITECTURE.md) | 系統架構說明 |

### 02_specs/ - 規格（硬性規定）

| 檔案 | 說明 |
|------|------|
| [01_AGENT_API_SPEC.md](02_specs/01_AGENT_API_SPEC.md) | Agent API 規格 |
| [02_PERSONA_SPEC.md](02_specs/02_PERSONA_SPEC.md) | Persona 配置規格 |
| [03_SESSION_API_SPEC.md](02_specs/03_SESSION_API_SPEC.md) | Session API 規格 |
| [04_SESSION_SDK_SPEC.md](02_specs/04_SESSION_SDK_SPEC.md) | Session SDK 規格 |
| [05_VIRTUAL_HUMAN_API_SPEC.md](02_specs/05_VIRTUAL_HUMAN_API_SPEC.md) | Virtual Human API 規格 |
| [06_KNOWLEDGE_SPEC.md](02_specs/06_KNOWLEDGE_SPEC.md) | Knowledge 系統規格 |
| [07_OUTPUT_FORMAT.md](02_specs/07_OUTPUT_FORMAT.md) | 輸出格式規格 |
| [08_LLM_PROVIDER_SPEC.md](02_specs/08_LLM_PROVIDER_SPEC.md) | LLM Provider 規格 |
| [09_VH_CHAT_WORKFLOW.md](02_specs/09_VH_CHAT_WORKFLOW.md) | VH Chat 工作流程 |
| [10_STREAM_REFACTOR_SPEC.md](02_specs/10_STREAM_REFACTOR_SPEC.md) | Stream 重構規格 |
| [11_PROMPT_GENERATION_SPEC.md](02_specs/11_PROMPT_GENERATION_SPEC.md) | Prompt 生成規格 |

### 03_guides/ - 指南（操作手冊）

| 檔案 | 說明 |
|------|------|
| [01_QUICKSTART.md](03_guides/01_QUICKSTART.md) | 快速開始 |
| [02_USER_GUIDE.md](03_guides/02_USER_GUIDE.md) | 用戶使用指南 |
| [03_PERSONA_DESIGNER_GUIDE.md](03_guides/03_PERSONA_DESIGNER_GUIDE.md) | Persona 設計指南 |
| [04_KNOWLEDGE_MANAGEMENT_GUIDE.md](03_guides/04_KNOWLEDGE_MANAGEMENT_GUIDE.md) | 知識庫管理指南 |
| [05_SESSION_OPERATIONS.md](03_guides/05_SESSION_OPERATIONS.md) | Session 操作指南 |
| [06_AGENT_OPERATIONS.md](03_guides/06_AGENT_OPERATIONS.md) | Agent 操作指南 |
| [07_DEPLOYMENT_GUIDE.md](03_guides/07_DEPLOYMENT_GUIDE.md) | 部署指南 |
| [08_TOOLS_GUIDE.md](03_guides/08_TOOLS_GUIDE.md) | 工具使用指南 |
| [09_DOCKER_TROUBLESHOOTING.md](03_guides/09_DOCKER_TROUBLESHOOTING.md) | Docker 問題診斷 |

### 04_reference/ - 參考資料（Notes）

| 檔案 | 說明 |
|------|------|
| [01_KNOWLEDGE_NOTES.md](04_reference/01_KNOWLEDGE_NOTES.md) | Knowledge 系統筆記 |
| [03_API_EXAMPLES.md](04_reference/03_API_EXAMPLES.md) | API 使用範例 |
| [LLM_PROVIDER_CASES.md](04_reference/LLM_PROVIDER_CASES.md) | LLM Provider 配置案例 |
| [PERFORMANCE-ANALYSIS.md](04_reference/PERFORMANCE-ANALYSIS.md) | 性能分析報告 |
| [SESSION_API_TEST.md](04_reference/SESSION_API_TEST.md) | Session API 測試記錄 |

### 05_archive/ - 歸檔（舊文檔）

| 目錄/檔案 | 說明 |
|-----------|------|
| [old_designs/](05_archive/old_designs/) | 舊設計文檔（7 個文件） |
| [old_specs/](05_archive/old_specs/) | 舊規格文檔（4 個文件） |
| [old_reference/](05_archive/old_reference/) | 舊參考資料（2 個文件） |
| [FRONTEND_CLEANUP_REPORT.md](05_archive/FRONTEND_CLEANUP_REPORT.md) | 前端清理報告 |
| [SESSION_REFACTOR_REPORT.md](05_archive/SESSION_REFACTOR_REPORT.md) | Session 重構報告 |
| [STREAM_SPEC.md](05_archive/STREAM_SPEC.md) | 舊 Stream 規格 |

### 06_study/ - 研究筆記

| 檔案 | 說明 |
|------|------|
| （現有研究筆記） | 保持原樣 |

---

## 🚀 快速開始

### 新用戶閱讀順序

1. **01_designs/01_VIRTUAL_HUMAN_PLATFORM_DESIGN.md** → 了解平台設計理念
2. **02_specs/** → 查看 API 規格
3. **03_guides/01_USER_GUIDE.md** → 開始使用

### 開發者閱讀順序

1. **01_designs/** → 了解架構設計
2. **02_specs/** → 查看技術規格
3. **03_guides/** → 部署與工具使用

---

## 📝 文檔分類原則

| 分類 | 說明 | 特點 |
|------|------|------|
| **Designs** | 設計理念、架構思路 | 哲學性、宏觀 |
| **Specs** | 技術規格、API 定義 | 硬性規定、必須遵守 |
| **Guides** | 操作手冊、使用指南 | 實用性、步驟式 |
| **Reference** | 參考資料、筆記 | 補充說明、範例 |
| **Archive** | 舊文檔 | 歷史參考 |
| **Study** | 研究筆記 | 學習記錄 |

---

**文檔結束**
