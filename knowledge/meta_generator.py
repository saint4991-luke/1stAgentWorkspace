"""
Meta 生成器 - 自動為知識庫生成 meta.json

使用 LLM 讀取文件內容，生成摘要與關鍵字。
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class MetaGenerator:
    """知識庫 Meta 生成器"""
    
    def __init__(self, llm_client=None):
        """
        初始化 Meta 生成器
        
        Args:
            llm_client: LLM 客戶端（需支援 generate 方法）
        """
        self.llm = llm_client
    
    def generate(self, knowledge_path: str, force: bool = False) -> Dict[str, Any]:
        """
        為知識庫生成 meta.json
        
        Args:
            knowledge_path: 知識庫目錄路徑
            force: 是否強制重新生成（覆蓋現有 meta.json）
        
        Returns:
            meta 字典
        """
        knowledge_path = Path(knowledge_path)
        meta_path = knowledge_path / "meta.json"
        
        # 檢查是否已存在
        if meta_path.exists() and not force:
            print(f"⚠️  meta.json 已存在，使用 --force 重新生成")
            return json.load(open(meta_path, 'r', encoding='utf-8'))
        
        # 收集所有 .txt 文件
        txt_files = list(knowledge_path.glob("*.txt"))
        if not txt_files:
            raise ValueError(f"知識庫目錄中沒有 .txt 文件：{knowledge_path}")
        
        print(f"📁 找到 {len(txt_files)} 個文件")
        
        # 生成每個文件的 meta
        files_meta = []
        for txt_file in txt_files:
            print(f"  📄 處理：{txt_file.name}")
            file_meta = self._generate_file_meta(txt_file)
            files_meta.append(file_meta)
        
        # 組合 meta
        meta = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "knowledge_id": knowledge_path.name,
            "files": files_meta
        }
        
        # 寫入 meta.json
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已生成：{meta_path}")
        return meta
    
    def _generate_file_meta(self, file_path: Path) -> Dict[str, Any]:
        """
        為單一文件生成 meta
        
        Args:
            file_path: 文件路徑
        
        Returns:
            文件 meta 字典
        """
        # 讀取文件內容（前 3000 字）
        content = file_path.read_text(encoding='utf-8')
        content_preview = content[:3000]
        
        # 如果沒有 LLM，使用基本資訊
        if not self.llm:
            return {
                "name": file_path.name,
                "summary": f"文件：{file_path.name}（{len(content)} 字）",
                "keywords": [file_path.stem],
                "size_bytes": len(content.encode('utf-8')),
                "line_count": len(content.splitlines())
            }
        
        # 使用 LLM 生成摘要與關鍵字
        prompt = f"""
以下是文件內容：
{content_preview}

請生成：
1. 一句話摘要（50-100 字，說明這份文件的主要內容）
2. 5-10 個關鍵字（用來說明文件主題）

請用 JSON 格式回應：
{{
  "summary": "摘要內容",
  "keywords": ["關鍵字 1", "關鍵字 2", "..."]
}}
"""
        try:
            llm_response = self.llm.generate(prompt)
            # 解析 JSON（可能需要清理）
            llm_response = llm_response.strip()
            if llm_response.startswith('```json'):
                llm_response = llm_response[7:]
            if llm_response.endswith('```'):
                llm_response = llm_response[:-3]
            
            file_meta = json.loads(llm_response.strip())
            
            return {
                "name": file_path.name,
                "summary": file_meta.get("summary", f"文件：{file_path.name}"),
                "keywords": file_meta.get("keywords", [file_path.stem]),
                "size_bytes": len(content.encode('utf-8')),
                "line_count": len(content.splitlines())
            }
        except Exception as e:
            print(f"    ⚠️  LLM 生成失敗：{e}，使用基本資訊")
            return {
                "name": file_path.name,
                "summary": f"文件：{file_path.name}（{len(content)} 字）",
                "keywords": [file_path.stem],
                "size_bytes": len(content.encode('utf-8')),
                "line_count": len(content.splitlines())
            }
    
    def generate_all(self, base_path: str = "/knowledge", force: bool = False) -> Dict[str, Any]:
        """
        為所有知識庫生成 meta.json
        
        Args:
            base_path: 知識庫基礎路徑
            force: 是否強制重新生成
        
        Returns:
            所有知識庫的 meta 字典
        """
        base_path = Path(base_path)
        if not base_path.exists():
            raise ValueError(f"知識庫基礎路徑不存在：{base_path}")
        
        all_metas = {}
        for knowledge_dir in base_path.iterdir():
            if knowledge_dir.is_dir():
                print(f"\n📚 處理知識庫：{knowledge_dir.name}")
                try:
                    meta = self.generate(str(knowledge_dir), force)
                    all_metas[knowledge_dir.name] = meta
                except Exception as e:
                    print(f"  ❌ 失敗：{e}")
        
        return all_metas


# CLI 入口
if __name__ == "__main__":
    import sys
    import os
    
    if len(sys.argv) < 2:
        print("=" * 60)
        print("KNOWLEDGE Meta 生成器")
        print("=" * 60)
        print("\n用法：")
        print("  python3 -m agent.rag.meta_generator <knowledge_path> [--force]")
        print("  python3 -m agent.rag.meta_generator /knowledge --all [--force]")
        print("\n範例：")
        print("  # 重新生成單一知識庫")
        print("  python3 -m agent.rag.meta_generator /knowledge/ubitus")
        print("\n  # 強制重新生成（覆蓋現有）")
        print("  python3 -m agent.rag.meta_generator /knowledge/ubitus --force")
        print("\n  # 重新生成所有知識庫")
        print("  python3 -m agent.rag.meta_generator /knowledge --all")
        print("=" * 60)
        sys.exit(1)
    
    base_path = sys.argv[1]
    force = "--force" in sys.argv
    rebuild_all = "--all" in sys.argv
    
    # 初始化 LLM 客戶端
    llm_client = None
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY", "sk-no-key-required")
        base_url = os.getenv("OPENAI_BASE_URL", "http://116.50.47.234:8081/v1")
        model = os.getenv("OPENAI_MODEL", "Qwen/Qwen3.5-397B-A17B-FP8")
        
        llm_client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"✅ LLM 客戶端已初始化：{model}")
    except Exception as e:
        print(f"⚠️  LLM 客戶端初始化失敗：{e}，使用無 LLM 模式")
    
    # 創建適配器讓 OpenAI 客戶端支援 generate 方法
    class LLMAdapter:
        def __init__(self, client, model):
            self.client = client
            self.model = model
        
        def generate(self, prompt: str) -> str:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content
    
    if llm_client:
        llm_adapter = LLMAdapter(llm_client, model)
        generator = MetaGenerator(llm_client=llm_adapter)
        print("🚀 使用 LLM 生成摘要與關鍵字")
    else:
        generator = MetaGenerator(llm_client=None)
        print("⚠️  使用無 LLM 模式（基本資訊）")
    
    if rebuild_all:
        # 重新生成所有知識庫
        print(f"📚 重新生成所有知識庫：{base_path}")
        print("=" * 60)
        try:
            all_metas = generator.generate_all(base_path, force)
            print(f"\n✅ 完成：{len(all_metas)} 個知識庫")
        except Exception as e:
            print(f"❌ 失敗：{e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        # 重新生成單一知識庫
        print(f"📁 重新生成：{base_path}")
        try:
            generator.generate(base_path, force)
            print("\n✅ 完成")
        except Exception as e:
            print(f"❌ 失敗：{e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
