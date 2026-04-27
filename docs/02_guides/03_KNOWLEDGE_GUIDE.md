# 📚 知識庫管理指南

**版本：** v1.0  
**最後更新：** 2026-04-16  
**適用對象：** 知識庫管理員、虛擬人設計師

---

## 🎯 文件職責

**本文檔說明：**
- 知識庫的創建、結構與管理指南
- Meta 生成與 RAG 檢索的配置說明

---

## 🚀 快速開始

### 什麼是 Knowledge（知識庫）？

**知識庫** 是系統的「專業知識來源」，為虛擬人提供：
- 公司資訊、產品介紹
- 專業領域知識（醫療、法律、技術）
- 常見問題解答（FAQ）

**單位：** 每個知識庫是一個**獨立的目錄**，放在 `/knowledge/` 下。

---

## 📁 步驟 1：創建知識庫目錄結構

### 基本結構

```
knowledge/
└── {knowledge_id}/          ← 知識庫目錄（知識庫 ID）
    ├── meta.json            ← 【自動生成】文件索引
    ├── file1.txt            ← 知識內容
    ├── file2.md
    └── ...
```

### 範例：優必達知識庫

```
knowledge/
└── ubitus/
    ├── meta.json
    ├── company.txt          # 公司介紹
    ├── products.txt         # 產品介紹
    └── faq.txt              # 常見問題
```

### 範例：多個知識庫

```
knowledge/
├── ubitus/                  # 優必達公司知識
│   ├── meta.json
│   └── *.txt
├── covid/                   # COVID 防疫知識
│   ├── meta.json
│   └── *.md
└── aiexpo2026/              # AI 展覽知識
    ├── meta.json
    └── *.txt
```

---

## 📝 步驟 2：準備知識內容

### 支援的文件格式

| 格式 | 副檔名 | 說明 | 建議 |
|------|--------|------|------|
| 純文字 | `.txt` | 最簡單，推薦使用 | ✅ 首選 |
| Markdown | `.md` | 支援格式排版 | ✅ 推薦 |
| PDF | `.pdf` | 需要額外處理 | ⚠️ 需測試 |

### 文件大小建議

- **每個文件：** < 50KB（避免單個文件過大）
- **每個知識庫：** < 200KB（總大小控制）
- **文件數量：** 每個知識庫 5-20 個文件為佳

### 內容撰寫技巧

**✅ 好的做法：**
```
- 一個文件一個主題（如：products.txt 只講產品）
- 使用清晰的標題和段落
- 包含關鍵字（便於檢索）
- 純文字或簡單 Markdown 格式
```

**❌ 避免：**
```
- 所有內容塞進一個文件
- 過於複雜的格式（表格、圖片）
- 模糊不清的描述
```

---

## 🔧 步驟 3：生成 meta.json

### 什麼是 meta.json？

**meta.json** 是知識庫的「索引文件」，包含：
- 知識庫的基本資訊
- 每個文件的摘要（由 LLM 生成）
- 每個文件的關鍵字（由 LLM 提取）

**用途：** 系統通過 meta.json 快速判斷哪些文件與用戶問題相關。

### 方法 A：使用 CLI 工具（推薦）

```bash
# 生成單一知識庫
cd /home/ubuntu/.openclaw/workspace/users/vic/agent-shrimp
python -m agent.rag.meta_generator knowledge/ubitus

# 生成所有知識庫
python -m agent.rag.meta_generator knowledge --all

# 強制重新生成（覆蓋現有 meta.json）
python -m agent.rag.meta_generator knowledge/ubitus --force
```

### 方法 B：口語命令（如果已啟用 Tool）

在對話中說：
```
"幫我整理 ubitus 的 meta，通關數字 5688"
```

系統會自動執行 meta 生成。

---

## 📋 meta.json 格式說明

### 完整範例

```json
{
  "version": "1.0",                    ← Meta 格式版本
  "generated_at": "2026-04-16T07:00:00Z",  ← 生成時間
  "knowledge_id": "ubitus",            ← 知識庫 ID
  "files": [                           ← 文件列表
    {
      "name": "company.txt",           ← 文件名
      "summary": "優必達公司介紹：成立於 2008 年，總部位於台北，專注於雲端串流技術...",  ← LLM 生成的摘要
      "keywords": ["公司", "優必達", "成立時間", "總部", "核心技術"],  ← LLM 提取的關鍵字
      "size_bytes": 686,               ← 文件大小（位元組）
      "line_count": 25                 ← 行數
    },
    {
      "name": "products.txt",
      "summary": "優必達產品線介紹：UbiGPT（AI 對話）、UbiAnchor（雲端遊戲）...",
      "keywords": ["產品", "UbiGPT", "UbiAnchor", "AI", "雲端遊戲"],
      "size_bytes": 911,
      "line_count": 32
    }
  ]
}
```

### 欄位說明

| 欄位 | 說明 | 生成方式 |
|------|------|---------|
| `version` | Meta 格式版本 | 手動設定（通常為 "1.0"） |
| `generated_at` | 生成時間 | 自動生成（ISO 8601 格式） |
| `knowledge_id` | 知識庫 ID | 自動從目錄名提取 |
| `files[].name` | 文件名 | 自動從文件列表提取 |
| `files[].summary` | 文件摘要 | LLM 生成（約 100-200 字） |
| `files[].keywords` | 關鍵字列表 | LLM 提取（5-10 個關鍵字） |
| `files[].size_bytes` | 文件大小 | 自動計算 |
| `files[].line_count` | 行數 | 自動計算 |

---

## 🔗 步驟 4：關聯知識庫到虛擬人

### 在 config.yaml 中指定

編輯 `workspace/personas/{persona_id}/config.yaml`：

```yaml
knowledge:
  enabled: true                      # 啟用知識庫
  folders:
    - ubitus/                        # 知識庫目錄（相對於 /knowledge/）
```

### 一對多關聯

一個虛擬人可以關聯多個知識庫：

```yaml
knowledge:
  enabled: true
  folders:
    - ubitus/                        # 公司知識
    - products/                      # 產品知識
    - faq/                           # 常見問題
```

### 多對一關聯

多個虛擬人可以共用同一知識庫：

```yaml
# ubichan/config.yaml
knowledge:
  folders:
    - ubitus/

# nurse/config.yaml
knowledge:
  folders:
    - ubitus/                        # 共用同一知識庫
    - medical/                       # 但護士另有醫學知識庫
```

---

## 🧪 步驟 5：測試知識庫

### 1. 檢查 meta.json 是否生成

```bash
ls -la knowledge/ubitus/meta.json
```

**預期：** 文件存在且內容完整

### 2. 測試檢索

```bash
curl -X POST http://localhost:8000/vh/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "message": "優必達有哪些產品？"
  }'
```

**預期：** 虛擬人能正確回答產品相關資訊

### 3. 檢查日誌

```bash
docker compose logs agent | grep "知識庫"
```

**預期看到：**
```
📚 取得 META 內容：1 個知識庫
📚 LLM1 獲取對話歷史：3 條
📚 已載入 2 個文件內容
```

---

## 🔄 維護與更新

### 何时需要重新生成 meta.json？

| 情境 | 是否需要重新生成 |
|------|----------------|
| 新增文件 | ✅ 需要 |
| 修改文件內容 | ✅ 需要 |
| 刪除文件 | ✅ 需要 |
| 僅修改 meta.json | ❌ 不需要（但通常沒必要） |

### 自動化建議

**使用 Git Hook（進階）：**
```bash
# .git/hooks/post-commit
#!/bin/bash
if git diff --name-only HEAD | grep -q "knowledge/"; then
    echo "检测到知識庫變更，重新生成 meta.json..."
    python -m agent.rag.meta_generator knowledge --all
fi
```

### 版本控制

- **建議：** 將 `*.txt`, `*.md` 納入 Git 管理
- **不建議：** 將 `meta.json` 納入 Git（因為會頻繁變更）

**.gitignore 範例：**
```
knowledge/*/meta.json
```

---

## 💡 最佳實踐

### 1. 知識庫組織

**✅ 好的做法：**
```
knowledge/
├── ubitus/                    # 公司知識
│   ├── 01_company.txt         # 公司介紹
│   ├── 02_products.txt        # 產品介紹
│   └── 03_faq.txt             # 常見問題
├── medical/                   # 醫學知識
│   ├── 01_common_cold.md      # 感冒
│   ├── 02_fever.md            # 發燒
│   └── 03_health.md           # 健康檢查
```

**❌ 避免：**
```
knowledge/
└── ubitus/
    └── all.txt                # 所有內容塞進一個文件
```

### 2. 文件命名

- **使用有意義的名稱：** `products.txt` 而非 `file1.txt`
- **統一格式：** 全部使用小寫 + 底線（`snake_case`）
- **添加序號：** 便於排序（`01_company.txt`, `02_products.txt`）

### 3. 內容更新流程

```
1. 修改知識內容（*.txt, *.md）
   ↓
2. 提交 Git（版本控制）
   ↓
3. 重新生成 meta.json
   ↓
4. 測試檢索是否正常
   ↓
5. 部署到生產環境
```

---

## 🔧 故障排除

### 問題 1：meta.json 無法生成

**錯誤：** `FileNotFoundError: knowledge/ubitus/`

**檢查：**
```bash
# 確認目錄存在
ls -la knowledge/ubitus/

# 確認有文件
ls knowledge/ubitus/*.txt
```

**解決：**
```bash
# 創建目錄
mkdir -p knowledge/ubitus

# 添加文件
echo "測試內容" > knowledge/ubitus/test.txt

# 重新生成
python -m agent.rag.meta_generator knowledge/ubitus
```

### 問題 2：檢索不到相關內容

**症狀：** 虛擬人無法回答知識庫相關問題

**檢查：**
```bash
# 檢查 meta.json 內容
cat knowledge/ubitus/meta.json

# 檢查摘要和關鍵字是否合理
# 檢查文件內容是否包含相關資訊
```

**解決：**
```bash
# 強制重新生成 meta.json
python -m agent.rag.meta_generator knowledge/ubitus --force

# 如果還是無效，檢查文件內容是否清晰
```

### 問題 3：知識庫未啟用

**症狀：** 日誌顯示「無相關文件」

**檢查：**
```yaml
# 檢查 config.yaml
knowledge:
  enabled: true                # 是否為 true？
  folders:
    - ubitus/                  # 目錄名是否正確？
```

**解決：**
```yaml
# 修改 config.yaml
knowledge:
  enabled: true
  folders:
    - ubitus/

# 重啟服務
docker compose restart
```

---

## 🔧 CLI 工具：Meta 生成器

### 生成單一知識庫的 meta

```bash
# 基本用法
python3 -m agent.rag.meta_generator /knowledge/ubitus

# 強制重新生成（覆蓋現有 meta.json）
python3 -m agent.rag.meta_generator /knowledge/ubitus --force
```

### 生成所有知識庫的 meta

```bash
# 生成所有知識庫
python3 -m agent.rag.meta_generator /knowledge --all

# 強制重新生成所有
python3 -m agent.rag.meta_generator /knowledge --all --force
```

### 輸出範例

```bash
$ python3 -m agent.rag.meta_generator /knowledge/ubitus

📁 重新生成：/knowledge/ubitus
📁 找到 3 個文件
  📄 處理：company.txt
  📄 處理：products.txt
  📄 處理：faq.txt
✅ 已生成：/knowledge/ubitus/meta.json

✅ 完成
```

### 進階用法

**無 LLM 模式（預設）：**
- ✅ 快速（< 1 秒）
- ✅ 不需要 LLM
- ⚠️ 摘要較簡單（只有基本資訊）

**LLM 模式（精準）：**
- ✅ 摘要精準
- ✅ 關鍵字相關性高
- ⚠️ 需要 LLM 可用
- ⚠️ 較慢（取決於 LLM 速度）

---

## 📚 相關文檔

- **知識庫規格：** `docs/03_specs/06_KNOWLEDGE_SPEC.md`
- **Persona 設計指南：** `docs/02_guides/02_PERSONA_GUIDE.md`
- **快速開始：** `docs/02_guides/01_QUICKSTART.md`

---

**版本歷史：**
- v1.0 (2026-04-16) - 初始版本
