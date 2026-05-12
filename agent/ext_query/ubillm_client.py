"""
ubillm_client.py - uBillm LLM API 客戶端

兩階段呼叫流程：
1. 呼叫 Grant API 獲取 token 和 endpoint（token 5 秒內有效）
2. 使用 token 呼叫 Chat Completions API

錯誤處理：
- TimeoutException: 請求超時，返回 504 Gateway Timeout
- HTTPStatusError: HTTP 錯誤，返回 502 Bad Gateway
- RequestError: 網絡錯誤，返回 503 Service Unavailable
"""

import httpx
import os
import json

from typing import AsyncGenerator, Dict, Any, Optional
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path


# 環境變數配置
PROMPT_FILE = Path(__file__).parent.parent / "shared" / "prompts" / "ext_ubillm_client_prompt.txt"
UBILM_GRANT_URL = os.getenv("UBILM_GRANT_URL", "https://sage-stg.ubitus.ai/ubillm/api/v1/resource/grant")
UBILM_API_KEY = os.getenv("UBILM_API_KEY", "QZ8NinKF8TNfRucRmdEmfcZVqs28mEKeXbV44fI0cig")
UBILM_MODEL = os.getenv("UBILM_LLM_MODEL", "qwen3-8b-fp8")

#app = FastAPI(title="uBillm API Server", description="提供電話號碼資料庫查詢的 API 接口")

def load_system_prompt() -> str:
    """從檔案載入 system prompt"""
    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"警告：找不到 prompt 檔案 {PROMPT_FILE}，使用預設 prompt")
        return ""
    except Exception as e:
        print(f"警告：讀取 prompt 檔案失敗：{e}，使用預設 prompt")
        return ""

SYSTEM_PROMPT = load_system_prompt()
class uBillmClient:
    """uBillm LLM API 客戶端"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or UBILM_API_KEY
        if not self.api_key:
            raise ValueError("UBILM_API_KEY 環境變數未設置")
    
    async def grant_token(self, model: str = "qwen3-8b-fp8", type: str = "llm") -> Dict[str, str]:
        """
        Stage 1: 獲取 API token 和 endpoint
        
        Args:
            model: 請求的模型名稱
            type: 資源類型
        
        Returns:
            Dict with api_token and api_endpoint
        
        Raises:
            HTTPException: 當請求失敗時（包含詳細錯誤信息）
                - 504: Timeout
                - 502: HTTP 錯誤
                - 503: 網絡錯誤
        """
        try:
            # 設置 timeout：connect=5s, read=10s, write=10s
            timeout = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    UBILM_GRANT_URL,
                    json={
                        "api_key": self.api_key,
                        "model": model,
                        "type": type
                    }
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException as e:
            print(f"❌ grant_token timeout: {e}")
            raise HTTPException(
                status_code=504,
                detail=f"Grant API timeout: {str(e)}"
            )
            
        except httpx.HTTPStatusError as e:
            error_detail = f"Grant API HTTP {e.response.status_code}: {e.response.text[:200]}"
            print(f"❌ grant_token HTTP error: {error_detail}")
            raise HTTPException(
                status_code=502,
                detail=f"Grant API failed: {error_detail}"
            )
            
        except httpx.RequestError as e:
            print(f"❌ grant_token request error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Grant API network error: {str(e)}"
            )
    
    async def chat_completions(
        self,
        endpoint: str,
        token: str,
        messages: List[Dict[str, str]],
        temperature: float = 0,
        enable_thinking: bool = False,
        stream: bool = False,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Stage 2: 呼叫 Chat Completions API
        
        Args:
            endpoint: API endpoint URL
            token: API token
            messages: 對話訊息列表
            temperature: 溫度參數
            enable_thinking: 是否啟用思考模式
            stream: 是否使用串流模式
            max_tokens: 最大生成 token 數（預設 2000）
        
        Returns:
            LLM 響應字典
        
        Raises:
            HTTPException: 當請求失敗時（包含詳細錯誤信息）
                - 504: Timeout
                - 502: HTTP 錯誤
                - 503: 網絡錯誤
        """
        url = f"{endpoint}/v1/chat/completions"
        
        try:
            # 設置 timeout：connect=5s, read=30s, write=30s
            timeout = httpx.Timeout(30.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}"
                    },
                    json={
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "chat_template_kwargs": {"enable_thinking": enable_thinking},
                        "stream": stream,
                        **kwargs
                    }
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException as e:
            print(f"❌ chat_completions timeout: {e}")
            raise HTTPException(
                status_code=504,
                detail=f"Chat API timeout: {str(e)}"
            )
            
        except httpx.HTTPStatusError as e:
            error_detail = f"Chat API HTTP {e.response.status_code}: {e.response.text[:200]}"
            print(f"❌ chat_completions HTTP error: {error_detail}")
            raise HTTPException(
                status_code=502,
                detail=f"Chat API failed: {error_detail}"
            )
            
        except httpx.RequestError as e:
            print(f"❌ chat_completions request error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Chat API network error: {str(e)}"
            )
                  
    async def call(
        self,
        model: str = "qwen3-8b-fp8",
        messages: Optional[List[Dict[str, str]]] = None,
        enable_thinking: bool = False,
        temperature: float = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        完整流程：自動獲取 token 並呼叫 LLM
        
        Args:
            model: 模型名稱
            messages: 對話訊息列表
            enable_thinking: 是否啟用思考模式
            temperature: 溫度參數
        
        Returns:
            LLM 響應字典（包含 _endpoint 字段）
        
        Raises:
            HTTPException: 當任一階段失敗時
        """
        if messages is None:
            messages = []
        
        try:
            # Stage 1: 獲取 token
            grant_data = await self.grant_token(model=model)
            token = grant_data["api_token"]
            endpoint = grant_data["api_endpoint"]
            
            # Stage 2: 呼叫 LLM
            response = await self.chat_completions(
                endpoint=endpoint,
                token=token,
                messages=messages,
                temperature=temperature,
                enable_thinking=enable_thinking,
                **kwargs
            )
            
            # 加入 endpoint 資訊方便除錯
            response["_endpoint"] = endpoint
            return response
            
        except HTTPException:
            # 已經處理過的 HTTPException 直接拋出
            raise
        except Exception as e:
            # 未預期的錯誤
            print(f"❌ call 發生意外錯誤：{e}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error: {str(e)}"
            )

# 便捷函數
async def call_ubillm(
    model: str = "qwen3-8b-fp8",
    user_messages: Optional[List[str]] = None,
    assistant_messages: Optional[List[str]] = None,
    enable_thinking: bool = False,
    temperature: float = 0,
    api_key: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    便捷函數：呼叫 uBillm LLM API（電話號碼資料庫查詢）
    自動加入 system prompt，並交錯組合 user 和 tool 的對話歷史
    
    參數：
        model: 模型名稱
        user_messages: 用戶訊息列表 ["訊息 1", "訊息 2", ...]
        assistant_messages: 工具回應列表 ["回應 1", "回應 2", ...]
        enable_thinking: 是否啟用思考模式
        temperature: 溫度參數
        api_key: API 金鑰（可選，預設使用環境變數）
    
    內部會自動組合成：
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message1},
            {"role": "tool", "content": tool_message1},
            {"role": "user", "content": user_message2},
            ...
        ]
    
    Returns:
        LLM 響應字典
    
    Raises:
        HTTPException: 當 API 請求失敗時（包含詳細錯誤信息）
            - 504: Timeout（超時）
            - 502: HTTP 錯誤（API 返回錯誤）
            - 503: 服務不可用（網絡錯誤）
            - 500: 未預期錯誤
    """
    client = uBillmClient(api_key=api_key)
    
    # 交錯組合 user 和 tool 的訊息
    messages = []
    user_msgs = user_messages or []
    assistant_msgs = assistant_messages or []
    
    # 交錯組合（user, tool, user, tool, ...）
    for i, user_msg in enumerate(user_msgs):
        messages.append({"role": "user", "content": user_msg})
        if i < len(assistant_msgs):
            messages.append({"role": "tool", "content": assistant_msgs[i]})
    
    # 自動加入 system prompt（如果還沒有）
    has_system = any(msg.get("role") == "system" for msg in messages)
    if not has_system:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    
    print(f"call_ubillm {messages=} ")
    
    # 呼叫 LLM，異常會直接拋出給調用者處理
    return await client.call(
        model=UBILM_MODEL,
        messages=messages,
        enable_thinking=enable_thinking,
        temperature=temperature,
        **kwargs
    )

# --- 定義 Request 模型 ---
class Message(BaseModel):
    role: str = Field(..., description="角色: system, user, 或 assistant")
    content: str = Field(..., description="對話內容")

class InputParserRequest(BaseModel):
    input: str = Field(..., description="使用者輸入的查詢字串")
    model: str = "qwen3-8b-fp8"
    enable_thinking: bool = False
    temperature: float = 0.0
'''
@app.post("/telsurvey/inputparser", tags=["LLM"])
async def telsurvey_inputparser(request: InputParserRequest):
    try:
        # 將單一的 input 字串包裝成 call_ubillm 預期的 messages 格式
        formatted_messages = [
            {"role": "user", "content": request.input}
        ]
        
        # 呼叫你原本的 async 函數
        response = await call_ubillm(
            model=request.model,
            messages=formatted_messages,
            enable_thinking=request.enable_thinking,
            temperature=request.temperature
        )
        
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"內部錯誤: {str(e)}")
'''

# 測試用
if __name__ == "__main__":
    import asyncio
    async def test():
        print("=== 電話號碼查詢測試（單一訊息）===")
        response = await call_ubillm(
            model=UBILM_MODEL,
            user_messages=["消基會會長的內線分機"],
            enable_thinking=False
        )
        print(response["choices"][0]["message"]["content"])
        
        print("\n=== 電話號碼查詢測試（多輪對話）===")
        response = await call_ubillm(
            model=UBILM_MODEL,
            user_messages=["遠藤和也的電話號碼是？", "那個部門是什麼？"],
            assistant_messages=["遠藤和也の内線番号は 1121 です。"],
            enable_thinking=False
        )
        print(response["choices"][0]["message"]["content"])
    
    asyncio.run(test())
    
    
    