"""
API 端點 - 虛擬人 Chat

提供 /sessions 和 /chat 端點
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import asyncio
import json
import time

# 流式模組
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'shared'))
from sse_events import StreamEvent, format_sse_event
from block_chunker import BlockChunker

# 新架構模組
from .prompt_loader import PromptLoader

# 這些會在 agent-api-streaming.py 中初始化
# config_loader = None
# session_store = None
# style_manager = None
# knowledge_retriever = None
# llm_service = None

router = APIRouter()


class CreateSessionRequest(BaseModel):
    """創建 Session 請求"""
    persona_id: str
    metadata: Optional[Dict[str, Any]] = None


class CreateSessionResponse(BaseModel):
    """創建 Session 回應"""
    session_id: str
    persona_id: str
    created_at: str


class ChatRequest(BaseModel):
    """Chat 請求"""
    session_id: str
    message: Optional[str] = None
    messages: Optional[list] = None
    
    def get_message(self) -> str:
        """取得用戶消息（支持 message 或 messages 格式）"""
        if self.message:
            return self.message
        if self.messages and len(self.messages) > 0:
            # 從 messages 陣列中取得最後一個用戶消息
            for msg in reversed(self.messages):
                if msg.get('role') == 'user':
                    return msg.get('content', '')
        return ''


class ChatResponse(BaseModel):
    """Chat 回應"""
    session_id: str
    response: str
    emotion: Optional[str] = None
    lang: Optional[str] = None
    persona_id: str
    timings: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None


class SwitchCharacterRequest(BaseModel):
    """切換虛擬人請求"""
    persona_id: str
    clear_messages: bool = True


class SwitchCharacterResponse(BaseModel):
    """切換虛擬人回應"""
    session_id: str
    old_config_id: str
    new_config_id: str
    messages_cleared: bool


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    創建新 Session（綁定 persona_id）
    
    前端在開始對話前，先創建 Session 並綁定虛擬人。
    使用 SQLite SessionStore 持久化存儲。
    """
    # 驗證 persona_id
    config = config_loader.get(request.persona_id)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"未知的虛擬人 ID: {request.persona_id}"
        )
    
    # 創建 Session（使用 SQLite SessionStore）
    # 統一使用 /data/sessions.db 持久化
    from session.session_store import get_session_store
    session_store = get_session_store('/data/sessions.db')
    
    session = session_store.create_session(
        prefix=request.persona_id,  # Session ID 前綴：UBICHAN_xxx
        metadata={
            "vh_char_config": {
                "persona_id": request.persona_id,
                "character_version": config.get('version', 'v1.0')
            }
        },
        ttl_hours=24
    )
    
    return CreateSessionResponse(
        session_id=session['session_id'],
        persona_id=request.persona_id,
        created_at=session['created_at']
    )


# ============= Prompt 組合邏輯（新架構）=============

async def _build_prompt(
    config: dict,
    user_message: str,
    conversation_history: list,
    workspace_path: Path,
    prompt_loader_obj,
    knowledge_content: str = None,
    knowledge_meta: str = None,
    is_llm1: bool = False
) -> tuple[str, bool]:
    """
    組合完整的 Prompt（5 部分結構）
    
    根據規範文件 specs/prompt-generation-spec.md v2.1：
    1. 角色風格 (Style)
    2. 輸出規格 (Output Spec)
    3. 知識庫內容 (Knowledge) - LLM1 用 Meta，LLM2 用完整內容
    4. 對話歷史 (Conversation History)
    5. 用戶問題 (User Message)
    
    Args:
        config: Persona 配置（YAML v2.0 結構）
        user_message: 用戶問題
        conversation_history: 對話歷史
        workspace_path: Workspace 路徑
        prompt_loader_obj: PromptLoader 實例
        knowledge_content: 知識庫完整內容（LLM2 使用）
        knowledge_meta: 知識庫 Meta（LLM1 使用）
        is_llm1: 是否為 LLM1 使用
    
    Returns:
        (prompt, emotion_enabled)
    """
    # 1. 載入角色風格
    style_file = config['style']['file']
    persona_id = config['persona_id']
    style_path = workspace_path / 'personas' / persona_id / style_file
    
    if style_path.exists():
        style_content = style_path.read_text(encoding='utf-8')
    else:
        print(f"⚠️  風格文件不存在：{style_path}")
        style_content = f"# {persona_id} 風格定義\n（文件缺失）"
    
    # 2. 載入輸出提示詞模板
    output_format = config['output_format']
    prompt_content = prompt_loader_obj.load_prompt(output_format)
    emotion_enabled = (output_format == 'virtual_human')
    
    # 3. 載入知識庫（LLM1 vs LLM2 差異）
    if is_llm1:
        # LLM1：只載入 Meta（用於判斷）
        knowledge_section = knowledge_meta if knowledge_meta else "無"
    else:
        # LLM2：載入完整內容
        knowledge_section = knowledge_content if knowledge_content else "無"
    
    # 4. 格式化對話歷史
    recent_history = conversation_history[-10:] if conversation_history else []
    history_text = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in recent_history
    ]) if recent_history else "（無）"
    
    # 5. 組合 Prompt
    prompt = f"""# 角色風格
{style_content}

# 輸出規格
{prompt_content}

# 知識庫內容
{knowledge_section}

# 對話歷史
{history_text}

# 用戶問題
{user_message}
"""
    
    return prompt, emotion_enabled


# ============= STREAM 生成器（虛擬人專用）=============

async def _call_llm1(
    user_message: str,
    meta_content: Optional[str],
    style_prompt: str,
    conversation_history: list = None,
    persona_config: dict = None,
    workspace_path: Path = None,
    prompt_loader_obj = None
):
    """
    呼叫 LLM1：生成友善回應 + 判斷相關文件
    
    永遠都要呼叫，永遠都返回友善回應
    
    Args:
        user_message: 用戶問題
        meta_content: META 內容（如果有 knowledge_ids）
        style_prompt: 風格 Prompt
        conversation_history: 對話歷史（可選）
        persona_config: Persona 配置（YAML v2.0，可選）
        workspace_path: Workspace 路徑（可選）
        prompt_loader_obj: PromptLoader 實例（可選）
    
    Returns:
        {
            'comforting_words': str,  # 永遠都有值
            'related_files': list,    # 可能為空
            'meta_content': str       # 返回 META 內容（如果有）
        }
    """
    global llm_service
    
    # 構建 Prompt
    # 如果有 persona_config 和 prompt_loader_obj，使用新的 _build_prompt 邏輯
    if persona_config and workspace_path and prompt_loader_obj:
        # 新架構：使用 _build_prompt
        prompt, _ = await _build_prompt(
            config=persona_config,
            user_message=user_message,
            conversation_history=conversation_history or [],
            workspace_path=workspace_path,
            prompt_loader_obj=prompt_loader_obj,
            knowledge_meta=meta_content,
            is_llm1=True
        )
        
        # 添加 LLM1 專用指令（快速回應 + 判斷）
        prompt += """

# LLM1 專用指令
請用 **1 句話快速回應（<20 字）**，並判斷是否需要查詢知識庫。

## 回應格式（必須遵守）
回應：[快速回應，一句話，不超過 20 字]
相關文件：["file1.txt", "file2.txt"]  # 如果需要查詢，否則 []

## 快速回應範例
- 需要查詢知識庫：「人家幫你看看～」、「讓我找找看喔」
- 需要調用工具：「人家來試試看」、「交給我吧～」
- 單純回話：「人家知道了～」、「收到了啦」、「好喔」

**注意：**
- 第一行必須是「回應：」開頭
- 第二行必須是「相關文件：」開頭
- **快速回應只能一句話，不超過 20 個字**
- 用繁體中文回應
"""
    else:
        # 舊架構：使用硬編碼 Prompt（向後兼容）
        # 根據是否有 style_prompt 調整角色設定
        is_virtual_human = bool(style_prompt)
        
        if meta_content:
            if is_virtual_human:
                # 格式化對話歷史
                history_text = ""
                if conversation_history and len(conversation_history) > 0:
                    history_text = "\n".join([f"- {msg['role']}: {msg['content']}" for msg in conversation_history[-10:]])
                
                prompt = f"""你是一個虛擬人助手。請**嚴格按照以下格式**回應：

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
- 需要查詢知識庫：「人家幫你看看～」、「讓我找找看喔」
- 需要調用工具：「人家來試試看」、「交給我吧～」
- 單純回話：「人家知道了～」、「收到了啦」、「好喔」

**注意：**
- 第一行必須是「回應：」開頭
- 第二行必須是「相關文件：」開頭
- **快速回應只能一句話，不超過 20 個字**
- **不要自我介紹，不要完整回應**
- 不要添加其他內容
- 用繁體中文回應
- **語氣要符合虛擬人風格（可愛、親切）**"""
            else:
                history_text = ""
                if conversation_history and len(conversation_history) > 0:
                    history_text = "\n".join([f"- {msg['role']}: {msg['content']}" for msg in conversation_history[-10:]])
                
                prompt = f"""你是一個知識庫檢索助手。請**嚴格按照以下格式**回應：

## 回應格式（必須遵守）
回應：[根據你的判斷行動，回覆對應的安撫語]
相關文件：["file1.txt", "file2.txt"]

## 已知資訊
{meta_content}

## 對話歷史
{history_text if history_text else "（無）"}

## 用戶問題
{user_message}

## 行動類別與安撫語範例
- 需要查詢知識庫：「我幫你查查」、「讓我看看相關資料」、「來找找看」
- 需要調用工具：「我幫你試試」、「讓我執行這個操作」、「處理中」
- 單純回話：「我知道了」、「收到了」、「明白了」、「好的」

**注意：**
- 第一行必須是「回應：」開頭
- 第二行必須是「相關文件：」開頭
- 不要添加其他內容
- 用繁體中文回應
- 根據行動類別選擇合適的安撫語
- 措辭應該自然、多樣，避免每次都一樣"""
        else:
            if is_virtual_human:
                history_text = ""
                if conversation_history and len(conversation_history) > 0:
                    history_text = "\n".join([f"- {msg['role']}: {msg['content']}" for msg in conversation_history[-10:]])
                
                prompt = f"""你是一個虛擬人助手。請**嚴格按照以下格式**回應：

## 回應格式（必須遵守）
回應：[快速回應，**一句話，不超過 20 字**]
相關文件：[]

## 對話歷史
{history_text if history_text else "（無）"}

## 用戶問題
{user_message}

## 快速回應範例（**只能一句話**）
- 需要查詢知識庫：「人家幫你看看～」、「讓我找找看喔」
- 需要調用工具：「人家來試試看」、「交給我吧～」
- 單純回話：「人家知道了～」、「收到了啦」、「好喔」

**注意：**
- 第一行必須是「回應：」開頭
- 第二行必須是「相關文件：」開頭
- **快速回應只能一句話，不超過 20 個字**
- **不要自我介紹，不要完整回應**
- 不要添加其他內容
- 用繁體中文回應
- **語氣要符合虛擬人風格（可愛、親切）**"""
            else:
                history_text = ""
                if conversation_history and len(conversation_history) > 0:
                    history_text = "\n".join([f"- {msg['role']}: {msg['content']}" for msg in conversation_history[-10:]])
                
                prompt = f"""請**嚴格按照以下格式**回應：

## 回應格式（必須遵守）
回應：[根據你的判斷行動，回覆對應的安撫語]
相關文件：[]

## 對話歷史
{history_text if history_text else "（無）"}

## 用戶問題
{user_message}

## 行動類別與安撫語範例
- 需要查詢知識庫：「我幫你查查」、「讓我看看相關資料」、「來找找看」
- 需要調用工具：「我幫你試試」、「讓我執行這個操作」、「處理中」
- 單純回話：「我知道了」、「收到了」、「明白了」、「好的」

**注意：**
- 第一行必須是「回應：」開頭
- 第二行必須是「相關文件：」開頭
- 不要添加其他內容
- 用繁體中文回應
- 根據行動類別選擇合適的安撫語
- 措辭應該自然、多樣，避免每次都一樣"""
    
    # 呼叫 LLM（STREAM 模式，與 /chat 統一）
    llm1_start = time.time()
    response_text = ""
    try:
        # ✅ 使用 chat_stream（與 /chat 端點統一）
        async for chunk in llm_service.provider.chat_stream(
            messages=[
                {"role": "system", "content": style_prompt or "你是一個友善的助手。"},
                {"role": "user", "content": prompt}
            ],
            use_reasoning=False  # ✅ 自動處理參數轉換
        ):
            response_text += chunk  # 收集完整回應
        
        llm1_time = int((time.time() - llm1_start) * 1000)
        print(f"💬 LLM1 STREAM 完成：{llm1_time}ms")
        
        # 分離友善回應和相關文件
        comforting_words = ""
        related_files = []
        
        if not response_text:
            print(f"⚠️ LLM1 返回空內容，使用中性 fallback")
            comforting_words = "我收到了，讓我處理一下。"
        else:
            for line in response_text.split('\n'):
                line = line.strip()
                if line.startswith('回應：'):
                    comforting_words = line.replace('回應：', '').strip()
                elif line.startswith('相關文件：'):
                    files_str = line.replace('相關文件：', '').strip()
                    try:
                        related_files = json.loads(files_str)
                    except:
                        print(f"⚠️  解析相關文件失敗：{files_str}")
                        related_files = []
            
            # 如果沒有解析到回應，嘗試提取第一行
            if not comforting_words:
                print(f"⚠️  無法解析「回應：」，嘗試降級處理")
                first_line = response_text.split('\n')[0].strip() if response_text else ''
                if first_line and len(first_line) > 5:
                    comforting_words = first_line
                    print(f"⚠️  從第一行提取回應：{comforting_words}")
                elif response_text.strip():
                    comforting_words = response_text.strip()
                    print(f"⚠️  使用整個回應作為快速回應")
                else:
                    # 使用中性 fallback
                    print(f"⚠️  LLM1 返回空內容，使用中性 fallback")
                    comforting_words = "我收到了，讓我處理一下。"
        
        print(f"💬 友善回應（LLM1 生成）：{comforting_words}")
        print(f"📋 相關文件：{related_files}")
        print(f"🔍 LLM1 原始回應：{response_text[:200] if response_text else '(空)'}")
        
        return {
            'comforting_words': comforting_words,
            'related_files': related_files,
            'meta_content': meta_content
        }
        
    except Exception as e:
        import traceback
        print(f"⚠️  LLM1 呼叫失敗：{e}")
        print(f"🔍 LLM1 異常堆疊：{traceback.format_exc()}")
        print(f"🔍 LLM1 原始回應物件：{repr(llm_raw_response)}")
        # ✅ 修復：使用中性 fallback
        return {
            'comforting_words': '我收到了，讓我處理一下。',
            'related_files': [],
            'meta_content': meta_content
        }


async def generate_vh_stream(request: ChatRequest, persona_config, style_prompt: str, knowledge_ids: list, session_store):
    """
    虛擬人 STREAM 生成器
    
    Args:
        request: ChatRequest
        persona_config: Persona 配置
        style_prompt: 風格 Prompt
        knowledge_ids: 知識庫 ID 列表
        session_store: Session Store 實例
    
    Yields:
        SSE 格式事件
    """
    global llm_service, config_loader
    
    start_time = asyncio.get_event_loop().time()
    user_message = request.get_message()
    
    # ========== 階段 1: 準備 LLM1 輸入 ==========
    print("🔍 階段 1: LLM1 生成快速回應 + RAG 判斷")
    
    meta_content = None
    rag_retrieve_time = 0  # RAG 向量檢索計時
    
    if knowledge_ids:
        # 從 knowledge_ids 取得 META 內容
        try:
            from .knowledge.retriever import MultiKnowledgeRetriever
            # ✅ 添加 RAG 完整計時（包含初始化 + get_meta_content）
            rag_start = time.time()
            
            retriever = MultiKnowledgeRetriever(
                knowledge_ids=knowledge_ids,
                base_path="/knowledge",
                llm_client=None  # 不需要 LLM，只要讀取 META
            )
            
            meta_content = retriever.get_meta_content()
            rag_retrieve_time = int((time.time() - rag_start) * 1000)
            print(f"📚 取得 META 內容：{len(knowledge_ids)} 個知識庫")
            print(f"⏱️ RAG 完整計時：{rag_retrieve_time}ms (初始化 + get_meta_content)")
        except Exception as e:
            print(f"⚠️  讀取 META 失敗：{e}")
    
    # ========== 階段 2: 呼叫 LLM1（永遠呼叫） ==========
    # 獲取對話歷史（傳遞給 LLM1 以理解上下文）
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
    
    # 初始化 PromptLoader（用於新架構）
    if not hasattr(generate_vh_stream, 'prompt_loader'):
        generate_vh_stream.prompt_loader = PromptLoader("/app/prompts")
    
    llm1_start = time.time()
    
    # 新架構：傳遞 persona_config 和 prompt_loader_obj
    llm1_result = await _call_llm1(
        user_message=user_message,
        meta_content=meta_content,
        style_prompt=style_prompt,
        conversation_history=conversation_history,
        persona_config=persona_config,  # 新參數
        workspace_path=Path("/workspace"),  # 新參數
        prompt_loader_obj=generate_vh_stream.prompt_loader  # 新參數
    )
    llm1_time = int((time.time() - llm1_start) * 1000)
    
    comforting_words = llm1_result['comforting_words']
    related_files = llm1_result['related_files']
    
    # ========== 階段 3: ⚡ 立即發送快速回應（關鍵！） ==========
    # 獲取時間戳（用於 UBICHAN v2.0 格式）
    created = int(start_time)
    event_id = f"{request.session_id}_{created}"
    
    event = StreamEvent.create_text_chunk(
        message=comforting_words,
        created=created,
        event_id=event_id
    )
    yield format_sse_event(event)  # 自動加 [DONE]
    print(f"⚡ 已發送快速回應（< 1 秒）")
    
    # ========== 階段 4: 載入相關文件內容（如果有） ==========
    knowledge_text = ""
    rag_timings = {
        'rag_llm_ms': llm1_time,        # LLM1 計時（永遠都有）
        'rag_retrieve_ms': rag_retrieve_time,  # ✅ RAG 向量檢索計時
    }
    
    if related_files:
        try:
            # 載入文件內容
            file_read_start = time.time()
            knowledge_text = retriever.load_files_content(related_files)
            file_read_time = int((time.time() - file_read_start) * 1000)
            
            rag_timings['file_read_ms'] = file_read_time
            rag_timings['rag_retrieve_ms'] = rag_retrieve_time + file_read_time  # ✅ RAG 檢索 + 文件讀取
            print(f"📚 已載入 {len(related_files)} 個文件內容")
        except Exception as e:
            print(f"⚠️  載入文件失敗：{e}")
            rag_timings['rag_retrieve_ms'] = rag_retrieve_time
    else:
        rag_timings['rag_retrieve_ms'] = rag_retrieve_time
        print(f"⚠️  無相關文件，只使用 LLM1 回應")
    
    # ========== 階段 2: 組合 LLM2 Prompt（使用新架構） ==========
    # 獲取對話歷史（用於 LLM2）
    session_data = session_store.get_session(request.session_id)
    messages = session_data.get('messages', []) if session_data else []
    conversation_history = [m for m in messages[-10:] if m.get('role') in ['user', 'assistant']]
    
    # ✅ 添加當前用戶輸入到 messages（用於 LLM 呼叫）
    messages.append({"role": "user", "content": user_message})
    
    # 使用新架構的 _build_prompt 組合 LLM2 Prompt
    # 注意：如果 persona_config 格式不對，會直接丟 ERROR
    # 初始化 PromptLoader
    if not hasattr(generate_vh_stream, 'prompt_loader'):
        generate_vh_stream.prompt_loader = PromptLoader("/app/prompts")
    
    workspace_path = Path("/workspace")
    
    # 組合 LLM2 Prompt（5 部分結構）
    llm2_prompt, emotion_enabled = await _build_prompt(
        config=persona_config,
        user_message=user_message,
        conversation_history=conversation_history,
        workspace_path=workspace_path,
        prompt_loader_obj=generate_vh_stream.prompt_loader,
        knowledge_content=knowledge_text if knowledge_text else None,
        is_llm1=False
    )
    print(f"✅ 使用新架構組合 LLM2 Prompt")
    
    # ========== 階段 3: LLM2 STREAM 回答 ==========
    print("📚 階段 3: LLM2 STREAM 回答")
    
    chunker = BlockChunker(min_chars=800, max_chars=1200)
    llm2_start = asyncio.get_event_loop().time()
    
    # ⭐ 收集完整回复（用於保存到 Session）
    full_response = ""
    
    try:
        # 構建完整 messages
        full_messages = [{"role": "system", "content": llm2_prompt}] + messages
        
        # 呼叫 LLM STREAM
        async for chunk in llm_service.provider.chat_stream(
            full_messages,
            use_reasoning=False,
            temperature=0
        ):
            if chunker.should_send(chunk):
                chunk_text = chunker.get_chunk(chunk)
                full_response += chunk_text  # ⭐ 收集
                event = StreamEvent.create_text_chunk(
                    message=chunk_text,
                    created=created,
                    event_id=event_id
                )
                yield format_sse_event(event)  # 自動加 [DONE]
        
        llm2_time = int((asyncio.get_event_loop().time() - llm2_start) * 1000)
        
        # 發送剩餘內容
        if chunker.has_remaining():
            remaining = chunker.get_remaining()
            full_response += remaining  # ⭐ 收集
            event = StreamEvent.create_text_chunk(
                message=remaining,
                created=created,
                event_id=event_id
            )
            yield format_sse_event(event)  # 自動加 [DONE]
    except Exception as e:
        print(f"❌ LLM STREAM 失敗：{e}")
        event = StreamEvent.create_error(
            error=str(e),
            created=created,
            event_id=event_id
        )
        yield format_sse_event(event)  # 自動加 [DONE]
        return
    
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


@router.post("/chat", response_model=None)
async def chat(request: ChatRequest):
    """
    Chat 端點 - 僅支援 STREAM 模式
    
    流程:
    1. 從 Session Store 取得 Session 內容
    2. 從 metadata 獲取 vh_char_config
    3. 取得 persona_id
    4. 載入 CONFIG 和風格 Prompt
    5. 檢索知識庫
    6. 組合 System Prompt
    7. 呼叫 LLM（STREAM）
    8. 添加回應到 Session Store
    9. 返回 STREAM 回應
    
    Args:
        request: ChatRequest
    
    Returns:
        StreamingResponse: SSE 格式回應
    """
    # ⭐ 所有請求都使用 STREAM 模式
    # 非 STREAM 模式已移除（保留參考見 git history）
    
    # 1. 從 Session Store 取得 Session 內容
    try:
        from session.session_store import get_session_store
        session_store = get_session_store('/data/sessions.db')
        session_data = session_store.get_session(request.session_id)
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session 不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session 讀取失敗：{str(e)}")
    
    # 2. 從 metadata 獲取 vh_char_config
    metadata = session_data.get('metadata')
    vh_char_config = None
    persona_id = None
    style_prompt = ""
    knowledge_ids = []
    
    if metadata:
        vh_char_config = metadata.get('vh_char_config')
        if vh_char_config:
            persona_id = vh_char_config.get('persona_id')
            
            if persona_id:
                # 載入 CONFIG 和風格 Prompt
                config = config_loader.get(persona_id)
                if config:
                    # 新架構：style 是物件 {'file': 'style.md'}
                    style_file = config.get('style', {}).get('file', 'style.md')
                    if not Path(style_file).is_absolute():
                        from virtual_human.config_loader import ConfigLoader
                        config_loader_instance = ConfigLoader()
                        style_full_path = str(config_loader_instance.personas_path / persona_id / style_file)
                    else:
                        style_full_path = style_file
                    style_prompt = style_manager.load_style(style_full_path)
                    
                    # 新架構：knowledge 是物件 {'enabled': true, 'folders': [...]}
                    knowledge_config = config.get('knowledge', {})
                    if knowledge_config.get('enabled'):
                        knowledge_ids = knowledge_config.get('folders', [])
                    else:
                        knowledge_ids = []
    
    # 3. 添加用戶消息到 Session Store
    user_message = request.get_message()
    session_store.add_message(request.session_id, "user", user_message)
    
    # 4. 返回 STREAM 回應
    return StreamingResponse(
        generate_vh_stream(
            request=request,
            persona_config=config,  # ✅ 傳入完整的 config，不是 vh_char_config
            style_prompt=style_prompt,
            knowledge_ids=knowledge_ids,
            session_store=session_store
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
    # 歷史代碼見 git commit 4725a96
    # 
    # 移除原因：
    # 1. 維護兩套邏輯複雜且容易出錯
    # 2. STREAM 模式體驗更好（即時回應）
    # 3. 前端已統一使用 STREAM
    # 
    # 如果需要非 STREAM 模式，請參考 git history
    # ========================================================================


@router.post("/sessions/{session_id}/switch", response_model=SwitchCharacterResponse)
async def switch_character(session_id: str, request: SwitchCharacterRequest):
    """
    切換虛擬人
    
    允許在既有 Session 中切換虛擬人（可選清空對話歷史）。
    """
    # 驗證 persona_id
    config = config_loader.get(request.persona_id)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"未知的虛擬人 ID: {request.persona_id}"
        )
    
    # 取得 Session（使用 SQLite SessionStore）
    session_data = session_store.get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail="Session 不存在或已過期"
        )
    
    # 記錄舊 persona_id（從 metadata 獲取）
    metadata = session_data.get('metadata', {})
    vh_char_config = metadata.get('vh_char_config', {})
    old_config_id = vh_char_config.get('persona_id', session_data.get('persona_id', 'unknown'))
    
    # 更新 Session 的 metadata
    metadata['vh_char_config'] = {
        'persona_id': request.persona_id,
        'character_version': config.get('version', 'v1.0')
    }
    
    # 可選：清空對話歷史（需要重新創建 Session）
    if request.clear_messages:
        # 刪除舊 Session，創建新 Session
        session_store.delete_session(session_id)
        new_session = session_store.create_session(
            prefix=request.persona_id,
            metadata=metadata,
            ttl_hours=24
        )
        session_id = new_session['session_id']
    
    return SwitchCharacterResponse(
        session_id=session_id,
        old_config_id=old_config_id,
        new_config_id=request.persona_id,
        messages_cleared=request.clear_messages
    )


@router.get("/sessions/{session_id}/stats")
async def get_session_stats(session_id: str):
    """
    取得 Session 統計資訊
    """
    session_data = session_store.get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=404,
            detail="Session 不存在或已過期"
        )
    
    # 從 metadata 獲取 persona_id
    metadata = session_data.get('metadata', {})
    vh_char_config = metadata.get('vh_char_config', {})
    persona_id = vh_char_config.get('persona_id', session_data.get('persona_id', 'unknown'))
    
    return {
        'session_id': session_id,
        'persona_id': persona_id,
        'message_count': session_data.get('message_count', 0),
        'created_at': session_data.get('created_at', ''),
        'last_active': session_data.get('last_active', '')
    }


@router.get("/sessions/stats")
async def get_all_sessions_stats():
    """
    取得所有 Session 統計資訊
    """
    sessions = session_store.list_sessions()
    return {
        'total_sessions': len(sessions),
        'sessions': sessions
    }


def extract_emotion(text: str) -> str:
    """
    從回應中提取情緒標籤
    
    範例:
    <!-- emotion -->happy<!-- /emotion --> 你好啊！<br>
    → 返回 "happy"
    """
    import re
    match = re.search(r'<!--\s*emotion>(\w+)</emotion\s*-->', text)
    return match.group(1) if match else 'neutral'


def extract_lang(text: str) -> str:
    """
    從回應中提取語言標籤
    
    範例:
    <!-- lang -->tw (zh)<!-- /lang --> 你好啊！<br>
    → 返回 "tw (zh)"
    """
    import re
    match = re.search(r'<!--\s*lang>([\w\s()]+)</lang\s*-->', text)
    return match.group(1) if match else 'tw (zh)'


# 初始化函數（在 agent-api-streaming.py 中調用）
def init_virtual_human_api(
    config_loader_obj,
    session_store_obj,
    style_manager_obj,
    knowledge_retriever_obj,
    llm_service_obj
):
    """
    初始化虛擬人 API
    
    在 Server 啟動時調用，注入依賴。
    """
    global config_loader, session_store, style_manager, knowledge_retriever, llm_service
    
    config_loader = config_loader_obj
    session_store = session_store_obj
    style_manager = style_manager_obj
    knowledge_retriever = knowledge_retriever_obj
    llm_service = llm_service_obj
