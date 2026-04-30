"""
ubillm_client.py - uBillm LLM API 客戶端

兩階段呼叫流程：
1. 呼叫 Grant API 獲取 token 和 endpoint（token 5 秒內有效）
2. 使用 token 呼叫 Chat Completions API
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
PROMPT_FILE = Path(__file__).parent / "shared" / "prompts" / "ext_ubillm_client_prompt.txt"
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
        """Stage 1: 獲取 API token 和 endpoint"""
        async with httpx.AsyncClient(timeout=10.0) as client:
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
    
    async def chat_completions(
        self,
        endpoint: str,
        token: str,
        messages: List[Dict[str, str]],
        temperature: float = 0,
        enable_thinking: bool = False,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Stage 2: 呼叫 Chat Completions API"""
        url = f"{endpoint}/v1/chat/completions"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                },
                json={
                    "messages": messages,
                    "temperature": temperature,
                    "chat_template_kwargs": {"enable_thinking": enable_thinking},
                    "stream": stream,
                    **kwargs
                }
            )
            response.raise_for_status()
            return response.json()
                  
    async def call(
        self,
        model: str = "qwen3-8b-fp8",
        messages: Optional[List[Dict[str, str]]] = None,
        enable_thinking: bool = False,
        temperature: float = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """完整流程：自動獲取 token 並呼叫 LLM"""
        if messages is None:
            messages = []
        
        # Stage 1: 獲取 token
        grant_data = await self.grant_token(model=model)
        token = grant_data["api_token"]
        endpoint = grant_data["api_endpoint"]
        
        # Stage 2: 呼叫 LLM（5 秒內）
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
    自動加入 system prompt，並交錯組合 user 和 assistant 的對話歷史
    
    參數：
        user_messages: 用戶訊息列表 ["訊息 1", "訊息 2", ...]
        assistant_messages: 助手回應列表 ["回應 1", "回應 2", ...]
    
    內部會自動組合成：
        [
            {"role": "user", "content": user_message1},
            {"role": "assistant", "content": assistant_message1},
            {"role": "user", "content": user_message2},
            ...
        ]
    """
    client = uBillmClient(api_key=api_key)
    
    # 交錯組合 user 和 assistant 的訊息
    messages = []
    user_msgs = user_messages or []
    assistant_msgs = assistant_messages or []
    
    # 交錯組合（user, assistant, user, assistant, ...）
    for i, user_msg in enumerate(user_msgs):
        messages.append({"role": "user", "content": user_msg})
        if i < len(assistant_msgs):
            messages.append({"role": "assistant", "content": assistant_msgs[i]})
    
    # 自動加入 system prompt（如果還沒有）
    has_system = any(msg.get("role") == "system" for msg in messages)
    if not has_system:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    
    print(f"call_ubillm {messages=} ")
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
    
    
    