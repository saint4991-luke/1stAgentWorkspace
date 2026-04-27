#!/usr/bin/env python3
"""
🦐 蝦米 Agent Web UI v3.1 - 支援 Session 管理

這是一個純前端 + 簡單代理的 Web UI，用於測試和實驗。
所有 Agent 邏輯都委託給 agent-api 服務。

端點：
- GET / - Web UI 介面（支援 Session 列表）
- POST /api/chat - 代理到 Agent API
- GET /api/health - 代理健康檢查
- GET /api/sessions/* - Session 管理
- GET /files/* - 檔案管理（本地處理）
"""

from flask import Flask, request, jsonify, send_file, render_template, Response
from flask_cors import CORS
import os
import json
import requests
from pathlib import Path

app = Flask(__name__, 
    template_folder='/app/frontend/templates',
    static_folder='/app/frontend/static'
)
CORS(app)

# Agent API 地址（Docker 網路內）
AGENT_API_URL = os.getenv("AGENT_API_URL", "http://agent:8000")
WORK_DIR = '/workspace'


# ============= HTML 模板 =============

# ============= Web UI 端點 =============
@app.route('/')
def index():
    """首頁：Web UI"""
    return render_template('index.html')

@app.route('/chat')
def chat_page():
    """一般對話頁面"""
    return render_template('chat.html')

@app.route('/vh/chat')
def vh_chat_page():
    """虛擬人對話頁面"""
    return render_template('vh-chat.html')


# ============= Agent API 代理端點 =============
@app.route('/api/chat', methods=['POST'])
def api_chat():
    """代理到 Agent API（一般對話）- 僅支援 STREAM 模式"""
    try:
        data = request.json
        # 移除 stream 參數（後端固定使用 STREAM）
        data.pop('stream', None)
        
        # 一般對話：使用 /chat（後端固定返回 STREAM）
        response = requests.post(
            f"{AGENT_API_URL}/chat",
            json=data,
            timeout=120,
            stream=True  # ⭐ 啟用 stream 以支持 SSE
        )
        
        # 代理 STREAM 回應
        return Response(
            response.iter_content(chunk_size=1024),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Agent API 不可用：{str(e)}'}), 503


@app.route('/api/vh/chat', methods=['POST'])
def api_vh_chat():
    """代理到 Agent API（虛擬人對話）- 僅支援 STREAM 模式"""
    try:
        data = request.json
        # 移除 stream 參數（後端固定使用 STREAM）
        data.pop('stream', None)
        
        # 虛擬人對話：使用 /vh/chat（後端固定返回 STREAM）
        response = requests.post(
            f"{AGENT_API_URL}/vh/chat",
            json=data,
            timeout=120,
            stream=True  # ⭐ 啟用 stream 以支持 SSE
        )
        
        # 代理 STREAM 回應
        return Response(
            response.iter_content(chunk_size=1024),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Agent API 不可用：{str(e)}'}), 503


@app.route('/api/health')
def api_health():
    """代理健康檢查"""
    try:
        response = requests.get(f"{AGENT_API_URL}/health", timeout=5)
        return jsonify(response.json())
    except:
        # 返回 unhealthy 狀態但不返回 503（不阻斷前端）
        return jsonify({
            'status': 'unhealthy',
            'message': 'Agent API 暫時不可用',
            'version': '3.1.0'
        }), 200


# ============= Session 管理代理端點 =============
@app.route('/api/sessions', methods=['GET', 'POST'])
def api_sessions():
    """代理 Session 列表/創建（調用 Session API）"""
    try:
        if request.method == 'GET':
            # 從 Session API 獲取列表
            response = requests.get(f"{AGENT_API_URL}/sessions", timeout=10)
            return jsonify(response.json())
        else:  # POST
            data = request.json
            # 調用 Session API 創建
            response = requests.post(
                f"{AGENT_API_URL}/sessions",
                json=data,
                timeout=10
            )
            return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        # GET 請求失敗時返回空陣列（不阻斷前端）
        if request.method == 'GET':
            print(f"[WARN] /api/sessions 失敗：{e}")
            return jsonify([])
        # POST 請求失敗時返回錯誤
        return jsonify({'error': f'Session API 不可用：{str(e)}'}), 503


@app.route('/api/sessions/<session_id>', methods=['GET', 'PUT', 'DELETE'])
def api_session(session_id):
    """代理 Session 詳情/更新/刪除"""
    try:
        if request.method == 'GET':
            response = requests.get(f"{AGENT_API_URL}/vh/sessions/{session_id}/stats", timeout=10)
            return jsonify(response.json())
        elif request.method == 'PUT':
            # 虛擬人 API 不支持更新 Session 名稱，暫時兼容處理
            data = request.json
            return jsonify({'success': True, 'message': 'Session 更新暫不支持'})
        else:  # DELETE
            # 虛擬人 API 不支持刪除 Session，暫時兼容處理
            return jsonify({'success': True, 'message': 'Session 刪除暫不支持'})
    except requests.exceptions.RequestException as e:
        # GET 請求失敗時返回空物件（不阻斷前端）
        if request.method == 'GET':
            print(f"[WARN] /api/sessions/{session_id} 失敗：{e}")
            return jsonify({})
        # PUT/DELETE 失敗時返回錯誤
        return jsonify({'error': f'Session API 不可用：{str(e)}'}), 503


@app.route('/api/sessions/<session_id>/messages', methods=['GET'])
def api_session_messages(session_id):
    """代理 Session 訊息歷史"""
    try:
        # 虛擬人 API 沒有 messages 端點，返回空陣列
        # 前端會顯示空對話狀態
        return jsonify([])
    except requests.exceptions.RequestException as e:
        # 返回空陣列（不阻斷前端）
        print(f"[WARN] /api/sessions/{session_id}/messages 失敗：{e}")
        return jsonify([])


@app.route('/api/sessions/<session_id>/export', methods=['GET'])
def api_session_export(session_id):
    """代理 Session 導出"""
    try:
        format = request.args.get('format', 'json')
        response = requests.get(
            f"{AGENT_API_URL}/sessions/{session_id}/export?format={format}",
            timeout=10
        )
        
        from flask import Response
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json'),
            headers={
                'Content-Disposition': response.headers.get('Content-Disposition', '')
            }
        )
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Session API 不可用：{str(e)}'}), 503


# ============= 檔案管理端點（本地處理） =============
@app.route('/files')
def list_files():
    """列出檔案"""
    try:
        path = request.args.get('path', '/')
        
        # 路徑處理：確保正確拼接
        if path == '/':
            full_path = WORK_DIR
        else:
            full_path = os.path.join(WORK_DIR, path.lstrip('/'))
        
        # 安全檢查：防止目錄遍歷攻擊
        real_path = os.path.realpath(full_path)
        real_work_dir = os.path.realpath(WORK_DIR)
        if not real_path.startswith(real_work_dir):
            return jsonify({'error': '無權限訪問：路徑超出工作區範圍'}), 403
        
        if not os.path.exists(full_path):
            return jsonify({'error': f'路徑不存在：{full_path}'}), 404
        
        if not os.path.isdir(full_path):
            return jsonify({'error': '不是目錄'}), 400
        
        files = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            if path == '/':
                rel_path = '/' + item
            else:
                rel_path = path.rstrip('/') + '/' + item
            
            rel_path = rel_path.replace('\\\\', '/')
            
            stat = os.stat(item_path)
            
            files.append({
                'name': item,
                'path': rel_path,
                'type': 'folder' if os.path.isdir(item_path) else 'file',
                'size': stat.st_size if os.path.isfile(item_path) else None
            })
        
        return jsonify(files)
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[FILES] 錯誤：{error_detail}")
        return jsonify({'error': str(e), 'detail': error_detail}), 500


@app.route('/files/preview')
def preview_file():
    """預覽檔案"""
    try:
        path = request.args.get('path', '')
        
        if path == '/':
            return jsonify({'error': '無法預覽目錄'}), 400
        
        full_path = os.path.join(WORK_DIR, path.lstrip('/'))
        
        real_path = os.path.realpath(full_path)
        real_work_dir = os.path.realpath(WORK_DIR)
        if not real_path.startswith(real_work_dir):
            return jsonify({'error': '無權限訪問'}), 403
        
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            return jsonify({'error': '檔案不存在'}), 404
        
        if os.path.getsize(full_path) > 1024 * 1024:
            return jsonify({'error': '檔案過大（最大 1MB）'}), 400
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(50000)
            return jsonify({'content': content})
        except UnicodeDecodeError:
            return jsonify({'error': '無法讀取二進位檔案'}), 400
            
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[PREVIEW] 錯誤：{error_detail}")
        return jsonify({'error': str(e)}), 500


@app.route('/files/download')
def download_file():
    """下載檔案"""
    try:
        path = request.args.get('path', '')
        
        if path == '/':
            return jsonify({'error': '無法下載目錄'}), 400
        
        full_path = os.path.join(WORK_DIR, path.lstrip('/'))
        
        real_path = os.path.realpath(full_path)
        real_work_dir = os.path.realpath(WORK_DIR)
        if not real_path.startswith(real_work_dir):
            return jsonify({'error': '無權限訪問'}), 403
        
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            return jsonify({'error': '檔案不存在'}), 404
        
        return send_file(full_path, as_attachment=True)
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[DOWNLOAD] 錯誤：{error_detail}")
        return jsonify({'error': str(e)}), 500


@app.route('/files/delete', methods=['DELETE'])
def delete_file_route():
    """刪除檔案"""
    try:
        path = request.args.get('path', '')
        
        if path == '/':
            return jsonify({'error': '無法刪除根目錄'}), 400
        
        full_path = os.path.join(WORK_DIR, path.lstrip('/'))
        
        real_path = os.path.realpath(full_path)
        real_work_dir = os.path.realpath(WORK_DIR)
        if not real_path.startswith(real_work_dir):
            return jsonify({'error': '無權限訪問'}), 403
        
        if not os.path.exists(full_path):
            return jsonify({'error': '檔案不存在'}), 404
        
        if os.path.isdir(full_path):
            os.rmdir(full_path)
            print(f"[DELETE] 刪除目錄：{full_path}")
        else:
            os.remove(full_path)
            print(f"[DELETE] 刪除檔案：{full_path}")
        
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[DELETE] 錯誤：{error_detail}")
        return jsonify({'error': str(e)}), 500


@app.route('/files/upload', methods=['POST'])
def upload_file():
    """上傳檔案"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '沒有檔案'}), 400
        
        file = request.files.get('file')
        if not file or file.filename == '':
            return jsonify({'error': '未選擇檔案'}), 400
        
        path = request.form.get('path', '/')
        
        if path == '/':
            upload_dir = WORK_DIR
        else:
            upload_dir = os.path.join(WORK_DIR, path.lstrip('/'))
        
        os.makedirs(upload_dir, exist_ok=True)
        
        save_path = os.path.join(upload_dir, file.filename)
        
        real_path = os.path.realpath(save_path)
        real_work_dir = os.path.realpath(WORK_DIR)
        if not real_path.startswith(real_work_dir):
            return jsonify({'error': '無權限上傳'}), 403
        
        file.save(save_path)
        print(f"[UPLOAD] 成功：{save_path}")
        return jsonify({'success': True, 'filename': file.filename})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[UPLOAD] 錯誤：{error_detail}")
        return jsonify({'error': str(e)}), 500


# ============= 主程式 =============
if __name__ == '__main__':
    print("🦐 蝦米 Agent Web UI v3.1 啟動中...")
    print(f"🔗 Agent API: {AGENT_API_URL}")
    print(f"📍 訪問地址：http://localhost:5000")
    print(f"📦 Session 功能：已啟用")
    app.run(host='0.0.0.0', port=5000, debug=False)
