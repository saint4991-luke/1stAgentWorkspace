"""
retrieval_agent.py - 電話號碼資料庫 Retrieval Agent

完整流程：
1. 呼叫 ubillm_client 解析用戶意圖，提取關鍵字
2. 呼叫 ubillm_embedding 將關鍵字轉換為 vector
3. 用 Milvus 搜尋匹配的電話號碼
"""
import os
import json
import re
import asyncio
import uvicorn
import argparse

from typing import List, Dict, Any, Tuple, AsyncGenerator
from ubillm_client import call_ubillm
from ubillm_embedding import get_embedding
#from milvus_searcher import MilvusSearcher
from qdrant_client import QdrantClient  # pip install qdrant-client
from qdrant_client.http import models
from final_agent import FinalAgent
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse   # pip install "starlette<0.41.0,>=0.37.2" sse-starlette
from log_redirector import setup_logging


UBILM_LLM_MODEL = os.getenv("UBILM_LLM_MODEL", "qwen3-8b-fp8")
UBILM_EMBED_MODEL = os.getenv("UBILM_EMBED_MODEL", "qwen3-embedding-4b")
QDRANT_HOST = os.getenv("QDRANT_HOST", "140.227.187.126")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6334")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "default_kb_832887850831363957")


app = FastAPI(title="Check Extension API Server", description="提供電話號碼資料庫查詢的 API 接口")
setup_logging("ext_query")

class RetrievalAgent:
    """電話號碼資料庫 Retrieval Agent"""
    
    def __init__(
        self,
        milvus_uri: str = "http://192.168.16.106:19530",
        milvus_db: str = "jp_phone",
        milvus_collection: str = "ext_number_0302",
        milvus_vector_field: str = "text_embedding",
        search_limit: int = 20
    ):
        self.ubillm_model = UBILM_LLM_MODEL
        self.embedding_model = UBILM_EMBED_MODEL
        self.milvus_uri = milvus_uri
        self.milvus_db = milvus_db
        self.milvus_collection = milvus_collection
        self.milvus_vector_field = milvus_vector_field
        self.search_limit = search_limit
        
        # 初始化 Milvus 搜尋器
        '''
        self.milvus_searcher = MilvusSearcher(
            uri=milvus_uri,
            db_name=milvus_db,
            collection_name=milvus_collection
        )
        '''
    
    def parse_ubillm_response(self, content: str) -> List[Dict[str, Any]]:
        """解析 uBillm 的 JSON 響應"""
        try:
            json_match = re.search(r'```json\s*(.+?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                return json.loads(json_str)
            return json.loads(content)
        except Exception as e:
            print(f"JSON 解析失敗：{e}")
            return []
    
    def extract_keywords(self, tool_calls: List[Dict[str, Any]]) -> Tuple[List[str], str, bool]:
        """從工具調用中提取關鍵字
        
        Returns:
            keywords: 關鍵字列表（retrieve_from_text 時有值）
            displayStr: 顯示訊息（兩者都有）
            is_ignore_retrieve: 是否為 ignore_retrieve 模式
        """
        keywords = []
        displayStr = ""
        is_ignore = False
        
        for call in tool_calls:
            tool = call.get("tool")
            
            if tool == "retrieve_from_text":
                tool_input = call.get("tool_input", {})
                query = tool_input.get("x", "")
                if query:
                    keywords.append(query)
                tool_display = call.get("tool_display", {})
                displayStr = tool_display.get("y", "")
                
            elif tool == "ignore_retrieve":
                is_ignore = True
                tool_display = call.get("tool_display", {})
                displayStr = tool_display.get("y", "")
                # 不提取 keywords，保持空列表
        
        return keywords, displayStr, is_ignore
    
    async def extract_keywords_from_query(self, user_query: str, conversation_history: Dict[str, List[str]] = None) -> Tuple[List[str], str, bool]:
        """
        Step 1: 呼叫 uBillm 解析用戶意圖，提取關鍵字
        
        Args:
            user_query: 用戶查詢（例如："我要找公共安全組的高島"）
            conversation_history: 對話歷史 {"user": [...], "assistant": [...]}（已包含當前查詢）
        
        Returns:
            keywords: 關鍵字列表
            display: 顯示訊息
            is_ignore: 是否為 ignore_retrieve 模式
        """
        print("Step 1: 解析用戶意圖...")
        
        # 準備對話歷史（bridge.py 已經將當前 user_query 添加到 conversation_history 中）
        user_messages = conversation_history.get("user", []) if conversation_history else []
        assistant_messages = conversation_history.get("assistant", []) if conversation_history else []
        
        ubillm_response = await call_ubillm(
            model=self.ubillm_model,
            user_messages=user_messages,
            assistant_messages=assistant_messages,
            enable_thinking=False
        )
        
        content = ubillm_response["choices"][0]["message"]["content"]
        print(f"uBillm 響應：{content[:200]}...")
        
        # 解析 JSON
        tool_calls = self.parse_ubillm_response(content)
        if not tool_calls:
            return [], None, False
        
        # 提取關鍵字
        keywords, displayStr, is_ignore = self.extract_keywords(tool_calls)
        if not keywords and not is_ignore:
            return [], displayStr, False
        
        print(f"{keywords=} {displayStr=} {is_ignore=}")
        return keywords, displayStr, is_ignore

    async def extract_keywords_from_query_gen(self, user_query: str, conversation_history: Dict[str, List[str]] = None) -> AsyncGenerator[dict, None]:
        # 準備對話歷史（bridge.py 已經將當前 user_query 添加到 conversation_history 中）
        user_messages = conversation_history.get("user", []) if conversation_history else []
        assistant_messages = conversation_history.get("assistant", []) if conversation_history else []
        
        ubillm_response = await call_ubillm(
            model=self.ubillm_model,
            user_messages=user_messages,
            assistant_messages=assistant_messages,
            enable_thinking=False
        )
        
        content = ubillm_response["choices"][0]["message"]["content"]
        tool_calls = self.parse_ubillm_response(content)
        print(f"extract_keywords_from_query_gen {tool_calls=}\n")
        if not tool_calls:
            print('status=eror')
            yield {"status": "error", "message": "無法解析關鍵字"}
            return

        keywords, displayStr = self.extract_keywords(tool_calls)
        if not keywords:
            yield {"status": "error", "message": "無法解析關鍵字"}
            return
        print(f'extract_keywords_from_query_gen status=completed {keywords=} {displayStr=}\n')
        yield {"status": "completed", "keywords": keywords, "display": displayStr}
    
    async def search_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        根據關鍵字搜尋電話號碼
        
        Args:
            keywords: 關鍵字列表（例如：["高島 (たかしま)"]）
        
        Returns:
            搜尋結果列表
        """
        # Step 2: 獲取 embedding vectors
        print("Step 2: 獲取 embeddings...")
        try:
            vectors = await get_embedding(
                text=", ".join(keywords),
                model=self.embedding_model
            )
            print(f"Vector 維度：{len(vectors)}")
        except Exception as e:
            print(f"Embedding 失敗：{e}")
            return [{"error": f"Embedding 失敗：{e}"}]
        
        # Step 3: Milvus 搜尋
        '''
        print("Step 3: Milvus 搜尋...")
        try:
            results = self.milvus_searcher.search(
                query_vector=vectors,
                limit=self.search_limit,
                output_fields=["*"]  # 返回所有欄位
            )
            
            print(f"找到 {len(results)} 筆結果")
            
            # 格式化結果
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted = {
                    "rank": i,
                    "score": result.get("score", 0),
                    "entity": result.get("entity", {})
                }
                formatted_results.append(formatted)
            
            return formatted_results
            
        except Exception as e:
            print(f"Milvus 搜尋失敗：{e}")
            return [{"error": f"Milvus 搜尋失敗：{e}"}]
        '''
        try:
            results = await self.qdrant_search(QDRANT_HOST, QDRANT_PORT, query_vector=vectors, limit=self.search_limit)
            print(f"找到 {len(results)} 筆結果")
            
            # 格式化結果
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted = {
                    "rank": i,
                    "score": result.get("score", 0),
                    "entity": result.get("entity", {})
                }
                formatted_results.append(formatted)
            
            return formatted_results
            
        except Exception as e:
            print(f"qdrant 搜尋失敗：{e}")
            return [{"error": f"qdrant 搜尋失敗：{e}"}]
    
    async def qdrant_search(self, host, port, query_vector: List[float],limit:int)-> List[Dict[str, Any]]:
        print(f"qdrant_search IN")       
        # Python 客戶端會自動處理連接池
        client = QdrantClient(host=host, port=port, prefer_grpc=True, check_compatibility=False)
        results = []
        try:
            search_result = client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=query_vector,
                limit=limit,
                with_payload=True
            ).points

            # 遍歷結果
            for result in search_result:
                # Python 的 payload 直接是字典格式，非常方便存取
                content = result.payload.get("content")
                print(f"qdrant_search {content=}")
                results.append({
                "score": result.score,
                "entity": result.payload  # 這裡包含 content 以及其他欄位
            })
                
        except Exception as e:
            print(f"發生錯誤: {e}")
        finally:
            # 關閉連線
            client.close()
        return results
    
    def close(self):
        """關閉資源"""
        self.milvus_searcher.close()

# 便捷函數
async def retrieve_phone_number(
    query: str,
    ubillm_model: str = "qwen3-8b-fp8",
    embedding_model: str = "qwen3-embedding-4b",
    milvus_uri: str = "http://localhost:19530",
    milvus_collection: str = "ext_number_0302",
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    便捷函數：搜尋電話號碼
    
    Args:
        query: 用戶查詢
        ubillm_model: LLM 模型
        embedding_model: Embedding 模型
        milvus_uri: Milvus 地址
        milvus_collection: Milvus 集合
        limit: 結果數量
    
    Returns:
        搜尋結果
    """
    agent = RetrievalAgent(
        ubillm_model=ubillm_model,
        embedding_model=embedding_model,
        milvus_uri=milvus_uri,
        milvus_collection=milvus_collection,
        search_limit=limit
    )
    
    try:
        # 方式 2: 分開呼叫 Step 1 + Step 2-3
        keywords = await agent.extract_keywords_from_query("我要找遠藤和也")
        search_results = await agent.search_by_keywords(keywords)
        return search_results
    finally:
        agent.close()

# --- 定義 Request 模型 ---
class Message(BaseModel):
    role: str = Field(..., description="角色: system, user, 或 assistant")
    content: str = Field(..., description="對話內容")

class InputParserRequest(BaseModel):
    input: str = Field(..., description="使用者輸入的查詢字串")


@app.post("/telsurvey/checkextension")
async def telsurvey_checkextension(request: InputParserRequest, raw_request: Request):
    print(f"--- 收到請求: {request.input} ---")
    try:
        retrieval_agent = RetrievalAgent()
        async def event_generator():
            print("進入 event_generator")
            try:
                search_keywords = [] # 用於搜尋的列表
                print("1.正在提取關鍵字...")
                async for step in retrieval_agent.extract_keywords_from_query_gen(request.input):
                    if await raw_request.is_disconnected(): return          
                    if step["status"] == "completed":
                        search_keywords = step["keywords"] # 取得 List
                        #display_text = "正在搜尋：" + ", ".join(search_keywords)
                        display_text = step["display"]
                        yield {
                            "event": "text_chunk", 
                            "data": json.dumps({"event": "text_chunk", "message":display_text}, ensure_ascii=False)
                        }
                if not search_keywords:
                    yield {"event": "error", 
                           "data": json.dumps({"event": "error", "error":"質問の内容が確認できません。もう一度具体的に入力してください"}, 
                            ensure_ascii=False)}
                    return
            
                print(f"2.提取成功: {search_keywords}，正在搜尋資料庫...")
                search_results = await retrieval_agent.search_by_keywords(search_keywords)
                
                print(f"搜尋完成，結果數量: {len(search_results)}")

                final_agent = FinalAgent()
        
                async for chunk in final_agent.generate_answer_stream(request.input, search_results):
                    if await raw_request.is_disconnected():
                        break
                    #print(f"Yielding chunk: {chunk}")
                    if "[DONE]" in chunk:
                        data_payload = json.dumps({"event": "done"}, ensure_ascii=False)
                        yield {"event": "done", "data": data_payload}
                    else: 
                        data_payload = json.dumps({"event": "text_chunk","message": chunk}, ensure_ascii=False)
                        yield {"event": "text_chunk", "data": data_payload}                
                print("串流結束。")
            except Exception as e:
                print(f"產生器內部報錯: {e}")
                data_payload = json.dumps({"event": "error","error":str(e)}, ensure_ascii=False)
                yield {"event": "error", "data": data_payload}

        return EventSourceResponse(event_generator())

    except Exception as e:
        print(f"外部初始化錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"} 
# 測試用
if __name__ == "__main__":
    #uvicorn.run(app, host="0.0.0.0", port=3005)
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=3005)

    parser.add_argument("--db_uri", type=str, default="http://127.0.0.1:19530")
    parser.add_argument("--ollama_uri", type=str, default="http://127.0.0.1:11434")
    #parser.add_argument("--ollama_model", type=str, default="gemma3:4b")
    parser.add_argument("--ollama_model", type=str, default="gemma2:2b")
    
    parser.add_argument("--max_neighbor_search", type=int, default=30)
    #parser.add_argument("--max_l2_distance", type=float, default=1.0) # make it larger than 1 to disable filter (for gemini)
    parser.add_argument("--max_l2_distance", type=float, default=10) # make it larger than 1 to disable filter (for qwen3)

    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
    
    '''
    async def test():
        print("=== Retrieval Agent 測試 ===\n")
        
        queries = [
            "我要找遠藤和也"
        ]
        
        for query in queries:
            print(f"\n{'='*50}")
            print(f"查詢：{query}")
            print('='*50)
            
            results = await retrieve_phone_number(query=query)
            
            print(f"\n結果：")
            for r in results:
                if 'error' not in r:
                    print(f'  ✓ Rank {r["rank"]}, Score: {r["score"]:.4f}')
                    print(r['entity'].get('text', ''))
    
    asyncio.run(test())
    '''
    '''
    async def test_stream():
        agent = StreamingRetrievalAgent()
        results = await agent.search_stream("我要找遠藤和也")
        print(f"結果：{results}")
        agent.close()
    '''
    '''
    # 帶回呼的串流
    async def test_stream_callback():
        agent = StreamingRetrievalAgent()
        
        async def on_token(content: str):
            print(content, end="", flush=True)
        
        async def on_thinking(content: str):
            print(f"\n[思考] {content}", end="", flush=True)
        
        async def on_done():
            print("\n✓ 完成")
        
        async def on_error(message: str):
            print(f"\n✗ 錯誤：{message}")
        
        results = await agent.search_stream_with_callback(
            user_query="我要找遠藤和也",
            token_callback=on_token,
            thinking_callback=on_thinking,
            done_callback=on_done,
            error_callback=on_error
        )
        
        #print(f"結果：{results}")
        
        # Step 2: Final Answer
        final_agent = FinalAgent()
        final_answer = await final_agent.generate_answer(
            user_question="我要找遠藤和也",
            search_results=results
        )
   
        print(final_answer)
        
        agent.close()
    asyncio.run(test_stream_callback())
    '''