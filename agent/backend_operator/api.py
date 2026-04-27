#!/usr/bin/env python3
"""
🦐 蝦米 Agent API 服務 v4.1.0 - 內建 Session 管理模組

支援的 Provider:
- OpenAI Provider: OpenAI, vLLM, LocalAI, Ollama (OpenAI 相容)
- Ubisage Provider: Ubisage 私有模型 (需要 Token 交換)

架構變更：
- Session API 作為 Agent API 的內建模組
- 代碼職責分離，但運行在同一容器
- 對話時調用 Session API 模組獲取 Session 內容
"""

import sys
import os
import json
import time  # 用於 TIMING 記錄
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
import asyncio

# Dotenv
from dotenv import load_dotenv
from pathlib import Path

# 明確指定 .env 路徑（相對於本檔案）
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"📝 載入 .env: {env_path}")

# 流式模組
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'shared'))
from block_chunker import BlockChunker
from sse_events import StreamEvent, StreamEventType, format_sse_event

# LLM Provider 抽象層
from llm_factory import create_provider, get_default_provider_type
from llm_providers import LLMProvider

# KNOWLEDGE 檢索（暫時註解，後續實作）
# from rag.knowledge_retriever import KnowledgeRetriever, MultiKnowledgeRetriever
# from virtual_human.knowledge.retriever import MultiKnowledgeRetriever


# ============= Session 模組（直接函數調用）=============
import sys
sys.path.insert(0, '/app')  # 添加根目錄到 Python path
from session.session_store import get_session_store

# 獲取全局 Session Store 實例
session_store = get_session_store('/data/sessions.db')


async def get_session_from_api(session_id: str) -> Optional[Dict[str, Any]]:
    """
    從 Session Store 獲取 Session 內容
    
    Args:
        session_id: Session ID
    
    Returns:
        Session 內容字典，如果失敗則返回 None
    """
    try:
        session = session_store.get_session(session_id)
        return session
    except Exception as e:
        print(f"❌ 獲取 Session 失敗：{e}")
        return None


async def add_message_to_session(session_id: str, role: str, content: str, 
                                  emotion: Optional[str] = None, 
                                  lang: Optional[str] = None) -> bool:
    """
    添加訊息到 Session
    
    Args:
        session_id: Session ID
        role: 角色 ('user' 或 'assistant')
        content: 訊息內容
        emotion: 情緒標籤（可選）
        lang: 語言標籤（可選）
    
    Returns:
        是否添加成功
    """
    try:
        return session_store.add_message(session_id, role, content, emotion, lang)
    except Exception as e:
        print(f"❌ 添加訊息失敗：{e}")
        return False

# 虛擬人模組
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from virtual_human.api import router as virtual_human_router, init_virtual_human_api
    from virtual_human.config_loader import ConfigLoader
    from virtual_human.style_manager import StyleManager
    from shared.llm_service import create_llm_service
    VIRTUAL_HUMAN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  虛擬人模組未導入：{e}")
    VIRTUAL_HUMAN_AVAILABLE = False
    virtual_human_router = None
    ConfigLoader = None
    StyleManager = None
    create_llm_service = None

# ============= 配置 =============
WORKSPACE = Path("/workspace")
KNOWLEDGE_BASE = Path("/knowledge")

# LLM Provider 配置
LLM_PROVIDER_TYPE = get_default_provider_type()  # "openai" 或 "ubisage"
llm_provider: Optional[LLMProvider] = None

# 其他配置
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
THINKING = os.getenv("THINKING", "enabled")
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "low")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))
STREAM_MIN_CHARS = int(os.getenv("STREAM_MIN_CHARS", "800"))
STREAM_MAX_CHARS = int(os.getenv("STREAM_MAX_CHARS", "1200"))
MAX_PARALLEL_TOOLS = int(os.getenv("MAX_PARALLEL_TOOLS", "5"))

# ============= 工具定義 =============
TOOLS = [
    {"type": "function", "function": {"name": "scan_workspace", "description": "掃描工作區", "parameters": {"type": "object", "properties": {"max_depth": {"type": "integer", "default": 2}}}}},
    {"type": "function", "function": {"name": "read_file", "description": "讀取檔案", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}}}, "required": ["filepath"]}},
    {"type": "function", "function": {"name": "write_file", "description": "寫入檔案", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "content": {"type": "string"}}}, "required": ["filepath", "content"]}},
    {"type": "function", "function": {"name": "list_dir", "description": "列出目錄", "parameters": {"type": "object", "properties": {"dirpath": {"type": "string"}}}, "required": ["dirpath"]}},
    {"type": "function", "function": {"name": "read_excel", "description": "讀取 Excel", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "rows": {"type": "integer", "default": 10}}}}},
    {"type": "function", "function": {"name": "read_csv", "description": "讀取 CSV", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "rows": {"type": "integer", "default": 10}}}}},
    {"type": "function", "function": {"name": "read_word", "description": "讀取 Word", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "read_pdf", "description": "讀取 PDF", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "web_search", "description": "網頁搜尋", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}, "required": ["query"]}},
    {"type": "function", "function": {"name": "rebuild_knowledge_meta", "description": "重新生成知識庫的 meta.json（需要通關密語）", "parameters": {"type": "object", "properties": {"knowledge_id": {"type": "string", "description": "知識庫 ID，例如 'ubitus'。如果為空則重新生成所有知識庫"}, "passphrase": {"type": "string", "description": "通關密語"}}, "required": ["passphrase"]}}},
]

# ============= 工具實作 =============
def scan_workspace(max_depth: int = 2) -> str:
    result = ["📁 工作區內容：", ""]
    try:
        for root, dirs, files in os.walk(WORKSPACE):
            rel_path = Path(root).relative_to(WORKSPACE)
            depth = len(rel_path.parts)
            if depth > max_depth: continue
            indent = "  " * depth
            dir_name = rel_path.name if rel_path.name else "/"
            result.append(f"{indent}📂 {dir_name}/")
            for file in sorted(files)[:20]:
                result.append(f"{indent}  📄 {file}")
    except Exception as e:
        result.append(f"錯誤：{e}")
    return "\n".join(result)

def read_file(filepath: str) -> str:
    try:
        abs_path = (WORKSPACE / filepath).resolve()
        if not str(abs_path).startswith(str(WORKSPACE)):
            return "❌ 錯誤：無法訪問 workspace 外的檔案"
        if not abs_path.exists():
            return f"❌ 錯誤：檔案不存在 - {filepath}"
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"❌ 讀取失敗：{e}"

def write_file(filepath: str, content: str) -> str:
    try:
        abs_path = (WORKSPACE / filepath).resolve()
        if not str(abs_path).startswith(str(WORKSPACE)):
            return "❌ 錯誤：無法訪問 workspace 外的檔案"
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✅ 寫入成功 - {filepath}"
    except Exception as e:
        return f"❌ 寫入失敗：{e}"

def list_dir(dirpath: str) -> str:
    try:
        abs_path = (WORKSPACE / dirpath).resolve()
        items = []
        for item in sorted(abs_path.iterdir()):
            icon = "📂" if item.is_dir() else "📄"
            items.append(f"{icon} {item.name}")
        return f"📁 {dirpath}:\n" + "\n".join(items)
    except Exception as e:
        return f"❌ 列出失敗：{e}"

def read_excel(filepath: str, rows: int = 10) -> str:
    try:
        import pandas as pd
        abs_path = (WORKSPACE / filepath).resolve()
        df = pd.read_excel(abs_path, nrows=rows)
        return f"📊 Excel 內容 (前{rows}列):\n{df.to_string()}"
    except Exception as e:
        return f"❌ 讀取 Excel 失敗：{e}"

def read_csv(filepath: str, rows: int = 10) -> str:
    try:
        import pandas as pd
        abs_path = (WORKSPACE / filepath).resolve()
        df = pd.read_csv(abs_path, nrows=rows)
        return f"📊 CSV 內容 (前{rows}列):\n{df.to_string()}"
    except Exception as e:
        return f"❌ 讀取 CSV 失敗：{e}"

def read_word(filepath: str) -> str:
    try:
        from docx import Document
        abs_path = (WORKSPACE / filepath).resolve()
        doc = Document(abs_path)
        content = [p.text for p in doc.paragraphs if p.text.strip()]
        return f"📘 Word 內容:\n" + "\n".join(content[:50])
    except Exception as e:
        return f"❌ 讀取 Word 失敗：{e}"

def read_pdf(filepath: str) -> str:
    try:
        import pdfplumber
        abs_path = (WORKSPACE / filepath).resolve()
        content = []
        with pdfplumber.open(abs_path) as pdf:
            for i, page in enumerate(pdf.pages[:5]):
                text = page.extract_text()
                if text:
                    content.append(f"--- 第 {i+1} 頁 ---\n{text}")
        return f"📕 PDF 內容:\n\n" + "\n\n".join(content)
    except Exception as e:
        return f"❌ 讀取 PDF 失敗：{e}"

def web_search(query: str) -> str:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "🔍 沒有找到相關結果"
        content = [f"🔍 搜尋結果 ({query}):"]
        for i, r in enumerate(results, 1):
            content.append(f"{i}. {r.get('title', '無標題')}")
            content.append(f"   {r.get('body', '無摘要')}")
            content.append(f"   {r.get('href', '無連結')}")
        return "\n".join(content)
    except Exception as e:
        return f"❌ 搜尋失敗：{e}"

def rebuild_knowledge_meta(knowledge_id: str = "", passphrase: str = "") -> str:
    """
    重新生成知識庫的 meta.json
    
    Args:
        knowledge_id: 知識庫 ID（例如 'ubitus'），如果為空則重新生成所有知識庫
        passphrase: 通關密語（預設：5688）
    
    Returns:
        執行結果字串
    """
    # 驗證通關密語
    expected_passphrase = os.getenv("KNOWLEDGE_PASSPHRASE", "5688")
    if passphrase != expected_passphrase:
        return f"❌ 通關密語錯誤"
    
    try:
        from rag.meta_generator import MetaGenerator
        
        # 知識庫基礎路徑
        knowledge_base = Path("/knowledge")
        if not knowledge_base.exists():
            return f"❌ 知識庫目錄不存在：{knowledge_base}"
        
        # 初始化生成器（不使用 LLM，僅生成基本資訊）
        generator = MetaGenerator(llm_client=None)
        
        if knowledge_id:
            # 重新生成單一知識庫
            knowledge_path = knowledge_base / knowledge_id
            if not knowledge_path.exists():
                return f"❌ 知識庫不存在：{knowledge_id}"
            
            print(f"📁 重新生成知識庫：{knowledge_id}")
            meta = generator.generate(str(knowledge_path), force=True)
            return f"✅ 已重新生成知識庫 '{knowledge_id}' 的 meta.json\n\n摘要：\n- 文件數量：{len(meta.get('files', []))}\n- 知識庫 ID: {meta.get('knowledge_id', 'N/A')}"
        else:
            # 重新生成所有知識庫
            print(f"📚 重新生成所有知識庫")
            all_metas = generator.generate_all(str(knowledge_base), force=True)
            if not all_metas:
                return "⚠️ 沒有找到任何知識庫"
            
            result = [f"✅ 已重新生成 {len(all_metas)} 個知識庫的 meta.json:\n"]
            for kid, meta in all_metas.items():
                file_count = len(meta.get('files', []))
                result.append(f"- {kid}: {file_count} 個文件")
            return "\n".join(result)
            
    except Exception as e:
        import traceback
        print(f"❌ rebuild_knowledge_meta 錯誤：{e}")
        traceback.print_exc()
        return f"❌ 重新生成失敗：{e}"

# 工具函數映射
TOOL_FUNCTIONS = {
    "scan_workspace": scan_workspace,
    "read_file": read_file,
    "write_file": write_file,
    "list_dir": list_dir,
    "read_excel": read_excel,
    "read_csv": read_csv,
    "read_word": read_word,
    "read_pdf": read_pdf,
    "web_search": web_search,
    "rebuild_knowledge_meta": rebuild_knowledge_meta,
}

# ============= FastAPI 應用 =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時
    print("🦐 蝦米 Agent API 服務 v3.2.1 啟動中...")
    print(f"📦 LLM Provider: {LLM_PROVIDER_TYPE}")
    print(f"📦 LLM Provider: {LLM_PROVIDER_TYPE}")
    print(f"🌐 API 基礎 URL: {os.getenv('OPENAI_BASE_URL', 'N/A')}")
    print(f"🤖 模型：{os.getenv('LLM_MODEL', os.getenv('OPENAI_MODEL', 'N/A'))}")
    print(f"⚙️  Session 功能：已啟用（內建模組）")
    
    # 初始化 LLM Provider
    global llm_provider
    try:
        llm_provider = create_provider()
        print(f"✅ LLM Provider 初始化成功")
    except Exception as e:
        print(f"⚠️  LLM Provider 初始化失敗：{e}")
        print(f"   將在首次請求時重試")
    
    # 獲取 Git Commit Hash（用於版本追蹤）
    git_hash = "unknown"
    try:
        import subprocess
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd="/workspace",
            stderr=subprocess.DEVNULL
        ).decode("ascii").strip()
    except Exception:
        pass
    
    # 初始化虛擬人模組
    if VIRTUAL_HUMAN_AVAILABLE:
        print("🎭 初始化虛擬人模組...")
        try:
            # 1. 初始化 ConfigLoader（載入所有 personas 配置）
            config_loader = ConfigLoader(personas_path="/workspace/personas")
            
            # 2. 初始化 StyleManager（快取風格 Prompt）
            style_manager = StyleManager(style_base="/workspace/personas")
            
            # 4. 預熱 Persona 快取（優化：啟動時載入所有風格 Prompt）
            print("🔥 預熱 Persona 快取...")
            persona_ids = config_loader.get_all_ids()
            for persona_id in persona_ids:
                try:
                    # ConfigLoader 已經在 _cache 中，直接獲取
                    config = config_loader._cache.get(persona_id)
                    if config:
                        # 從 config 獲取 style 路徑
                        style_rel_path = config.get('style')
                        if style_rel_path:
                            style_path = Path("/workspace/personas") / persona_id / style_rel_path
                            if style_path.exists():
                                style_manager.load_style(str(style_path))
                                print(f"   ✅ 預熱：{persona_id}")
                except Exception as e:
                    print(f"   ⚠️  預熱失敗 {persona_id}: {e}")
            
            # 5. 初始化 LLM Service（統一服務層）
            llm_service = create_llm_service(llm_provider) if llm_provider else None
            
            # 6. Knowledge Retriever（在 /vh/chat 中動態創建）
            knowledge_retriever = None
            
            # 7. 註冊虛擬人路由（使用 SQLite SessionStore）
            init_virtual_human_api(
                config_loader_obj=config_loader,
                session_store_obj=session_store,
                style_manager_obj=style_manager,
                knowledge_retriever_obj=knowledge_retriever,
                llm_service_obj=llm_service
            )
            app.include_router(virtual_human_router, prefix="/vh", tags=["Virtual Human"])
            
            print("✅ 虛擬人模組初始化完成")
            print(f"   - personas 數量：{len(persona_ids)}")
            print(f"   - personas 路徑：/workspace/personas")
            print(f"   - Git Commit: {git_hash}")
            print(f"   - Persona 快取：已預熱 {len(persona_ids)} 個角色")
        except Exception as e:
            print(f"⚠️  虛擬人模組初始化失敗：{e}")
    
    yield
    
    # 關閉時
    print("🦐 蝦米 Agent API 服務關閉中...")

app = FastAPI(
    title="🦐 蝦米 Agent API",
    version="3.2.1",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= 請求/回應模型 =============
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="對話歷史")
    session_id: Optional[str] = Field(None, description="Session ID")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent 回應")
    session_id: str = Field(..., description="Session ID")
    used_tools: List[Dict[str, Any]] = Field(default_factory=list, description="使用的工具")
    thinking: Optional[str] = Field(None, description="思考過程（如果有）")
    message_count: int = Field(0, description="Session 中的訊息總數")
    timings: Optional[Dict[str, Any]] = Field(default=None, description="性能計時數據")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="Token Usage 統計")

# ============= API 端點 =============
@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "version": "v4.0.0",  # 虛擬人版本
        "provider": LLM_PROVIDER_TYPE,
        "model": os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "N/A")),
        "workspace": str(WORKSPACE),
        "session_support": True,
        "virtual_human_support": VIRTUAL_HUMAN_AVAILABLE,
        "knowledge_support": True
    }

@app.get("/sessions")
async def list_sessions():
    """列出 Sessions"""
    try:
        sessions = session_store.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        print(f"❌ 列出 Sessions 失敗：{e}")
        return {"sessions": []}


@app.post("/sessions")
async def create_session(request: dict):
    """創建 Session（支持 metadata）"""
    try:
        prefix = request.get("prefix")  # 可為空（一般無風格對話）
        metadata = request.get("metadata")  # 可選的 metadata（JSON 物件）
        ttl_hours = request.get("ttl_hours", 1)
        
        session = session_store.create_session(prefix=prefix, metadata=metadata, ttl_hours=ttl_hours)
        return session
    except Exception as e:
        print(f"❌ 創建 Session 失敗：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """獲取 Session 詳情"""
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """刪除 Session"""
    success = session_store.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": "Session deleted"}


@app.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    """獲取 Session 的訊息歷史"""
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": session.get("messages", [])}


@app.post("/sessions/{session_id}/messages")
async def add_message(session_id: str, role: str, content: str, emotion: Optional[str] = None, lang: Optional[str] = None):
    """添加訊息到 Session"""
    success = session_store.add_message(session_id, role, content, emotion, lang)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


# ⚠️ 暫時註解：Knowledge 功能將在後續實作為 Tool
# def _auto_search_knowledge(question: str) -> tuple:
#     """
#     自動檢索 KNOWLEDGE
#     
#     Args:
#         question: 用戶問題
#     
#     Returns:
#         (知識內容，timings 數據) 或 (None, {})
#     """
#     try:
#         # 檢查知識庫目錄是否存在
#         if not KNOWLEDGE_BASE.exists():
#             print("⚠️  KNOWLEDGE 目錄不存在")
#             return None, {}
#         
#         # 獲取所有知識庫 ID
#         knowledge_ids = [d.name for d in KNOWLEDGE_BASE.iterdir() if d.is_dir()]
#         if not knowledge_ids:
#             print("📚 沒有知識庫")
#             return None, {}
#         
#         print(f"🔍 自動檢索知識庫：{knowledge_ids}")
#         
#         # 創建檢索器（使用 LLM Provider 的客戶端）
#         llm_client = llm_provider.client if llm_provider else None
#         
#         # 創建適配器
#         class LLMAdapter:
#             def __init__(self, client, model):
#                 self.client = client
#                 self.model = model
#             
#             def generate(self, prompt: str) -> str:
#                 response = self.client.chat.completions.create(
#                     model=self.model,
#                     messages=[{"role": "user", "content": prompt}],
#                     max_tokens=500
#                 )
#                 return response.choices[0].message.content
#         
#         if llm_client:
#             adapter = LLMAdapter(llm_client, getattr(llm_provider, 'model', 'Qwen/Qwen3.5-397B-A17B-FP8'))
#             retriever = MultiKnowledgeRetriever(knowledge_ids, str(KNOWLEDGE_BASE), adapter)
#         else:
#             retriever = MultiKnowledgeRetriever(knowledge_ids, str(KNOWLEDGE_BASE), None)
#         
#         # 執行檢索
#         result = retriever.query(question)
#         
#         if result["content"]:
#             print(f"✅ 找到相關知識：{result.get('knowledge_used', [])}")
#             # 返回知識內容和 timings
#             return result["content"], result.get("timings", {})
#         else:
#             print("⚠️  未找到相關知識")
#             return None, {}
#             
#     except Exception as e:
#         print(f"❌ 自動檢索失敗：{e}")
#         return None, {}


# ============= STREAM 生成器（方案 A：彈性設計）=============

async def generate_stream(request, user_message: str, tools=None, knowledge_ids: List[str] = None, persona_config=None):
    """
    統一 STREAM 生成器（方案 A）- LLM1 獨立呼叫架構
    
    Args:
        request: ChatRequest（用於 session_id）
        user_message: 用戶問題
        tools: Tool 列表（可選，None 表示不執行 Tool）
        knowledge_ids: 知識庫 ID 列表（可選，空列表表示不執行 RAG）
        persona_config: Persona 配置（可選，None 表示一般 Agent）
    
    Yields:
        SSE 格式事件
    """
    global llm_provider
    
    start_time = asyncio.get_event_loop().time()
    
    # ========== 階段 1: 準備 LLM1 輸入（讀取 META，不呼叫 LLM） ==========
    print("🔍 階段 1: LLM1 生成快速回應 + RAG 判斷")
    
    meta_content = None
    rag_retrieve_time = 0  # RAG 向量檢索計時
    meta_read_time = 0     # META 讀取計時
    
    # ⚠️ 暫時註解：Knowledge 功能將在後續實作為 Tool
    # if knowledge_ids:
    #     try:
    #         # ✅ 添加 RAG 完整計時（包含初始化 + get_meta_content）
    #         rag_start = time.time()
    #         
    #         # 創建 RAG 檢索器（llm_client=None，只讀取 META，不呼叫 LLM）
    #         retriever = MultiKnowledgeRetriever(
    #             knowledge_ids=knowledge_ids,
    #             base_path="/knowledge",
    #             llm_client=None  # ✅ 不呼叫 LLM，只讀取 META
    #         )
    #         
    #         meta_content = retriever.get_meta_content()
    #         rag_retrieve_time = int((time.time() - rag_start) * 1000)
    #         
    #         meta_read_time = rag_retrieve_time  # 完整 RAG 流程計時
    #         print(f"📚 取得 META 內容：{len(knowledge_ids)} 個知識庫")
    #         print(f"⏱️ RAG 完整計時：{rag_retrieve_time}ms (初始化 + get_meta_content)")
    #     except Exception as e:
    #         print(f"⚠️  讀取 META 失敗：{e}")
    
    # ========== 階段 2: 獲取對話歷史（用於 LLM1 上下文） ==========
    conversation_history = []
    try:
        session_data = session_store.get_session(request.session_id)
        if session_data:
            messages = session_data.get('messages', [])
            # 只取最近 10 條歷史（排除當前用戶消息）
            conversation_history = [m for m in messages[-10:] if m.get('role') in ['user', 'assistant']]
            print(f"📚 LLM1 獲取對話歷史：{len(conversation_history)} 條")
    except Exception as e:
        print(f"⚠️  獲取對話歷史失敗：{e}")
    
    # 格式化對話歷史
    history_text = ""
    if conversation_history:
        history_text = "\n".join([f"- {msg['role']}: {msg['content']}" for msg in conversation_history])
    
    # ========== 階段 3: 組合 LLM1 Prompt（包含 META + 對話歷史 + 用戶問題） ==========
    # 構建 LLM1 Prompt（嚴格遵循格式）
    if meta_content:
        llm1_prompt = f"""你是一個知識庫檢索助手。請**嚴格按照以下格式**回應：

## 回應格式（必須遵守）
回應：[快速回應，**一句話，不超過 20 字**]
相關文件：["file1.txt", "file2.txt"]

## 已知資訊
{meta_content}

## 對話歷史
{history_text if history_text else "（無）"}

## 用戶問題
{user_message}

## 快速回應範例（**只能一句話**）
- 需要查詢知識庫：「我幫你查查」、「讓我看看資料」
- 需要調用工具：「我幫你試試」、「處理中」
- 單純回話：「我知道了」、「收到了」、「好的」

**注意：**
- 第一行必須是「回應：」開頭
- 第二行必須是「相關文件：」開頭
- **快速回應只能一句話，不超過 20 個字**
- **不要完整回應，只需要快速簡短回應**
- 不要添加其他內容
- 用繁體中文回應
- 措辭應該自然、多樣，避免每次都一樣"""
    else:
        llm1_prompt = f"""請**嚴格按照以下格式**回應：

## 回應格式（必須遵守）
回應：[快速回應，**一句話，不超過 20 字**]
相關文件：[]

## 對話歷史
{history_text if history_text else "（無）"}

## 用戶問題
{user_message}

## 快速回應範例（**只能一句話**）
- 需要查詢知識庫：「我幫你查查」、「讓我看看」
- 需要調用工具：「我幫你試試」、「處理中」
- 單純回話：「我知道了」、「收到了」、「好的」

**注意：**
- 第一行必須是「回應：」開頭
- 第二行必須是「相關文件：」開頭
- **快速回應只能一句話，不超過 20 個字**
- **不要完整回應，只需要快速簡短回應**
- 不要添加其他內容
- 用繁體中文回應
- 措辭應該自然、多樣，避免每次都一樣"""
    
    # ========== 階段 4: 呼叫 LLM1（STREAM 模式，最快回覆） ==========
    llm1_start = time.time()
    llm_result = ""
    try:
        # ✅ 使用 STREAM 模式（與 LLM2 統一接口）
        async for chunk in llm_provider.chat_stream(
            messages=[{"role": "user", "content": llm1_prompt}],
            max_tokens=1000,
            use_reasoning=False  # ✅ 自動處理參數轉換
        ):
            llm_result += chunk  # 收集完整回應
        
        llm1_time = int((time.time() - llm1_start) * 1000)
        print(f"💬 LLM1 STREAM 完成：{llm1_time}ms")
        
        # 解析 LLM1 結果
        comforting_words = ""
        related_files = []
        
        if not llm_result:
            print(f"⚠️ LLM1 返回空內容，使用中性 fallback")
            comforting_words = "我收到了，讓我處理一下。"
        else:
            for line in llm_result.split('\n'):
                line = line.strip()
                if line.startswith('回應：'):
                    comforting_words = line.replace('回應：', '').strip()
                elif line.startswith('相關文件：'):
                    files_str = line.replace('相關文件：', '').strip()
                    try:
                        related_files = json.loads(files_str)
                    except:
                        related_files = []
            
            # Fallback
            if not comforting_words and llm_result.strip():
                comforting_words = llm_result.strip()
            elif not comforting_words:
                comforting_words = "我收到了，讓我處理一下。"
        
        print(f"💬 快速回應：{comforting_words}")
        print(f"📋 相關文件：{related_files}")
        
    except Exception as e:
        import traceback
        print(f"⚠️ LLM1 呼叫失敗：{e}")
        print(f"🔍 LLM1 異常堆疊：{traceback.format_exc()}")
        comforting_words = "我收到了，讓我處理一下。"
        related_files = []
        llm1_time = 0
    
    # ========== 階段 4: ⚡ 立即發送快速回應（關鍵！） ==========
    # 獲取時間戳（用於 UBICHAN v2.0 格式）
    created = int(start_time)
    event_id = f"{request.session_id}_{created}"
    
    if comforting_words:
        event = StreamEvent.create_text_chunk(
            message=comforting_words,
            created=created,
            event_id=event_id
        )
        yield format_sse_event(event)  # 自動加 [DONE]
        print(f"⚡ 已發送快速回應（< 1 秒）")
    
    # ========== 階段 5: 載入相關文件內容（如果有，可選） ==========
    rag_timings = {
        'rag_llm_ms': llm1_time,        # LLM1 計時（永遠都有）
        'rag_retrieve_ms': rag_retrieve_time,  # ✅ RAG 向量檢索計時
        'meta_read_ms': meta_read_time,        # META 讀取計時
    }
    rag_content = ""
    valid_files = related_files
    
    # ⚠️ 暫時註解：Knowledge 功能將在後續實作為 Tool
    # if related_files and knowledge_ids:
    #     try:
    #         # 載入文件內容
    #         file_read_start = time.time()
    #         rag_content = retriever.load_files_content(related_files)
    #         file_read_time = int((time.time() - file_read_start) * 1000)
    #         
    #         rag_timings['file_read_ms'] = file_read_time
    #         rag_timings['rag_retrieve_ms'] = rag_retrieve_time + file_read_time  # ✅ RAG 檢索 + 文件讀取
    #         print(f"📚 已載入 {len(related_files)} 個文件內容")
    #     except Exception as e:
    #         print(f"⚠️  載入文件失敗：{e}")
    #         rag_timings['rag_retrieve_ms'] = rag_retrieve_time
    # else:
    #     rag_timings['rag_retrieve_ms'] = rag_retrieve_time
    #     if not related_files:
    #         print(f"⚠️  無相關文件，只使用 LLM1 回應")
    
    # ========== 階段 6: 執行 Tools（可選） ==========
    tool_results = []
    if tools:
        print(f"🔧 階段 3: 執行 Tools")
        # TODO: 實作 Tool 執行邏輯
        # 目前跳過，之後實作
    
    # ========== 階段 4: LLM2 用 RAG 結果回答 ==========
    print(f"📚 階段 4: LLM2 用 RAG 結果回答")
    
    # 構建 system prompt
    if persona_config:
        # 虛擬人 Agent：使用風格 Prompt
        style_prompt = persona_config.get('style_prompt', '')
        if rag_content:
            system_prompt = f"""{style_prompt}

### 知識庫內容 ###
{rag_content}

### 注意 ###
- 只使用提供的參考資訊回答
- 如果參考資訊不足，請誠實說明
- 使用繁體中文回應
"""
        else:
            system_prompt = f"""{style_prompt}

你是一個專業的助手。請用繁體中文友善地回答用戶問題。"""
    else:
        # 一般 Agent
        if rag_content:
            system_prompt = f"""你是一個專業的助手。請根據以下知識庫內容回答用戶問題。如果知識庫內容與問題相關，請優先使用這些資訊；如果無關，請一般回答。

=== 知識庫內容 ===
{rag_content}
=== 結束 ===
"""
        else:
            system_prompt = """你是一個專業的助手。請用繁體中文友善地回答用戶問題。"""
    
    # 構建完整 messages（包含對話歷史）
    # 從 session_store 讀取對話歷史
    try:
        from session.session_store import get_session_store
        session_store = get_session_store('/data/sessions.db')
        session_data = session_store.get_session(request.session_id)
        messages = session_data.get('messages', []) if session_data else []
        
        # ✅ 添加當前用戶輸入到 messages
        messages.append({"role": "user", "content": user_message})
    except Exception as e:
        print(f"⚠️  讀取 Session 失敗：{e}")
        messages = [{"role": "user", "content": user_message}]
    
    # 組合完整 messages（System + 歷史對話 + 當前輸入）
    messages_with_context = [{"role": "system", "content": system_prompt}] + messages
    
    # STREAM 模式呼叫 LLM2
    chunker = BlockChunker(min_chars=STREAM_MIN_CHARS, max_chars=STREAM_MAX_CHARS)
    llm2_start = asyncio.get_event_loop().time()
    
    # ⭐ 收集完整回复（用於保存到 Session）
    full_response = ""
    
    async for chunk in llm_provider.chat_stream(
        messages_with_context,
        use_reasoning=False,  # 快速回應
        temperature=0  # 確定性回應
    ):
        # 檢查是否需要發送 chunk
        if chunker.should_send(chunk):
            chunk_text = chunker.get_chunk(chunk)
            full_response += chunk_text  # ⭐ 收集
            try:
                event = StreamEvent.create_text_chunk(
                    message=chunk_text,
                    created=created,
                    event_id=event_id
                )
                yield format_sse_event(event)  # 自動加 [DONE]
            except Exception as e:
                print(f"⚠️  SSE 事件序列化失敗：{e}")
                print(f"🔍 chunk_text 長度：{len(chunk_text)}, 內容预览：{chunk_text[:100]}...")
                # 嘗試清理特殊字符後重試
                clean_chunk = chunk_text.replace('\n', '\\n').replace('\r', '\\r').replace('"', '\\"')
                event = StreamEvent.create_text_chunk(
                    message=clean_chunk,
                    created=created,
                    event_id=event_id
                )
                yield format_sse_event(event)  # 自動加 [DONE]
    
    llm2_time = int((asyncio.get_event_loop().time() - llm2_start) * 1000)
    
    # 發送剩餘內容
    if chunker.has_remaining():
        remaining = chunker.get_remaining()
        full_response += remaining  # ⭐ 收集
        try:
            event = StreamEvent.create_text_chunk(
                message=remaining,
                created=created,
                event_id=event_id
            )
            yield format_sse_event(event)  # 自動加 [DONE]
        except Exception as e:
            print(f"⚠️  SSE 剩餘內容序列化失敗：{e}")
            clean_remaining = remaining.replace('\n', '\\n').replace('\r', '\\r').replace('"', '\\"')
            event = StreamEvent.create_text_chunk(
                message=clean_remaining,
                created=created,
                event_id=event_id
            )
            yield format_sse_event(event)  # 自動加 [DONE]
    
    # ⭐ STREAM 完成後保存助手回复到 Session
    if request.session_id and full_response:
        try:
            session_store.add_message(request.session_id, "assistant", full_response)
            print(f"✅ 已保存助手回复到 Session: {request.session_id} ({len(full_response)} 字)")
        except Exception as e:
            print(f"⚠️  保存 Session 失敗：{e}")
    
    # ========== 階段 5: Done 事件 ==========
    total_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
    
    # UBICHAN v2.0 格式：扁平結構
    created = int(start_time)
    event_id = f"{request.session_id}_{created}"
    
    event = StreamEvent.create_done(
        created=created,
        event_id=event_id,
        timing={
            "rag_llm_ms": rag_timings.get('rag_llm_ms', 0),
            "file_read_ms": rag_timings.get('file_read_ms', 0),
            "rag_retrieve_ms": rag_timings.get('rag_retrieve_ms', 0),
            "llm_call_ms": llm2_time,
            "total_ms": total_time
        }
    )
    yield format_sse_event(event)  # 自動加 [DONE]
    
    # 🔍 印出 Session ID 和 TIMING
    print(f"📊 Session: {request.session_id} | TIMING: rag_llm={rag_timings.get('rag_llm_ms', 0)}ms, llm_call={llm2_time}ms, total={total_time}ms")


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    聊天端點 - 僅支援 STREAM 模式
    
    Args:
        request: ChatRequest
    
    Returns:
        StreamingResponse: SSE 格式回應
    """
    global llm_provider
    
    # ⭐ 所有請求都使用 STREAM 模式
    # 非 STREAM 模式已移除（保留參考見 git history）
    
    user_message = request.messages[-1]["content"] if request.messages else ""
    
    return StreamingResponse(
        generate_stream(
            request=request,
            user_message=user_message,
            tools=TOOLS,
            knowledge_ids=["ubitus"],  # 可配置
            persona_config=None
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
    
    # ========================================================================
    # ⚠️ 非 STREAM 模式已移除（保留參考）
    # ========================================================================
    # 歷史代碼見 git commit bf3e715
    # 
    # 移除原因：
    # 1. 維護兩套邏輯複雜且容易出錯
    # 2. STREAM 模式體驗更好（即時回應）
    # 3. 前端已統一使用 STREAM
    # 
    # 如果需要非 STREAM 模式，請參考 git history
    # ========================================================================

# ========================================================================
# ⚠️ /chat/stream 端點已移除
# ========================================================================
# 歷史代碼見 git commit 4857825
# 
# 移除原因：
# 1. 與 /chat 端點功能重複
# 2. 統一使用單一 STREAM 端點
# 3. 避免混淆
# 
# 如果需要參考，請查看 git history
# ========================================================================

# ============= 主程式 =============
if __name__ == "__main__":
    uvicorn.run(
        "backend_operator.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
