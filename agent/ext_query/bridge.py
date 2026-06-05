"""
bridge.py - Session + ext_query 橋接服務

整合：
- RESTful API Session 管理（遠端 nagato 服務）
- ext_query/ 模組（電話號碼查詢）

API 端點（根據 AIJPDNC-QueryRESTAPIforDNC-110526-1134-192.pdf 規範）:
- GET /session - 創建 Session（初始化會話環境）
- POST /chat - 聊天查詢（SSE 串流）
- GET /session/{session_id} - 獲取 Session 詳情（除錯用）
- GET /sessions - 獲取所有活躍 Session
- DELETE /session/{session_id} - 刪除 Session
- GET /health - 健康檢查
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
import httpx

# 添加父目錄到 Python 路徑，以便導入 session 模組
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from typing import Optional, Dict, Any
import json
import time

# 環境變數配置
NAGATO_BASE_URL = os.getenv("NAGATO_BASE_URL", "http://140.227.187.126:6480/api/v1")
NAGATO_HOST = os.getenv("NAGATO_HOST", "scroll.gc.ubicloud.net")
BRIDGE_HOST = os.getenv("BRIDGE_HOST", "0.0.0.0")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "3006"))

# 導入 ext_query 模組（同目錄）
try:
    from retrieval_agent import RetrievalAgent
    from final_agent import FinalAgent
    EXT_QUERY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 警告：無法導入 ext_query 模組：{e}")
    EXT_QUERY_AVAILABLE = False

# 全局變數
retrieval_agent: Optional[RetrievalAgent] = None
final_agent: Optional[FinalAgent] = None
http_client: Optional[httpx.AsyncClient] = None

# Session 自動清理配置
SESSION_EXPIRY_MINUTES = 5  # 5 分鐘過期
SESSION_CLEANUP_INTERVAL = 60  # 1 分鐘檢查一次（秒）

# 內存 Session 記錄：{session_id: created_timestamp}
session_created_at: Dict[str, float] = {}


def initialize_modules():
    """初始化所有模組"""
    global retrieval_agent, final_agent
    
    # 初始化 Retrieval Agent
    if EXT_QUERY_AVAILABLE:
        try:
            retrieval_agent = RetrievalAgent()
            print("✅ RetrievalAgent 初始化完成")
        except Exception as e:
            print(f"❌ RetrievalAgent 初始化失敗：{e}")
            retrieval_agent = None
    
    # 初始化 Final Agent
    if EXT_QUERY_AVAILABLE:
        try:
            final_agent = FinalAgent()
            print("✅ FinalAgent 初始化完成")
        except Exception as e:
            print(f"❌ FinalAgent 初始化失敗：{e}")
            final_agent = None


async def initialize_http_client():
    """初始化 HTTP 客戶端"""
    global http_client
    http_client = httpx.AsyncClient(
        base_url=NAGATO_BASE_URL,
        timeout=30.0
    )
    print(f"✅ HTTP Client 初始化完成 ({NAGATO_BASE_URL})")


async def close_http_client():
    """關閉 HTTP 客戶端"""
    global http_client
    if http_client:
        await http_client.aclose()
        print("✅ HTTP Client 已關閉")


async def cleanup_expired_sessions():
    """
    背景任務：定期清理過期的 Session
    
    每 1 分鐘檢查一次，刪除超過 5 分鐘的 session
    """
    import asyncio
    
    while True:
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL)  # 等待 1 分鐘
        
        current_time = time.time()
        expiry_seconds = SESSION_EXPIRY_MINUTES * 60  # 5 分鐘 = 300 秒
        expired_sessions = []
        
        # 找出過期的 session
        for session_id, created_at in session_created_at.items():
            if current_time - created_at > expiry_seconds:
                expired_sessions.append(session_id)
        
        # 刪除過期的 session
        if expired_sessions:
            print(f"🧹 發現 {len(expired_sessions)} 個過期 session，開始清理...")
            for session_id in expired_sessions:
                try:
                    await delete_session(session_id)
                    # del session_created_at[session_id]  # 已移除：delete_session 內部會處理
                    print(f"✅ 已刪除過期 session: {session_id}")
                except Exception as e:
                    print(f"❌ 刪除 session {session_id} 失敗：{e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命週期管理"""
    import asyncio
    
    # 啟動時
    initialize_modules()
    await initialize_http_client()
    
    # 啟動背景清理任務
    cleanup_task = asyncio.create_task(cleanup_expired_sessions())
    print(f"✅ Session 自動清理任務已啟動（每 {SESSION_CLEANUP_INTERVAL} 秒檢查，{SESSION_EXPIRY_MINUTES}分鐘過期）")
    
    yield
    
    # 關閉時
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await close_http_client()


app = FastAPI(title="Check Extension Bridge API Server", description="提供 Session 管理與電話號碼資料庫查詢的 API 接口", lifespan=lifespan)


# ==================== Session 管理 ====================

@app.get("/session")
async def create_session():
    """
    創建 Session（符合規範 Section 1.1）
    
    調用遠端 nagato 服務創建 session
    
    Response:
    {
        "sessionId": "0QENXBMJVRHV6",
        "metadata": {},
        "created_at": 1778211058,
        "last_active": 1778211058,
        "ttl_hours": 24
    }
    """
    try:
        # 調用遠端 API 創建 session
        response = await http_client.post(
            "/sessions",
            json={},
            headers={"Host": NAGATO_HOST}
        )
        response.raise_for_status()
        session_data = response.json()
        
        session_id = session_data.get("sessionId")
        created = int(time.time())
        
        # 記錄 session 創建時間（用於自動清理）
        session_created_at[session_id] = time.time()
        print(f"🆕 創建 Session: {session_id} (記錄創建時間：{created})")
        
        # 構建響應（符合規範格式）
        response_data = {
            "event": "done",
            "message": {
                "session_id": session_id,
                "metadata": session_data.get('metadata', {}),
                "created_at": session_data.get('created_at', created),
                "last_active": session_data.get('last_active', created),
                "ttl_hours": session_data.get('ttl_hours', 24)
            },
            "created": created,
            "id": f"{session_id}_{created}",
            "timing": {
                "total_ms": 1
            }
        }
        
        # 創建 JSONResponse 並設置 cookie
        response = JSONResponse(content=response_data)
        
        # 設置 Session ID Cookie（符合規範）
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="lax",
            path="/"
        )
        
        return response
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to create session: {e}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    獲取 Session 詳情
    
    調用遠端 nagato 服務獲取 session 詳情
    """
    try:
        response = await http_client.get(
            f"/sessions/{session_id}",
            headers={"Host": NAGATO_HOST}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to get session: {e}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")


@app.get("/sessions")
async def list_sessions():
    """
    獲取所有活躍 Session
    
    調用遠端 nagato 服務獲取 sessions 列表
    """
    try:
        response = await http_client.get(
            "/sessions",
            headers={"Host": NAGATO_HOST}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to list sessions: {e}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    刪除 Session
    
    調用遠端 nagato 服務刪除 session
    
    API: DELETE /sessions/{session_id}
    Header: Host: scroll.gc.ubicloud.net
    
    Response: 204 No Content (成功刪除，無返回內容)
    
    Example:
    curl -X DELETE 'http://140.227.187.126:6480/api/v1/sessions/{session_id}' \
      --header 'Host: scroll.gc.ubicloud.net'
    """
    try:
        response = await http_client.delete(
            f"/sessions/{session_id}",
            headers={"Host": NAGATO_HOST}
        )
        response.raise_for_status()
        
        # 從內存記錄中移除
        if session_id in session_created_at:
            del session_created_at[session_id]
        
        # 返回 204 No Content（RESTful API 規範）
        return Response(status_code=204)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # 從內存記錄中移除（如果存在）
            if session_id in session_created_at:
                del session_created_at[session_id]
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to delete session: {e}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """
    健康檢查
    
    返回各模組的就緒狀態。
    """
    return {
        "status": "ok",
        "modules": {
            "ext_query": "ready" if EXT_QUERY_AVAILABLE and retrieval_agent and final_agent else "not available",
            "nagato_api": "ready" if http_client else "not available"
        }
    }


# ==================== Chat Endpoint ====================

@app.post("/chat")
async def chat_endpoint(request: Request):
    """
    聊天查詢（SSE 串流）
    
    根據規範 AIJPDNC-QueryRESTAPIforDNC-110526-1134-192.pdf Section 1.2
    
    HTTP Method: POST
    Content-Type: application/json
    Accept: text/event-stream
    Cookie: session_id=<YOUR_SESSION_ID>
    
    Request Body:
    {
        "input": "${input}"
    }
    
    Response Headers:
    - Content-Type: text/event-stream; charset=utf-8
    - Cache-Control: no-cache
    - Connection: keep-alive
    
    Response Body (Stream):
    event: text_chunk
    data: {"event":"text_chunk","message":"","created":1778211058,"id":"EXT_0acbce59-4502-4eb8-8661-26cb1a6b222e_1778211058"}
    ...
    event: done
    data: {"event":"done","created":1778211058,"id":"EXT_0acbce59-4502-4eb8-8661-26cb1a6b222e_1778211058","timing":{...}}
    data: [DONE]
    
    Session Expired:
    HTTP Status: 401 Unauthorized
    Body: {"detail": "Session expired or invalid. Please re-initialize session."}
    """
    # 檢查模組就緒狀態
    if not EXT_QUERY_AVAILABLE or not retrieval_agent or not final_agent:
        raise HTTPException(status_code=503, detail="ext_query module not available")
    
    if not http_client:
        raise HTTPException(status_code=503, detail="Nagato API client not available")
    
    # 1. Session 管理（檢查 cookie 中的 session_id）
    session_id = request.cookies.get("session_id")
    
    # 如果沒有 session_id，返回 401（符合規範）
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid. Please re-initialize session."
        )
    
    print(f"🔄 使用 Session: {session_id}")
    
    # 3. 獲取用戶問題
    try:
        data = await request.json()
        user_query = data.get("input", "")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    if not user_query:
        raise HTTPException(status_code=400, detail="Missing 'input' in request body")
    
    # 4. 記錄用戶問題（調用遠端 API）
    try:
        await http_client.post(
            f"/sessions/{session_id}/messages",
            json={
                "messages": [
                    {"role": "user", "content": user_query}
                ]
            },
            headers={"Host": NAGATO_HOST}
        )
        print(f"💬 [Session: {session_id}] User: {user_query}")
    except Exception as e:
        print(f"⚠️ 記錄用戶消息失敗：{e}")
    
    # 5. ext_query 判斷流程
    async def event_generator():
        full_answer = ""
        start_time = time.time()
        
        # 獲取時間戳（請求開始時）- 用於所有事件
        created = int(time.time())
        
        # 生成事件 ID: {session_id}_{created}
        event_id = f"{session_id}_{created}"
        
        try:
            # 獲取對話歷史（調用遠端 API）
            messages = []
            try:
                response = await http_client.get(
                    f"/sessions/{session_id}/messages",
                    headers={"Host": NAGATO_HOST}
                )
                if response.status_code == 200:
                    data = response.json()
                    messages = data.get("messages", [])
                elif response.status_code == 404 or (response.status_code == 200 and response.json().get("service_code") == "69711001"):
                    # Session 不存在
                    print(f"⚠️ Session 不存在：{session_id}")
                    raise HTTPException(
                        status_code=401,
                        detail="Session expired or invalid. Please re-initialize session."
                    )
            except HTTPException:
                raise
            except Exception as e:
                print(f"⚠️ 獲取對話歷史失敗：{e}")
            
            conversation_history = {"user": [], "assistant": []}
            for msg in messages:
                if msg["role"] == "user":
                    conversation_history["user"].append(msg["content"])
                elif msg["role"] == "assistant":
                    conversation_history["assistant"].append(msg["content"])
            
            # Step A: 判斷意圖（傳入對話歷史）
            print(f"🔍 [Session: {session_id}] 判斷意圖...")
            keywords, display, is_ignore, search_result = await retrieval_agent.extract_keywords_from_query(
                user_query, 
                conversation_history=conversation_history
            )
            
            if is_ignore:
                # ignore_retrieve：LLM 已經從對話歷史提取了答案
                print(f"💬 [Session: {session_id}] ignore_retrieve，使用 LLM 提取的答案")
                
                # 先傳送 display（如果有）
                if display:
                    full_answer += display
                    yield f"event: text_chunk\ndata: {json.dumps({'event': 'text_chunk', 'message': display, 'created': created, 'id': event_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
                
                # 再傳送 search_result（如果有）
                if search_result:
                    search_display = f"<!-- json>{json.dumps(search_result, ensure_ascii=False)}</json -->"
                    full_answer += search_display
                    yield f"event: text_chunk\ndata: {json.dumps({'event': 'text_chunk', 'message': search_display, 'created': created, 'id': event_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
                
                # 如果都沒有
                if not display and not search_result:
                    full_answer = "申し訳ございませんが、回答を抽出できませんでした。"
                    
            elif keywords:
                # 需要查詢 → 呼叫資料庫
                print(f"🔍 [Session: {session_id}] 需要查詢：{keywords}")
                
                # 先回 display（等待中訊息）
                if display:
                    yield f"event: text_chunk\ndata: {json.dumps({'event': 'text_chunk', 'message': display, 'created': created, 'id': event_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
                
                # Step B: 搜尋資料庫
                results = await retrieval_agent.search_by_keywords(keywords)
                print(f"📊 [Session: {session_id}] 找到 {len(results)} 筆結果")
                
                # Step C: Final Agent 生成回答
                async for chunk in final_agent.generate_answer_stream(user_query, results):
                    if chunk == "[DONE]":
                        break
                    full_answer += chunk
                    
                    # SSE 格式：text_chunk（扁平結構）
                    yield f"event: text_chunk\ndata: {json.dumps({'event': 'text_chunk', 'message': chunk, 'created': created, 'id': event_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
            
            # Step D: 記錄系統回答（調用遠端 API）
            if full_answer:
                try:
                    await http_client.post(
                        f"/sessions/{session_id}/messages",
                        json={
                            "messages": [
                                {"role": "assistant", "content": full_answer}
                            ]
                        },
                        headers={"Host": NAGATO_HOST}
                    )
                    print(f"💬 [Session: {session_id}] Assistant: {full_answer[:50]}...")
                except Exception as e:
                    print(f"⚠️ 記錄助手消息失敗：{e}")
            
            # 計算計時數據
            end_time = time.time()
            timing = {
                "start_ms": int(start_time * 1000),
                "end_ms": int(end_time * 1000),
                "total_ms": int((end_time - start_time) * 1000)
            }
            
            # 完成事件（符合規範格式）
            yield f"event: done\ndata: {json.dumps({'event': 'done', 'created': created, 'id': event_id, 'timing': timing}, ensure_ascii=False, separators=(',', ':'))}\n\n"
            
            # [DONE] 標記（符合規範）
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"❌ [Session: {session_id}] 錯誤：{e}")
            error_time = int(time.time())
            error_id = f"{session_id}_{error_time}"
            
            # 錯誤事件
            yield f"event: error\ndata: {json.dumps({'event': 'error', 'message': str(e), 'created': error_time, 'id': error_id}, ensure_ascii=False, separators=(',', ':'))}\n\n"
            yield "data: [DONE]\n\n"
    
    # 返回 SSE 串流（使用 StreamingResponse）
    from fastapi.responses import StreamingResponse
    
    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8"
    )
    
    # 設置 Cache-Control（符合規範）
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    
    return response


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 啟動 Bridge API Server...")
    print(f"📍 Host: {BRIDGE_HOST}:{BRIDGE_PORT}")
    print(f"🔗 Nagato API: {NAGATO_BASE_URL}/tenants/{NAGATO_TENANT}")
    
    uvicorn.run(app, host=BRIDGE_HOST, port=BRIDGE_PORT)
