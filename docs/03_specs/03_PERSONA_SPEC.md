# 🎭 Persona 規格書

**版本：** v2.0  
**日期：** 2026-04-16  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- Persona 配置格式與檔案結構
- YAML v2.0 規格與欄位定義

---

## 📋 概述

Persona 是**虛擬人的配置檔案**，定義：
- **身份** - 虛擬人的基本資訊
- **風格** - 風格 Prompt 路徑（style.md）
- **輸出格式** - 前端渲染規格（virtual_human | chat）
- **知識** - 知識庫資料夾列表
- **工具** - 可用工具列表

**格式：** YAML v2.0（支援註解、結構化、人類可讀）

---

## 📐 檔案結構

### 位置

```
workspace/personas/
├── ubichan/
│   ├── config.yaml       ← YAML v2.0 配置
│   └── style.md          ← 風格 Prompt
├── nurse/
│   ├── config.yaml
│   └── style.md
└── TEMPLATE/
    ├── config.yaml       ← 範本（新角色參考）
    └── style.md
```

### 命名規則

- ✅ 使用小寫英文（`ubichan/`）
- ✅ 使用 `.yaml` 副檔名
- ✅ 避免特殊字元（只允許 `a-z0-9_-`）
- ✅ `TEMPLATE/` 目錄會被跳過（不載入）

---

## 📋 Persona 格式（YAML v2.0）

### 完整範例

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
  target_audience: general
  tone: cheerful friendly
```

### 欄位說明

#### 基本欄位

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `persona_id` | string | ✅ | Persona 唯一識別碼 |
| `display_name` | string | ✅ | 虛擬人名稱（繁體中文） |

#### 風格定義

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `style.file` | string | ✅ | 風格 Prompt 檔案路徑（相對於 persona 目錄） |

**style.md 範例：**
```markdown
# 優必醬風格定義

## 角色設定
- 身份：優必達公司的虛擬客服助手
- 性格：親切友善、專業認真
- 語氣：活潑但不失專業

## 回應規範
- 使用繁體中文
- 適度使用表情符號
- 保持簡潔明瞭
```

#### 輸出格式

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `output_format.type` | string | ✅ | 輸出規格類型 |

**類型說明：**
- `virtual_human`：虛擬人對話格式（含 emotion、lang 標籤）
- `chat`：一般對話格式（純文字）

#### 知識庫配置

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `knowledge.enabled` | boolean | ❌ | 是否啟用知識庫（預設：true） |
| `knowledge.folders` | array | ❌ | 知識庫資料夾列表（相對於 /knowledge/） |

**說明：**
- 資料夾名稱相對於 `/knowledge/` 目錄
- `enabled: false` 表示不載入知識庫
- 多個資料夾可載入多個知識庫

#### 工具配置

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `tools.enabled` | boolean | ❌ | 是否啟用工具（預設：false） |
| `tools.available` | array | ❌ | 可用的工具列表 |

**說明：**
- 未來擴展用，目前保持空陣列
- 工具名稱需與 `agent/tools/` 目錄下的工具一致

---

## 📝 風格 Prompt 範例

> **說明：** 風格 Prompt 格式不強制，由创作者自行定義。以下為參考範例。

**範例：**
```markdown
# 優必醬風格定義

## 角色設定
- 身份：優必達公司的虛擬客服助手
- 性格：親切友善、專業認真
- 語氣：活潑但不失專業

## 回應規範
- 使用繁體中文
- 適度使用表情符號
- 保持簡潔明瞭
- 遇到不確定的問題，誠實告知
```

---

## 🔧 使用流程

### 1. 創建 Persona

```bash
# 1. 創建目錄
mkdir -p workspace/personas/ubichan

# 2. 創建 config.yaml
cat > workspace/personas/ubichan/config.yaml << EOF
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
EOF

# 3. 創建風格 Prompt
cat > workspace/personas/ubichan/style.md << EOF
# 優必醬風格定義

## 角色設定
- 身份：優必達公司的虛擬客服助手
- 性格：親切友善、專業認真
- 語氣：活潑但不失專業

## 回應規範
- 使用繁體中文
- 適度使用表情符號
- 保持簡潔明瞭
EOF
```

### 2. 使用 Persona

```bash
# 創建虛擬人 Session
curl -X POST http://localhost:8000/vh/sessions \
  -H "Content-Type: application/json" \
  -d '{"persona_id": "ubichan"}'

# 回應：{"session_id": "vh_abc123", "persona_id": "ubichan"}
```

---

## ⚠️ 注意事項

1. **TEMPLATE 目錄**：`workspace/personas/TEMPLATE/` 是範本，不會被載入
2. **必填欄位**：`persona_id`、`style.file`、`output_format.type` 是必填
3. **知識庫路徑**：`knowledge.folders` 中的資料夾必須存在於 `/knowledge/` 目錄
4. **風格檔案**：`style.file` 指定的檔案必須存在於 persona 目錄下

---

**文檔結束**
