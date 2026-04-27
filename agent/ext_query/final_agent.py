"""
final_agent.py - 最終回答整理 Agent

將 retrieval 結果和用戶問題傳給 LLM API，生成最終回答
"""

import httpx
import os
import json
import re

from typing import List, Dict, Any, Optional, AsyncGenerator
from pathlib import Path

# 環境變數配置
PROMPT_FILE = Path(__file__).parent / "shared" / "prompts" / "ext_final_agent_prompt.txt"
UBIGPT_FQDN = os.getenv("UBIGPT_FQDN", "https://g.ubitus.ai/v1/chat/completions")
UBIGPT_AUTH_KEY = os.getenv("UBIGPT_AUTH_KEY", "Bearer +5/tIEiUce9skGhe+mPt6AjL7TPY2kAvKNzvcilblHc73FAndMfH5EICwOSHPLbB3qN85eGTFlEGwJBItrQVcg==")
UBIGPT_MODEL = os.getenv("UBIGPT_MODEL", "llama-4-maverick-fp8")


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


class FinalAgent:
    """最終回答整理 Agent"""
    
    def __init__(
        self,
        api_url: str = None,
        auth_key: str = None,
        model: str = None
    ):
        self.api_url = api_url or UBIGPT_FQDN
        self.auth_key = auth_key or UBIGPT_AUTH_KEY
        self.model = model or UBIGPT_MODEL
        
        if not self.auth_key:
            raise ValueError("UBIGPT_AUTH_KEY 環境變數未設置")
    
    def format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """
        格式化搜尋結果為文字
        
        Args:
            results: retrieval_agent 的搜尋結果
        
        Returns:
            格式化後的文字
        """
        if not results:
            return "該当する情報が見つかりませんでした。"
        print(f"format_search_results {results=}\n")
        formatted_lines = []
        for result in results:
            if "error" in result:
                continue
            
            entity = result.get("entity", {})
            text = entity.get("text", "")
            text_content = entity.get("content", "")
            
            if text:    # Milvus results
                formatted_lines.append(text)
            if text_content:    # qdrant results
                formatted_lines.append(text_content)
        
        if not formatted_lines:
            return "該当する情報が見つかりませんでした。"
        
        return "\n".join(formatted_lines)
    
    async def generate_answer(
        self,
        user_question: str,
        search_results: List[Dict[str, Any]]
    ) -> str:
        """
        生成最終回答
        
        Args:
            user_question: 用戶問題
            search_results: retrieval_agent 的搜尋結果
        
        Returns:
            LLM 生成的最終回答
        """
        # 格式化搜尋結果
        formatted_results = self.format_search_results(search_results)
        
        # 構建 system prompt
        system_prompt = SYSTEM_PROMPT.format(question=user_question)
        
        # 構建 messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""ユーザーの質問：{user_question}

            検索結果：
            {formatted_results}

            上記の情報に基づいて、最終的な回答を生成してください。"""}
        ]
        print(f"luke0408 {messages=}")
        # 呼叫 LLM API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": self.auth_key
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 500
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # 提取回答
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                return "申し訳ございませんが、回答を生成できませんでした。"
            
    async def generate_answer_stream(
        self,
        user_question: str,
        search_results: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        print(f"3. generate_answer_stream \n")
        formatted_results = self.format_search_results(search_results)
        #print(f"generate_answer_stream {formatted_results=}\n")
        
        system_prompt = SYSTEM_PROMPT
        system_prompt.replace("{question}", user_question)
        #print(f"generate_answer_stream {system_prompt=}\n")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.auth_key
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"ユーザーの質問：{user_question}\n\n検索結果：\n{formatted_results}\n\n上記の情報に基づいて、最終的な回答を生成してください。"}
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 500,
            "stream": True
        }
        print(f"generate_answer_stream {payload=}\n")

        final_content = ""
        # 使用 AsyncClient
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream("POST", self.api_url, headers=headers, json=payload) as response:
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            yield "[DONE]"
                            break
                        
                        try:
                            data_json = json.loads(data_str)
                            choices = data_json.get("choices", [])
                            
                            if choices:
                                choice = choices[0]
                                
                                # 先找 delta，找不到就找 message
                                content_holder = choice.get("delta") or choice.get("message")
                                
                                if content_holder:
                                    content = content_holder.get("content", "")
                                    if content:
                                        #print(f"Captured: {content}") 
                                        final_content += content
                                        yield content
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print(f"Parsing error: {e}")
            except Exception as e:
                yield f"Connection Error: {str(e)}"
        clean_content = re.sub(r"\n+", "", final_content)
        print(f"{clean_content=}\n") 
        

# 便捷函數
async def generate_final_answer(
    user_question: str,
    search_results: List[Dict[str, Any]],
    api_url: str = None,
    auth_key: str = None,
    model: str = None
) -> str:
    """
    便捷函數：生成最終回答
    
    Args:
        user_question: 用戶問題
        search_results: retrieval_agent 的搜尋結果
        api_url: LLM API URL
        auth_key: 認證金鑰
        model: 模型名稱
    
    Returns:
        最終回答
    """
    agent = FinalAgent(
        api_url=api_url,
        auth_key=auth_key,
        model=model
    )
    return await agent.generate_answer(user_question, search_results)


# 測試用
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=== Final Agent 測試 ===\n")
        
        # 模擬搜尋結果
        mock_results = [
            {
                "rank": 1,
                "score": 0.95,
                "entity": {
                    "id": "1121",
                    "text": "管理本部 経営企画部 次長 遠藤 和也 えんどう かずや, 内線番号 1121"
                }
            }
        ]
        
        # 測試生成
        answer = await generate_final_answer(
            user_question="我要找遠藤和也",
            search_results=mock_results
        )
        
        print(f"用戶問題：我要找遠藤和也")
        print(f"\n最終回答：\n{answer}")

    asyncio.run(test())