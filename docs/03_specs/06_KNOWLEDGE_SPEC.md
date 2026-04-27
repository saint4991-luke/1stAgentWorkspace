# 📚 Knowledge 系統規格書

**版本：** v1.0  
**日期：** 2026-04-08  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- Knowledge 系統的架構與檢索邏輯
- 知識庫存儲格式與 Meta 規格

---

## 📋 概述

Knowledge 系統提供**知識庫管理與檢索**功能：
- 多格式檔案支援（.txt, .md）
- 兩階段 Meta 檢索（LLM 判斷 + 文件載入）
- Meta 索引模式（快速判斷相關文件）
- 內部模組調用（非 HTTP API）

---

## 📐 知識庫結構

### 位置

```
/knowledge/
├── ubitus/
│   ├── meta.json          ← 必須，文件索引
│   ├── company.txt        ← 知識文件
│   ├── products.txt       ← 知識文件
│   └── faq.txt            ← 知識文件
└── ...
```

### 命名規則

- ✅ 使用小寫英文（`ubitus/`）
- ✅ 避免特殊字元（只允許 `a-z0-9_-`）
- ✅ **必須包含 `meta.json`**（檢索核心）

---

## 📄 支援的檔案格式

| 格式 | 副檔名 | 說明 |
|------|--------|------|
| 純文字 | `.txt` | 推薦格式（目前主要使用） |
| Markdown | `.md` | 支援 |

**注意：**
- ❌ 不支援 PDF（需先轉換為文字）
- ✅ 推薦使用 `.txt`（簡單、無格式問題）

---

## 🔍 META 模式

### meta.json 格式

每個知識庫**必須**包含 `meta.json`（檢索核心）：

```json
{
  "version": "1.0",
  "generated_at": "2026-04-02T07:10:00Z",
  "knowledge_id": "ubitus",
  "files": [
    {
      "name": "products.txt",
      "summary": "優必達產品線完整介紹...",
      "keywords": ["產品", "UbiGPT", "UbiAnchor"],
      "size_bytes": 911,
      "line_count": 32
    }
  ]
}
```

### meta.json 用途

| 用途 | 說明 |
|------|------|
| **快速檢索** | LLM 通過 summary 和 keywords 判斷相關文件 |
| **節省 Token** | 只讀取 meta（小文件），不載入完整內容 |
| **準確判斷** | 摘要 + 關鍵字雙重判斷，提高準確性 |

### 生成工具

```bash
python -m agent.rag.meta_generator knowledge/ubitus
```

---

## 🔎 檢索流程

### 兩階段 Meta 檢索

```
用戶問題
    ↓
┌─────────────────────────────────────────┐
│ 階段 1：讀取 meta.json（LLM 判斷）        │
│ - 載入 meta.json（含文件摘要與關鍵字）    │
│ - LLM 根據用戶問題判斷相關文件            │
│ - 返回相關文件列表                       │
│ ⏱️ 約 2-5 秒                             │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 階段 2：載入相關文件完整內容              │
│ - 根據階段 1 的文件列表載入完整內容       │
│ - 合併所有相關文件內容                   │
│ - 用於 LLM2 生成回答                     │
│ ⏱️ 可慢（不阻塞用戶）                    │
└─────────────────────────────────────────┘
    ↓
返回完整知識內容
```

**說明：**
- ❌ **不是 Vector DB** - 不使用 Embedding 或語意檢索
- ✅ **LLM 判斷** - 通過 LLM 閱讀 meta.json 的摘要與關鍵字來判斷相關性
- ✅ **快速準確** - Meta 文件小，LLM 判斷快速且準確

---

## 🔧 內部 API（Python 模組）

### KnowledgeRetriever 類

**用途：** 知識庫檢索引擎，用於 `/vh/chat` 端點的 RAG 檢索。

**初始化：**
```python
from agent.rag.knowledge_retriever import KnowledgeRetriever

# 初始化（需指定 knowledge_id 和 LLM client）
retriever = KnowledgeRetriever(
    knowledge_id="ubitus",
    base_path="/knowledge",
    llm_client=llm_service
)
```

**檢索方法：**
```python
# 兩階段檢索
result = retriever.query(question="優必達有哪些產品？")

# 返回格式
{
    "content": "知識庫完整內容（合併的相關文件）",
    "files": ["products.txt", "company.txt"],
    "used_files": ["products.txt", "company.txt"],
    "meta_used": True,
    "timings": {
        "rag_llm_ms": 755,      # 階段 1：LLM 判斷時間
        "file_read_ms": 0,      # 階段 2：文件讀取時間
        "rag_retrieve_ms": 755  # RAG 總時間
    }
}
```

---

## 📝 使用範例

### 1. 準備知識文件

```bash
# 1. 創建知識庫目錄
mkdir -p /knowledge/ubitus

# 2. 添加知識文件（.txt 或 .md）
cat > /knowledge/ubitus/products.txt << EOF
優必達產品線介紹：
- UbiGPT：AI 對話助手
- UbiAnchor：雲端遊戲平台
- UbiArt：AI 藝術生成
EOF

cat > /knowledge/ubitus/company.txt << EOF
優必達公司介紹：
成立時間：2008 年
總部：台北市松山區
EOF
```

### 2. 生成 Meta 索引

**方法一：在 /chat 中要求 LLM 生成**

與虛擬人對話，要求它幫你生成 meta：

```
用戶：幫我生成知識庫的 meta.json，通關密語：admin123
助手：好的，正在為您生成 meta.json...
```

**方法二：執行 Python 命令**

```bash
# 使用 meta_generator 模組生成
python -m agent.rag.meta_generator /knowledge/ubitus

# 輸出：
# ✅ meta.json 已生成：/knowledge/ubitus/meta.json
# 📊 處理文件：3 個
# ⏱️ 耗時：2.3 秒
```

**生成的 meta.json 格式：**
```json
{
  "version": "1.0",
  "generated_at": "2026-04-17T03:00:00Z",
  "knowledge_id": "ubitus",
  "files": [
    {
      "name": "products.txt",
      "summary": "優必達產品線完整介紹...",
      "keywords": ["產品", "UbiGPT", "UbiAnchor"],
      "size_bytes": 911,
      "line_count": 32
    },
    {
      "name": "company.txt",
      "summary": "優必達公司介紹...",
      "keywords": ["公司", "優必達", "成立時間"],
      "size_bytes": 686,
      "line_count": 25
    }
  ]
}
```

### 3. 知識庫檢索

知識庫會在 `/vh/chat` 端點自動使用：

```bash
# 創建虛擬人 Session（啟用知識庫）
curl -X POST http://localhost:8000/vh/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "persona_id": "ubichan",
    "knowledge_ids": ["ubitus"]
  }'

# 發送對話（自動檢索知識庫）
curl -X POST http://localhost:8000/vh/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "vh_abc123",
    "messages": [{"role": "user", "content": "優必達有哪些產品？"}]
  }'
```

---

## ⚠️ 注意事項

1. **知識庫更新後需重新生成 meta.json**
2. **meta.json 必須存在** - 否則無法進行檢索
3. **使用 .txt 格式** - 推薦使用純文字格式，避免格式問題

---

**文檔結束**
