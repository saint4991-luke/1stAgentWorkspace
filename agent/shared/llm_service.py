"""
LLM 服務層 - 統一 LLM 訪問接口

為不同模組提供統一的 LLM 訪問接口，解耦模組與 Provider。
"""

from typing import List, Dict, Any, Optional
import asyncio


class LLMService:
    """統一 LLM 服務層（薄適配器）"""
    
    def __init__(self, provider):
        """
        初始化 LLM 服務
        
        Args:
            provider: LLM Provider 實例（from llm_providers）
        """
        self.provider = provider
    
    async def chat_for_virtual_human(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        use_reasoning: bool = False,
        temperature: float = 0,
        **kwargs
    ) -> str:
        """
        虛擬人專用對話接口
        
        Args:
            system_prompt: System Prompt（角色設定）
            messages: 對話歷史 [{"role": "user", "content": "..."}]
            use_reasoning: 是否啟用 reasoning（預設 False，快速回應）
            temperature: 溫度（預設 0，確定性回應）
            **kwargs: 額外參數（如 chat_template_kwargs）
        
        Returns:
            LLM 回應文字
        """
        # 組合完整的 messages（包含 system prompt）
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        # 調用 Provider（支持額外參數）
        # 預設 use_reasoning=False, temperature=0 以獲得快速、確定的回應
        response = await self.provider.chat(
            messages=full_messages,
            use_reasoning=use_reasoning,
            temperature=temperature,
            **kwargs
        )
        
        return response
    
    async def chat_for_knowledge(self, prompt: str, use_reasoning: bool = False, temperature: float = 0) -> str:
        """
        Knowledge 檢索專用接口
        
        Args:
            prompt: 判斷/檢索提示
            use_reasoning: 是否啟用 reasoning（預設 False，快速檢索）
            temperature: 溫度（預設 0，確定性回應）
        
        Returns:
            LLM 回應文字
        """
        # ⭐ 預設 use_reasoning=False, temperature=0 以獲得快速、確定的檢索結果
        response = await self.provider.chat(
            messages=[{"role": "user", "content": prompt}],
            use_reasoning=use_reasoning if use_reasoning is not True else False,  # 預設 False
            temperature=temperature
        )
        
        return response
    
    def chat_for_knowledge_sync(self, prompt: str) -> dict:
        """
        Knowledge 檢索同步接口（用於非非同步環境）
        
        Args:
            prompt: 判斷/檢索提示
        
        Returns:
            {
                "content": str,  # LLM 回應文字
                "usage": dict,   # Token usage（如果有）
                "elapsed_ms": int  # 執行時間
            }
        """
        try:
            # 檢查是否已有正在運行的 event loop
            loop = asyncio.get_running_loop()
            # 如果有，表示在異步環境中，需要用其他方式執行
            # 這裡用一個簡單的同步 HTTP 呼叫作為 fallback
            import httpx
            import os
            import time
            api_key = os.getenv('OPENAI_API_KEY', '')
            api_base = os.getenv('OPENAI_API_BASE', 'http://116.50.47.234:8081/v1')
            model = os.getenv('OPENAI_MODEL', 'Qwen/Qwen3.5-397B-A17B-FP8')
            
            # ⭐ 計時開始
            start_time = time.time()
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,  # 確定性回應
                        "chat_template_kwargs": {
                            "reasoning_effort": "low"  # 禁用深度推理，加速 RAG 檢索
                        }
                    }
                )
                result = response.json()
                
                # ⭐ 計時結束並記錄
                elapsed_ms = int((time.time() - start_time) * 1000)
                print(f"⏱️  chat_for_knowledge_sync: {elapsed_ms}ms")
                
                # ⭐ 獲取 usage（如果有）
                usage = result.get('usage', None)
                
                # 如果 LLM 沒有返回 usage，自行估算
                if not usage:
                    content = result['choices'][0]['message']['content']
                    usage = self._estimate_tokens(prompt, content)
                    print(f"📊 Token 估算：prompt={usage['prompt_tokens']}, completion={usage['completion_tokens']}")
                
                return {
                    "content": result['choices'][0]['message']['content'],
                    "usage": usage,
                    "elapsed_ms": elapsed_ms
                }
        except RuntimeError:
            # 沒有正在運行的 event loop，可以用 asyncio.run()
            # 使用 use_reasoning=False, temperature=0
            content = asyncio.run(self.chat_for_knowledge(prompt, use_reasoning=False, temperature=0))
            return {
                "content": content,
                "usage": self._estimate_tokens(prompt, content),
                "elapsed_ms": 0
            }
        except Exception as e:
            print(f"⚠️  chat_for_knowledge_sync 失敗：{e}")
            return {
                "content": "[]",
                "usage": None,
                "elapsed_ms": 0
            }
    
    def _estimate_tokens(self, prompt: str, content: str) -> dict:
        """
        估算 token 數量
        
        估算規則：
        - 中文：約 1.5 字符/token
        - 英文：約 4 字符/token
        - 混合：取平均約 3 字符/token
        
        Args:
            prompt: 輸入提示
            content: 輸出內容
        
        Returns:
            {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
        """
        # 簡單估算：中文字符約 1.5 個字符一個 token，英文約 4 個字符一個 token
        # 這裡用 3 作為平均值
        prompt_tokens = max(1, int(len(prompt) / 3))
        completion_tokens = max(1, int(len(content) / 3))
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "estimated": True  # 標記為估算值
        }


def create_llm_service(provider) -> LLMService:
    """
    創建 LLM 服務實例
    
    Args:
        provider: LLM Provider 實例
    
    Returns:
        LLMService 實例
    """
    return LLMService(provider)
