"""
Knowledge 檢索引擎 - 兩階段 Meta 檢索

階段 1: 讀取 meta.json，讓 LLM 判斷相關文件
階段 2: 載入相關文件完整內容，用於回答
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class KnowledgeRetriever:
    """知識庫檢索引擎"""
    
    def __init__(self, knowledge_id: str, base_path: str = "/knowledge", llm_client=None):
        """
        初始化檢索引擎
        
        Args:
            knowledge_id: 知識庫 ID（目錄名稱）
            base_path: 知識庫基礎路徑
            llm_client: LLMService 實例（需支援 chat_for_knowledge_sync 方法）
        """
        self.knowledge_id = knowledge_id
        self.knowledge_path = Path(base_path) / knowledge_id
        self.meta_path = self.knowledge_path / "meta.json"
        self.llm = llm_client
        
        # 載入 meta
        self.meta = self._load_meta()
    
    def _load_meta(self) -> Optional[Dict[str, Any]]:
        """載入 meta.json"""
        if not self.meta_path.exists():
            print(f"⚠️  meta.json 不存在：{self.meta_path}")
            return None
        
        try:
            with open(self.meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  讀取 meta.json 失敗：{e}")
            return None
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        查詢知識庫
        
        Args:
            question: 用戶問題
        
        Returns:
            {
                "content": "知識庫內容（相關文件合併）",
                "used_files": ["file1.txt", "file2.txt"],
                "meta_used": True/False
            }
        """
        # 階段 1: 判斷相關文件（含計時）
        result = self._find_related_files(question)
        
        # _find_related_files 返回完整 dict（包含 files, comforting_words, timings）
        if isinstance(result, dict):
            # LLM 失敗時的退化模式
            return {
                "content": "",
                "files": result.get("files", []),
                "comforting_words": result.get("comforting_words", ""),
                "used_files": result.get("files", []),
                "meta_used": False,
                "timings": result.get("timings", {})
            }
        
        related_files = result
        
        if not related_files:
            # 沒有相關文件
            return {
                "content": "",
                "files": [],
                "comforting_words": getattr(self, 'timings', {}).get('comforting_words', ''),
                "used_files": [],
                "meta_used": False,
                "message": "未找到相關文件",
                "timings": getattr(self, 'timings', {})
            }
        
        # 階段 2: 載入完整內容（計時）
        file_read_start = time.time()
        content, loaded_files = self._load_files(related_files)
        file_read_time = int((time.time() - file_read_start) * 1000)
        
        # 整合計時數據
        timings = getattr(self, 'timings', {})
        timings['file_read_ms'] = file_read_time
        
        return {
            "content": content,
            "files": loaded_files,
            "comforting_words": getattr(self, 'timings', {}).get('comforting_words', ''),
            "used_files": loaded_files,
            "meta_used": True,
            "timings": timings
        }
    
    def _find_related_files(self, question: str) -> List[str]:
        """
        階段 1: 找出相關文件
        
        Args:
            question: 用戶問題
        
        Returns:
            相關文件名稱列表
        """
        # 如果沒有 meta，返回所有文件
        if not self.meta or "files" not in self.meta:
            print("⚠️  無 meta 資訊，載入所有文件")
            return self._get_all_files()
        
        # 如果沒有 LLM，返回所有文件（退化模式）
        if not self.llm:
            print("⚠️  無 LLM 客戶端，載入所有文件")
            return self._get_all_files()
        
        # 構建 meta prompt
        files_info = []
        for file_meta in self.meta["files"]:
            files_info.append({
                "name": file_meta["name"],
                "summary": file_meta["summary"],
                "keywords": file_meta["keywords"]
            })
        
        # 優化 prompt：同時生成安撫話語和文件判斷（強調嚴格遵循格式）
        prompt = f"""你是一個知識庫檢索助手。請**嚴格按照以下格式**回應：

## 回應格式（必須遵守）
回應：[一句友善的回應，表達你理解用戶問題並準備查詢]
相關文件：["file1.txt", "file2.txt"]

## 文件清單與摘要
{json.dumps(files_info, ensure_ascii=False, indent=2)}

## 用戶問題
{question}

## 範例
用戶問題：「優必達有哪些產品？」
回應：
回應：我來幫你查查優必達的產品資訊！
相關文件：["products.txt"]

用戶問題：「優必達公司什麼時候成立的？」
回應：
回應：讓我查詢一下優必達的成立時間～
相關文件：["company.txt"]

**注意：**
- 第一行必須是「回應：」開頭
- 第二行必須是「相關文件：」開頭
- 不要添加其他內容
- 用繁體中文回應
- 相關文件只返回真正需要的文件
- 如果沒有相關文件，返回空列表：[]
"""
        
        # ⭐ 計時開始：LLM 判斷
        import time
        llm_start = time.time()
        
        try:
            llm_result = self.llm.chat_for_knowledge_sync(prompt)
            llm_time = int((time.time() - llm_start) * 1000)
            
            # ⭐ 儲存計時數據和 Token Usage
            self.timings = {
                'rag_llm_ms': llm_time,
            }
            
            # ⭐ 獲取 Token Usage
            if isinstance(llm_result, dict):
                # 新格式：返回 dict
                llm_response = llm_result.get('content', '[]')
                usage = llm_result.get('usage', None)
                if usage:
                    self.timings['rag_prompt_tokens'] = usage.get('prompt_tokens', 0)
                    self.timings['rag_completion_tokens'] = usage.get('completion_tokens', 0)
                    self.timings['rag_total_tokens'] = usage.get('total_tokens', 0)
                    if usage.get('estimated', False):
                        self.timings['rag_tokens_estimated'] = True
            else:
                # 舊格式：返回 str（向後兼容）
                llm_response = llm_result
            
            # 解析 LLM1 回應：分離安撫話語和相關文件
            if isinstance(llm_response, str):
                llm_response = llm_response.strip()
                
                # 🔍 方案 3：添加日誌診斷
                print(f"🔍 LLM1 原始回應：{repr(llm_response[:500]) if llm_response else '(空)'}")
                
                # 解析安撫話語和相關文件（使用新格式「回應：」）
                comforting_words = ""
                related_files = []
                
                for line in llm_response.split('\n'):
                    line = line.strip()
                    if line.startswith('回應：'):
                        comforting_words = line.replace('回應：', '').strip()
                    elif line.startswith('相關文件：'):
                        files_json = line.replace('相關文件：', '').strip()
                        # 移除 markdown 代碼塊標記
                        if files_json.startswith('```'):
                            files_json = files_json[3:]
                        if files_json.endswith('```'):
                            files_json = files_json[:-3]
                        try:
                            related_files = json.loads(files_json)
                        except:
                            print(f"⚠️  解析相關文件失敗：{files_json}")
                            related_files = []
                
                # 如果沒有解析出安撫話語，嘗試提取第一行
                if not comforting_words:
                    first_line = llm_response.split('\n')[0].strip() if llm_response else ''
                    if first_line and len(first_line) > 5:
                        comforting_words = first_line
                        print(f"⚠️  從第一行提取回應：{comforting_words}")
                    elif llm_response:
                        comforting_words = llm_response
                        print(f"⚠️  使用整個回應作為安撫話語")
                    else:
                        comforting_words = "我來幫你查詢相關資訊..."
                        print(f"⚠️  使用預設安撫話語（LLM 返回空內容）")
                
                # 儲存安撫話語到 timings
                self.timings['comforting_words'] = comforting_words
            
            # 驗證文件是否存在
            valid_files = []
            for filename in related_files:
                file_path = self.knowledge_path / filename
                if file_path.exists():
                    valid_files.append(filename)
                else:
                    print(f"⚠️  文件不存在：{filename}")
            
            print(f"📋 找到 {len(valid_files)} 個相關文件：{valid_files}")
            print(f"⏱️  RAG LLM 計時：{llm_time}ms")
            if 'comforting_words' in self.timings:
                print(f"💬 安撫話：{self.timings['comforting_words']}")
            if 'rag_prompt_tokens' in self.timings:
                estimated = " (估算)" if self.timings.get('rag_tokens_estimated', False) else ""
                print(f"📊 Token Usage{estimated}: prompt={self.timings['rag_prompt_tokens']}, completion={self.timings['rag_completion_tokens']}, total={self.timings.get('rag_total_tokens', 0)}")
            
            # 返回完整結果（包含安撫話語）
            return {
                "files": valid_files,
                "comforting_words": self.timings.get('comforting_words', "我來幫你查詢相關資訊..."),
                "timings": self.timings
            }
        
        except Exception as e:
            print(f"⚠️  LLM 判斷失敗：{e}，載入所有文件")
            # 記錄 LLM 失敗的計時
            llm_time = int((time.time() - llm_start) * 1000)
            self.timings = {'rag_llm_ms': llm_time}
            if hasattr(self, 'timings') and 'rag_prompt_tokens' in self.timings:
                print(f"📊 Token Usage: prompt={self.timings['rag_prompt_tokens']}, completion={self.timings['rag_completion_tokens']}")
            
            # 返回完整 dict（包含 comforting_words）
            all_files = self._get_all_files()
            return {
                "files": all_files,
                "comforting_words": "我來幫你查詢相關資訊...",
                "timings": self.timings
            }
    
    def _get_all_files(self) -> List[str]:
        """獲取所有 .txt 文件"""
        if not self.knowledge_path.exists():
            return []
        
        files = [f.name for f in self.knowledge_path.glob("*.txt")]
        return files
    
    def _load_files(self, filenames: List[str]) -> Tuple[str, List[str]]:
        """
        階段 2: 載入文件完整內容
        
        Args:
            filenames: 文件名稱列表
        
        Returns:
            (合併內容，成功載入的文件列表)
        """
        content_parts = []
        loaded_files = []
        
        for filename in filenames:
            file_path = self.knowledge_path / filename
            if not file_path.exists():
                print(f"⚠️  文件不存在：{filename}")
                continue
            
            try:
                file_content = file_path.read_text(encoding='utf-8')
                content_parts.append(f"=== {filename} ===\n{file_content}")
                loaded_files.append(filename)
                print(f"📄 載入：{filename} ({len(file_content)} 字)")
            except Exception as e:
                print(f"⚠️  讀取文件失敗 {filename}: {e}")
        
        return "\n\n".join(content_parts), loaded_files
    
    def get_status(self) -> Dict[str, Any]:
        """獲取知識庫狀態"""
        if not self.meta:
            return {
                "knowledge_id": self.knowledge_id,
                "status": "no_meta",
                "files": self._get_all_files()
            }
        
        return {
            "knowledge_id": self.knowledge_id,
            "status": "ready",
            "meta_version": self.meta.get("version", "unknown"),
            "generated_at": self.meta.get("generated_at", "unknown"),
            "file_count": len(self.meta.get("files", [])),
            "files": [f["name"] for f in self.meta.get("files", [])]
        }


# 多知識庫檢索
class MultiKnowledgeRetriever:
    """多知識庫檢索引擎"""
    
    def __init__(self, knowledge_ids: List[str], base_path: str = "/knowledge", llm_client=None):
        """
        初始化多知識庫檢索
        
        Args:
            knowledge_ids: 知識庫 ID 列表
            base_path: 知識庫基礎路徑
            llm_client: LLM 客戶端
        """
        self.knowledge_ids = knowledge_ids
        self.base_path = base_path
        self.retrievers = {
            kid: KnowledgeRetriever(kid, base_path, llm_client)
            for kid in knowledge_ids
        }
    
    def get_meta_content(self) -> Optional[str]:
        """
        獲取所有知識庫的 META 內容（用於 LLM1 輸入）
        
        Returns:
            str: META 內容（文件摘要和關鍵字）
            None: 如果沒有 META
        """
        meta_contents = []
        
        for kid, retriever in self.retrievers.items():
            if retriever.meta and "files" in retriever.meta:
                files_info = []
                for file_meta in retriever.meta["files"]:
                    files_info.append({
                        "name": file_meta["name"],
                        "summary": file_meta["summary"],
                        "keywords": file_meta["keywords"]
                    })
                
                meta_contents.append({
                    "knowledge_id": kid,
                    "files": files_info
                })
        
        if not meta_contents:
            return None
        
        # 格式化為 LLM1 輸入
        meta_text = "## 知識庫清單\n\n"
        for meta in meta_contents:
            meta_text += f"### 知識庫：{meta['knowledge_id']}\n"
            for file_info in meta['files']:
                meta_text += f"- **{file_info['name']}**: {file_info['summary']}\n"
                meta_text += f"  關鍵字：{', '.join(file_info['keywords'])}\n"
            meta_text += "\n"
        
        return meta_text
    
    def load_files_content(self, filenames: List[str]) -> str:
        """
        載入文件完整內容
        
        Args:
            filenames: 文件名稱列表
        
        Returns:
            str: 所有文件內容合併
        """
        contents = []
        
        for filename in filenames:
            # 嘗試從所有知識庫中找到文件
            for kid, retriever in self.retrievers.items():
                file_path = retriever.knowledge_path / filename
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            contents.append(f.read())
                        break
                    except Exception as e:
                        print(f"⚠️  讀取文件失敗 {filename}: {e}")
        
        return "\n\n---\n\n".join(contents)
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        查詢多個知識庫
        
        Args:
            question: 用戶問題
        
        Returns:
            {
                "content": "所有知識庫內容合併",
                "files": ["file1.txt", "file2.txt"],
                "comforting_words": "安撫話語",
                "timings": {"rag_llm_ms": 450, "file_read_ms": 120, ...}
            }
        """
        all_content = []
        all_files = []
        all_timings = {}
        comforting_words = None
        
        for kid, retriever in self.retrievers.items():
            result = retriever.query(question)
            
            # 獲取安撫話語（只取第一個）
            if comforting_words is None and result.get("comforting_words"):
                comforting_words = result["comforting_words"]
            
            # 獲取文件列表
            files = result.get("files", [])
            if files:
                all_files.extend(files)
                # 載入文件內容
                content, loaded = retriever._load_files(files)
                if content:
                    all_content.append(f"=== 知識庫：{kid} ===\n{content}")
            
            # 整合 timings
            if result.get("timings"):
                if not all_timings:
                    all_timings = result["timings"].copy()
                else:
                    for key, value in result["timings"].items():
                        if isinstance(value, (int, float)):
                            all_timings[key] = all_timings.get(key, 0) + value
        
        return {
            "content": "\n\n".join(all_content),
            "files": all_files,
            "comforting_words": comforting_words,  # 可能為 None，讓上層處理
            "timings": all_timings
        }
    
    def get_status(self) -> Dict[str, Any]:
        """獲取所有知識庫狀態"""
        return {
            kid: retriever.get_status()
            for kid, retriever in self.retrievers.items()
        }
