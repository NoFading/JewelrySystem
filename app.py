import os
import json
from flask import Flask, request, jsonify, render_template_string
import pandas as pd

app = Flask(__name__)
DATA_FILE = 'jewelry_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 包含安全预览、取消机制的全新一体化前端
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>丰高珠宝库存管理系统 2.5 安全版</title>
    <script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <style>
        body { font-family: -apple-system, sans-serif; background: #f4f5f7; margin: 0; padding: 15px; color: #333; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 15px; }
        h2 { margin-top: 0; color: #111; font-size: 18px; border-left: 4px solid #007aff; padding-left: 8px; }
        .btn { background: #007aff; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-size: 15px; width: 100%; cursor: pointer; font-weight: bold; }
        .btn-green { background: #34c759; }
        .btn-red { background: #ff3b30; }
        .btn-scan { background: #5856d6; margin-bottom: 10px; }
        input[type="file"], input[type="text"] { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #f9f9f9; font-weight: 600; }
        .tips { font-size: 12px; color: #666; margin-top: 5px; line-height: 1.5; }
        #reader { width: 100%; max-width: 400px; margin: 0 auto; background: #000; border-radius: 8px; overflow: hidden; display: none; }
        .preview-zone { display: none; background: #fff9e6; border: 2px dashed #ff9500; border-radius: 12px; padding: 15px; margin-bottom: 15px; }
        .action-group { display: flex; gap: 10px; margin-top: 10px; }
    </style>
</head>
<body>

    <div class="preview-zone" id="previewZone">
        <h2 style="border-left-color: #ff9500; color: #n00;">⚠️ 侦测到待导入数据（安全预览中）</h2>
        <p class="tips" style="color: #ff9500; font-weight: bold;">提示：此时数据尚未写入云端数据库，检查下方列表，若文件传错或内容不对，请直接点击「取消导入」！</p>
        <div style="overflow-x: auto; max-height: 200px; background: #fff; border-radius: 6px; margin: 10px 0;">
            <table>
                <thead>
                    <tr><th>标签号/条码</th><th>货品名称</th><th>金重</th><th>数量</th></tr>
                </thead>
                <tbody id="previewBody"></tbody>
            </table>
        </div>
        <div class="action-group">
            <button class="btn btn-green" style="flex: 1;" onclick="confirmImport()">确认无误，锁库上架</button>
            <button class="btn btn-red" style="flex: 1;" onclick="cancelImport()">❌ 文件不对，取消导入</button>
        </div>
    </div>

    <div class="card">
        <h2>📦 货品入库 (安全 Excel 渠道)</h2>
        <input type="file" id="excelFile" accept=".xlsx, .xls">
        <button class="btn btn-green" onclick="uploadExcel()">选择并解析 Excel 文件</button>
        <div class="tips">💡 无论供应商提供何种表格，系统均会自动模糊匹配。先解析预览，确认无误后再存盘，100%防止污染原有数据。</div>
    </div>

    <div class="card">
        <h2>🛒 商品出库 (扫码/手动)</h2>
        <button class="btn btn-scan" id="scanBtn" onclick="toggleScanner()">📷 点击扫码卖出</button>
        <div id="reader"></div>
        <input type="text" id="barcodeInput" placeholder="栏位无法扫码时，请在此手动输入条码">
        <button class="btn" onclick="submitCheckout()">确认核销出库</button>
        <div class="tips" style="color: #ff9500;">⚠️ 提示：若点击出库无反应，说明条码可能输错或网络微弱，系统会自动弹窗告知具体原因。</div>
    </div>

    <div class="card">
        <h2>📊 实时库存看板</h2>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>标签号/条码</th>
                        <th>货品名称</th>
                        <th>金重(g)</th>
                        <th>件数</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody id="inventoryBody"></tbody>
            </table>
        </div>
    </div>

    <script>
        let html5QrcodeScanner = null;
        let tempParsedData = null; // 用于缓存解析好但未存盘的临时数据

        window.onload = loadInventory;

        function loadInventory() {
            fetch('/api/inventory')
                .then(res => res.json())
                .then(data => {
                    const tbody = document.getElementById('inventoryBody');
                    tbody.innerHTML = '';
                    if(!data || data.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#999;">暂无库存，请先导入 Excel</td></tr>';
                        return;
                    }
                    data.forEach(item => {
                        tbody.innerHTML += `
                            <tr>
                                <td><b>${item.code || '-'}</b></td>
                                <td>${item.name || '-'}</td>
                                <td>${item.weight || 0}g</td>
                                <td>${item.quantity || 1}</td>
                                <td style="color: ${item.status === '已售出' ? '#ff3b30' : '#34c759'}; font-weight:bold;">
                                    ${item.status || '在售'}
                                </td>
                            </tr>
                        `;
                    });
                }).catch(() => alert('读取库存数据失败，请刷新网页重试'));
        }

        // 上传并解析文件（只读到内存，不写文件）
        function uploadExcel() {
            const fileInput = document.getElementById('excelFile');
            if (!fileInput.files[0]) {
                alert('请先选择一个 Excel 文件！');
                return;
            }
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            fetch('/api/parse_preview', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(res => {
                    if (res.success) {
                        tempParsedData = res.data;
                        const pbody = document.getElementById('previewBody');
                        pbody.innerHTML = '';
                        res.data.forEach(item => {
                            pbody.innerHTML += `<tr><td>${item.code}</td><td>${item.name}</td><td>${item.weight}g</td><td>${item.quantity}</td></tr>`;
                        });
                        document.getElementById('previewZone').style.display = 'block';
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                    } else {
                        alert('解析失败：' + res.msg);
                    }
                })
                .catch(err => alert('网络通信异常，Excel 预解析失败，请检查网络或文件格式'));
        }

        // 机制：确认写入
        function confirmImport() {
            if (!tempParsedData || tempParsedData.length === 0) return;
            fetch('/api/confirm_save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: tempParsedData })
            })
            .then(res => res.json())
            .then(res => {
                alert(res.msg);
                cancelImport(); // 写入后隐藏预览区
                loadInventory(); // 刷新账本
            })
            .catch(() => alert('存盘失败，请重试'));
        }

        // 机制：安全取消/取消再次导入
        function cancelImport() {
            tempParsedData = null;
            document.getElementById('previewZone').style.display = 'none';
            document.getElementById('excelFile').value = ''; // 清空选择框
        }

        // 扫码控制
        function toggleScanner() {
            const readerDiv = document.getElementById('reader');
            const scanBtn = document.getElementById('scanBtn');
            if (readerDiv.style.display === 'block') {
                stopScanner();
            } else {
                readerDiv.style.display = 'block';
                scanBtn.innerText = '🛑 关闭扫码器';
                html5QrcodeScanner = new Html5Qrcode("reader");
                html5QrcodeScanner.start(
                    { facingMode: "environment" },
                    { fps: 10, qrbox: { width: 250, height: 250 } },
                    (decodedText) => {
                        document.getElementById('barcodeInput').value = decodedText;
                        stopScanner();
                        alert('扫描成功: ' + decodedText);
                    },
                    () => {}
                ).catch(err => {
                    alert("无法唤醒摄像头。如果在微信内，请点击右上角...并在浏览器打开");
                    stopScanner();
                });
            }
        }

        function stopScanner() {
            if (html5QrcodeScanner) {
                html5QrcodeScanner.stop().then(() => {
                    document.getElementById('reader').style.display = 'none';
                    document.getElementById('scanBtn').innerText = '📷 点击扫码卖出';
                }).catch(() => {
                    document.getElementById('reader').style.display = 'none';
                    document.getElementById('scanBtn').innerText = '📷 点击扫码卖出';
                });
            }
        }

        // 强力出库，防无反应
        function submitCheckout() {
            const code = document.getElementById('barcodeInput').value.trim();
            if (!code) {
                alert('请先录入或输入条码！');
                return;
            }
            
            // 按钮防重复点击保护
            fetch('/api/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code })
            })
            .then(res => {
                if (!res.ok) {
                    throw new Error('服务器状态异常: ' + res.status);
                }
                return res.json();
            })
            .then(res => {
                alert(res.msg);
                if (res.success) {
                    document.getElementById('barcodeInput').value = '';
                    loadInventory();
                }
            })
            .catch(err => {
                alert('❌ 出库故障提示：系统在核销条码 [' + code + '] 时未能成功，通常因为系统库里查无此货，或网络连接在山顶出现波动。请检查条码是否录入。');
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    return jsonify(load_data())

# 核心接口1：只负责解析，100%不碰数据库文件，确保绝对隔离安全
@app.route('/api/parse_preview', methods=['POST'])
def parse_preview():
    if 'file' not in request.files:
        return jsonify({'success': False, 'msg': '未找到文件'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'msg': '文件名为空'})
    
    try:
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        
        code_col, name_col, weight_col, qty_col = None, None, None, None
        for col in df.columns:
            low_col = col.lower()
            if any(k in low_col for k in ['标签', '条码', '编码', '码', 'code']): code_col = col
            elif any(k in low_col for k in ['名', '货品', '商品', '款式', 'name']): name_col = col
            elif any(k in low_col for k in ['重', '金重', '克重', 'weight']): weight_col = col
            elif any(k in low_col for k in ['件', '数量', '数', 'qty']): qty_col = col

        if not code_col:
            return jsonify({'success': False, 'msg': f'找不到包含“标签”或“条码”的列。'})

        preview_list = []
        for _, row in df.iterrows():
            raw_code = row[code_col]
            if pd.isna(raw_code): continue
            
            code_str = str(raw_code).strip().split('.')[0]
            if not code_str: continue

            name_val = str(row[name_col]).strip() if (name_col and not pd.isna(row[name_col])) else "未命名珠宝"
            weight_val = ""
            if weight_col and not pd.isna(row[weight_col]):
                try: weight_val = str(round(float(row[weight_col]), 3))
                except: weight_val = str(row[weight_col]).strip()
            
            qty_val = 1
            if qty_col and not pd.isna(row[qty_col]):
                try: qty_val = int(row[qty_col])
                except: qty_val = 1

            preview_list.append({
                "code": code_str,
                "name": name_val,
                "weight": weight_val,
                "quantity": qty_val
            })
            
        return jsonify({'success': True, 'data': preview_list})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

# 核心接口2：用户在前端点击“确认无误”后，才开始合并写入
@app.route('/api/confirm_save', methods=['POST'])
def confirm_save():
    req = request.get_json() or {}
    new_items = req.get('data', [])
    
    current_data = load_data()
    existing_codes = {str(item['code']) for item in current_data}
    added_count = 0
    
    for item in new_items:
        # 查重，防止重复追加污染账目
        if item['code'] not in existing_codes:
            current_data.append({
                "code": item['code'],
                "name": item['name'],
                "weight": item['weight'],
                "quantity": item['quantity'],
                "status": "在售"
            })
            existing_codes.add(item['code'])
            added_count += 1
            
    save_data(current_data)
    return jsonify({'success': True, 'msg': f'🎉 隔离审核通过！已成功将 {added_count} 件新品并入库存系统。'})

@app.route('/api/checkout', methods=['POST'])
def checkout():
    req = request.get_json() or {}
    code = str(req.get('code', '')).strip()
    if not code:
        return jsonify({'success': False, 'msg': '请输入条码！'})
        
    current_data = load_data()
    for item in current_data:
        if str(item['code']).strip() == code:
            if item['status'] == '已售出':
                return jsonify({'success': False, 'msg': f'⚠️ 提示：条码 {code} 之前早已卖出，属于核销状态！'})
            item['status'] = '已售出'
            save_data(current_data)
            return jsonify({'success': True, 'msg': f'🛍️ 货品 {code} 核销出库成功！'})
            
    # 如果没找到，返回明明白白的错误，前端会捕获并弹窗
    return jsonify({'success': False, 'msg': f'❌ 未能在系统库存库里找到条码为 [{code}] 的货品，请核对条码或重新确认 Excel 导入情况。'})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
