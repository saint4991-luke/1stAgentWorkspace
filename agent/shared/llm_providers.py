#!/usr/bin/env python3
"""
🦐 蝦米 Agent v3.2.1 - LLM Provider 抽象層

支援多種 LLM Provider：
- OpenAIProvider: OpenAI 相容 API (OpenAI, vLLM, LocalAI, Ollama)
- UbisageProvider: Ubisage 私有模型 (需要 Token 交換)
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncGenerator
from datetime import datetime, timedelta
import asyncio

# ============= 抽象基底類 =============

class LLMProvider(ABC):
    """LLM Provider 抽象基底類"""
    
    def __init__(self, model: str, **kwargs):
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    async def chat(self, messages: List[Dict]) -> str:
        """
        非流式聊天
        
        Args:
            messages: 訊息列表 [{"role": "user", "content": "..."}]
        
        Returns:
            回應內容字串
        """
        pass
    
    @abstractmethod
    async def chat_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """
        流式聊天
        
        Args:
            messages: 訊息列表
        
        Yields:
            逐步輸出的內容片段
        """
        pass
    
    @abstractmethod
    async def get_token(self) -> Optional[str]:
        """
        獲取訪問 Token
        
        Returns:
            Token 字串，如果不需要則返回 None
        """
        pass


# ============= OpenAI Provider =============

class OpenAIProvider(LLMProvider):
    """
    OpenAI 相容 Provider
    
    支援：
    - OpenAI (api.openai.com)
    - vLLM (本地部署)
    - LocalAI
    - Ollama (with OpenAI compatibility)
    - Azure OpenAI
    """
    
    def __init__(self, model: str, api_key: str, base_url: str, 
                 max_tokens: int = 4096, timeout: float = 30.0, **kwargs):
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client = None
    
    @property
    def client(self):
        """延遲初始化 OpenAI Client"""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client
    
    async def get_token(self) -> Optional[str]:
        """OpenAI 不需要額外 Token，直接返回 API Key"""
        return self.api_key
    
    async def chat(self, messages: List[Dict], use_reasoning: bool = True, **kwargs) -> str:
        """
        非流式聊天
        
        Args:
            messages: 訊息列表
            use_reasoning: 是否啟用 reasoning（預設 True）
            **kwargs: 額外參數（temperature, chat_template_kwargs, extra_body 等）
        """
        try:
            # 構建請求參數
            create_kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens
            }
            
            # 統一接口：use_reasoning=False 時自動轉換為 Provider 特定格式
            if not use_reasoning:
                # OpenAI Provider (本地 Qwen Server) 使用 enable_thinking: false
                kwargs["chat_template_kwargs"] = {"enable_thinking": False}
            
            # 支持 chat_template_kwargs（Qwen3.5 非 thinking 模式）
            if "chat_template_kwargs" in kwargs:
                if "extra_body" not in kwargs:
                    kwargs["extra_body"] = {}
                kwargs["extra_body"]["chat_template_kwargs"] = kwargs["chat_template_kwargs"]
            
            # 添加 extra_body（用於 Qwen3.5 的 extra_body 參數）
            if "extra_body" in kwargs:
                create_kwargs["extra_body"] = kwargs["extra_body"]
            
            # 添加 temperature 等其他參數
            for key in ["temperature", "top_p", "presence_penalty", "frequency_penalty"]:
                if key in kwargs:
                    create_kwargs[key] = kwargs[key]
            
            response = await self.client.chat.completions.create(**create_kwargs)
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API 請求失敗：{str(e)}")
    
    async def chat_stream(self, messages: List[Dict], use_reasoning: bool = True, **kwargs) -> AsyncGenerator[str, None]:
        """
        流式聊天
        
        Args:
            messages: 訊息列表
            use_reasoning: 是否啟用 reasoning（預設 True）
            **kwargs: 額外參數（temperature, chat_template_kwargs, extra_body 等）
        """
        try:
            # 構建請求參數
            create_kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "stream": True
            }
            
            # 統一接口：use_reasoning=False 時自動轉換為 Provider 特定格式
            if not use_reasoning:
                # OpenAI Provider (本地 Qwen Server) 使用 enable_thinking: false
                kwargs["chat_template_kwargs"] = {"enable_thinking": False}
            
            # 支持 chat_template_kwargs
            if "chat_template_kwargs" in kwargs:
                if "extra_body" not in kwargs:
                    kwargs["extra_body"] = {}
                kwargs["extra_body"]["chat_template_kwargs"] = kwargs["chat_template_kwargs"]
            
            # 添加 extra_body
            if "extra_body" in kwargs:
                create_kwargs["extra_body"] = kwargs["extra_body"]
            
            # 添加 temperature 等其他參數
            for key in ["temperature", "top_p", "presence_penalty", "frequency_penalty"]:
                if key in kwargs:
                    create_kwargs[key] = kwargs[key]
            
            stream = await self.client.chat.completions.create(**create_kwargs)
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
        except Exception as e:
            raise Exception(f"OpenAI 流式請求失敗：{str(e)}")
    
    async def chat_with_tools(self, messages: List[Dict], tools: List[Dict], use_reasoning: bool = True, temperature: float = 0, **kwargs) -> Dict:
        """
        聊天並支援 Tool 呼叫
        
        Args:
            messages: 訊息列表
            tools: Tool 定義列表
            use_reasoning: 是否啟用 reasoning（預設 False，快速回應）
            temperature: 溫度（預設 0，確定性回應）
            **kwargs: 額外參數
        
        Returns:
            {
                "content": str,  # LLM 回應內容
                "tool_calls": List[Dict],  # Tool 呼叫列表（如果有）
                "needs_tool_execution": bool  # 是否需要執行 Tool
            }
        """
        try:
            # 構建請求參數
            create_kwargs = {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "max_tokens": self.max_tokens
            }
            
            # 統一接口：use_reasoning=False 時自動轉換為 Provider 特定格式
            if not use_reasoning:
                # OpenAI Provider (本地 Qwen Server) 使用 enable_thinking: false
                kwargs["chat_template_kwargs"] = {"enable_thinking": False}
            
            # 支持 chat_template_kwargs
            if "chat_template_kwargs" in kwargs:
                if "extra_body" not in kwargs:
                    kwargs["extra_body"] = {}
                kwargs["extra_body"]["chat_template_kwargs"] = kwargs["chat_template_kwargs"]
            
            # 添加 extra_body
            if "extra_body" in kwargs:
                create_kwargs["extra_body"] = kwargs["extra_body"]
            
            # 添加 temperature
            create_kwargs["temperature"] = temperature
            
            response = await self.client.chat.completions.create(**create_kwargs)
            
            choice = response.choices[0].message
            
            result = {
                "content": choice.content or "",
                "tool_calls": [],
                "needs_tool_execution": False,
                "usage": getattr(response, 'usage', None)
            }
            
            # 檢查是否有 Tool 呼叫
            if hasattr(choice, 'tool_calls') and choice.tool_calls:
                for tc in choice.tool_calls:
                    result["tool_calls"].append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    })
                result["needs_tool_execution"] = True
            
            return result
        except Exception as e:
            raise Exception(f"OpenAI Tool 請求失敗：{str(e)}")


# ============= Ubisage Provider =============

class UbisageProvider(LLMProvider):
    """
    Ubisage 私有模型 Provider
    
    特點：
    - 需要 Token 交換（每次訪問前先獲取 Token）
    - Token 有效期 5 秒，每次請求前重新獲取
    - 獲取 api_token + api_endpoint
    - 使用 OpenAI 相容 API 呼叫
    
    API 流程：
    1. POST /ubillm/api/v1/resource/grant → 獲取 api_token, api_endpoint
    2. POST {api_endpoint}/v1/chat/completions → 使用 Token 呼叫
    """
    
    def __init__(self, model: str, api_key: str, 
                 grant_url: str = "https://sage-stg.ubitus.ai/ubillm/api/v1/resource/grant",
                 **kwargs):
        """
        Args:
            model: 模型名稱 (e.g., "qwen3-8b-fp8")
            api_key: Ubisage API Key (用於換 Token)
            grant_url: Token 交換 API URL
        """
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self.grant_url = grant_url
        
        # Token 緩存（只用於當前請求，不跨請求緩存）
        self._token_lock = asyncio.Lock()
    
    async def get_token(self):
        """
        獲取 Ubisage Token（每次請求前都要重新獲取）
        
        Returns:
            (api_token, api_endpoint) 元組
        """
        import aiohttp
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "api_key": self.api_key,
            "model": self.model,
            "type": "llm"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.grant_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("api_token"), data.get("api_endpoint")
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ubisage Token 交換失敗 (HTTP {response.status}): {error_text}")
        except aiohttp.ClientError as e:
            raise Exception(f"Ubisage Token 交換網路錯誤：{str(e)}")
    
    async def chat(self, messages: List[Dict], use_reasoning: bool = True, **kwargs) -> str:
        """
        非流式聊天
        
        每次請求前都要重新獲取 Token（一次性使用）
        
        Args:
            messages: 訊息列表
            use_reasoning: 是否啟用 reasoning（預設 True）
            **kwargs: 額外參數（temperature 等）
        
        使用 OpenAI 相容 API：
        POST {api_endpoint}/v1/chat/completions
        Authorization: Bearer {api_token}
        """
        import aiohttp
        
        # 每次請求前都要重新獲取 Token
        token, endpoint = await self.get_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # OpenAI 相容格式
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        
        # 統一接口：use_reasoning=False 時自動轉換為 Provider 特定格式
        if not use_reasoning:
            # Ubisage Provider 使用 enable_thinking: false
            kwargs["chat_template_kwargs"] = {"enable_thinking": False}
        
        # 添加額外參數
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "chat_template_kwargs" in kwargs:
            payload["chat_template_kwargs"] = kwargs["chat_template_kwargs"]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint}/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    else:
                        error_text = await response.text()
                        raise Exception(
                            f"Ubisage API 請求失敗 (HTTP {response.status}): {error_text}"
                        )
        except aiohttp.ClientError as e:
            raise Exception(f"Ubisage API 網路錯誤：{str(e)}")
    
    async def chat_stream(self, messages: List[Dict], use_reasoning: bool = True, **kwargs) -> AsyncGenerator[str, None]:
        """
        流式聊天
        
        每次請求前都要重新獲取 Token（一次性使用）
        
        Args:
            messages: 訊息列表
            use_reasoning: 是否啟用 reasoning（預設 True）
            **kwargs: 額外參數（temperature 等）
        
        使用 OpenAI 相容 API with stream=true
        """
        import aiohttp
        
        # 每次請求前都要重新獲取 Token
        token, endpoint = await self.get_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        
        # 統一接口：use_reasoning=False 時自動轉換為 Provider 特定格式
        if not use_reasoning:
            # Ubisage Provider 使用 enable_thinking: false
            kwargs["chat_template_kwargs"] = {"enable_thinking": False}
        
        # 添加額外參數
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "chat_template_kwargs" in kwargs:
            payload["chat_template_kwargs"] = kwargs["chat_template_kwargs"]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint}/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        # SSE 流式解析
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    break
                                try:
                                    import json
                                    chunk_data = json.loads(data)
                                    delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                except:
                                    continue
                    else:
                        error_text = await response.text()
                        raise Exception(
                            f"Ubisage 流式請求失敗 (HTTP {response.status}): {error_text}"
                        )
        except aiohttp.ClientError as e:
            raise Exception(f"Ubisage 流式網路錯誤：{str(e)}")


# ============= Provider 註冊表 =============

# 可用的 Provider 列表
AVAILABLE_PROVIDERS = {
    "openai": OpenAIProvider,
    "ubisage": UbisageProvider,
}


def get_provider_class(provider_type: str) -> type:
    """
    根據類型獲取 Provider 類
    
    Args:
        provider_type: Provider 類型 ("openai", "ubisage")
    
    Returns:
        Provider 類
    
    Raises:
        ValueError: 如果 Provider 類型不存在
    """
    if provider_type not in AVAILABLE_PROVIDERS:
        available = ", ".join(AVAILABLE_PROVIDERS.keys())
        raise ValueError(
            f"未知的 Provider 類型：{provider_type}\n"
            f"可用的 Provider: {available}"
        )
    return AVAILABLE_PROVIDERS[provider_type]


def list_providers() -> List[str]:
    """列出所有可用的 Provider 類型"""
    return list(AVAILABLE_PROVIDERS.keys())
