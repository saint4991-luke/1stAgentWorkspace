"""
ubillm_embedding.py - uBillm Embedding API 客戶端

兩階段呼叫流程：
1. 呼叫 Grant API 獲取 token 和 endpoint（type: "embedding"）
2. 使用 token 呼叫 Embedding API 獲取 vector
"""

import httpx
import os
import asyncio
import uvicorn

from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
#from milvus_searcher import MilvusSearcher

# 環境變數配置
UBILM_GRANT_URL = os.getenv("UBILM_GRANT_URL", "https://sage-stg.ubitus.ai/ubillm/api/v1/resource/grant")
UBILM_API_KEY = os.getenv("UBILM_API_KEY", "QZ8NinKF8TNfRucRmdEmfcZVqs28mEKeXbV44fI0cig")
UBILM_MODEL = os.getenv("UBILM_EMBED_MODEL", "qwen3-embedding-4b")

#app = FastAPI(title="text embedding api server", description="transfer text to vectors")


class uBillmEmbeddingClient:
    """uBillm Embedding API 客戶端"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or UBILM_API_KEY
        if not self.api_key:
            raise ValueError("UBILM_API_KEY 環境變數未設置")
    
    async def grant_token(self, model: str = "qwen3-embedding-4b", type: str = "embedding") -> Dict[str, str]:
        """Stage 1: 獲取 Embedding API token 和 endpoint"""
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
    
    async def get_embedding(
        self,
        text: str,
        model: str = "qwen3-embedding-4b",
        enable_thinking: bool = False,
        **kwargs
    ) -> List[float]:
        """
        獲取單段文字的 embedding vector
        
        Returns:
            embedding vector (float list) - 維度：2560
        """
        # Stage 1: 獲取 token
        grant_data = await self.grant_token(model=model, type="embedding")
        token = grant_data["api_token"]
        endpoint = grant_data["api_endpoint"]
        
        # Stage 2: 呼叫 Embedding API
        url = f"{endpoint}/v1/embeddings"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                    "Authorization": f"Bearer {token}"
                },
                json={
                    "input": text,
                    "model": model,
                    "stream": False,
                    "chat_template_kwargs": {"enable_thinking": enable_thinking},
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # 提取 embedding vector
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0].get("embedding", [])
            raise ValueError("Embedding API 回應格式錯誤")
    
    async def get_embeddings(
        self,
        texts: List[str],
        model: str = "qwen3-embedding-4b",
        enable_thinking: bool = False,
        **kwargs
    ) -> List[List[float]]:
        """
        獲取多段文字的 embedding vectors
        
        Returns:
            embedding vectors (list of float lists) - 每個 vector 維度：2560
        """
        # Stage 1: 獲取 token
        grant_data = await self.grant_token(model=model, type="embedding")
        token = grant_data["api_token"]
        endpoint = grant_data["api_endpoint"]
        
        # Stage 2: 呼叫 Embedding API
        url = f"{endpoint}/v1/embeddings"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                    "Authorization": f"Bearer {token}"
                },
                json={
                    "input": texts,
                    "model": model,
                    "stream": False,
                    "chat_template_kwargs": {"enable_thinking": enable_thinking},
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # 提取所有 embedding vectors
            if "data" in data:
                return [item.get("embedding", []) for item in data["data"]]
            raise ValueError("Embedding API 回應格式錯誤")


# 便捷函數
async def get_embedding(text: str, model: str = "qwen3-embedding-4b", api_key: Optional[str] = None, **kwargs) -> List[float]:
    """便捷函數：獲取單段文字的 embedding"""
    client = uBillmEmbeddingClient(api_key=api_key)
    return await client.get_embedding(text=text, model=model, **kwargs)


async def get_embeddings(texts: List[str], model: str = "qwen3-embedding-4b", api_key: Optional[str] = None, **kwargs) -> List[List[float]]:
    """便捷函數：獲取多段文字的 embeddings"""
    client = uBillmEmbeddingClient(api_key=api_key)
    return await client.get_embeddings(texts=texts, model=model, **kwargs)

# --- 定義 Request 模型 ---
class InputParserRequest(BaseModel):
    input: str = Field(..., description="使用者輸入的查詢字串")
'''
@app.post("/v1/telsurvey/textembedding", tags=["Embed"])
async def telsurvey_textembedding(request: InputParserRequest):
    try:
        vector = await get_embedding(request.input)
        print(f"Vector 維度：{len(vector)}")  # 應該是 2560
        
        milvus_searcher = MilvusSearcher(
            uri="http://192.168.16.106:19530",
            db_name="jp_phone",
            collection_name="ext_number_0302"
        )
        try:
            results = milvus_searcher.search(
                query_vector=vector,
                limit=20,
                output_fields=["*"]
            )
            print(f"找到 {len(results)} 筆結果")
            # 格式化結果
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted = {
                    "rank": i,
                    "text": result['entity'].get('text', '')
                }
                formatted_results.append(formatted)
            return formatted_results

        except Exception as e:
            print(f"Milvus 搜尋失敗：{e}")
            return [{"error": f"Milvus 搜尋失敗：{e}"}]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"內部錯誤: {str(e)}")
'''
# 測試用
if __name__ == "__main__":
    #uvicorn.run(app, host="0.0.0.0", port=3005)
    ''' # how to test
    curl -X POST 'http://192.168.16.106:3005/v1/telsurvey/textembedding' \
  --header 'Content-Type: application/json' \
  --data '{
  "input": "山口"
  }'
    '''
    
    
    
    async def test():
        print("=== Embedding 測試 ===")
        text = "高島 (たかしま)"
        print(f"文字：{text}")
        vector = await get_embedding(text=text)
        print(f"Vector 維度：{len(vector)}")  # 應該是 2560
        print(f"Vector 前 10 個值：{vector[:10]}")

    asyncio.run(test())
    