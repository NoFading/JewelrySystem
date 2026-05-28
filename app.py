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

# 纯前端一体化 HTML 界面
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>丰高珠宝库存管理系统</title>
    <script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <style>
        body { font-family: -apple-system, sans-serif; background: #f4f5f7; margin: 0; padding: 15px; color: #333; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 15px; }
        h2 { margin-top: 0; color: #111; font-size: 18px; border-left: 4px solid #007aff; padding-left: 8px; }
        .btn { background: #007aff; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-size: 15px; width: 100%; cursor: pointer; font-weight: bold; }
        .btn-green { background: #34c759; }
        .btn-scan { background: #5856d6; margin-bottom: 10px; }
        input[type="file"], input[type="text"] { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #f9f9f9; font-weight: 600; }
        .tips { font-size: 12px; color: #666; margin-top: 5px; line-height: 1.5; }
        #reader { width: 100%; max-width: 400px; margin: 0 auto; background: #000; border-radius: 8px; overflow: hidden; display: none; }
    </style>
</head>
<body>

    <div class="card">
        <h2>📦 货品入库 (Excel 导入)</h2>
        <input type="file" id="excelFile" accept=".xlsx, .xls">
        <button class="btn btn-green" onclick="uploadExcel()">选择并导入 Excel 文件</button>
        <div class="tips">💡 支持任意供应商表格，系统会自动智能识别「标签/条码、名称、重、件数」等核心列。如果某些行数据不全（如为空），系统会自动跳过或允许空值，确保顺利导入。</div>
    </div>

    <div class="card">
        <h2>🛒 商品出库 (扫码/手动)</h2>
        <button class="btn btn-scan" id="scanBtn" onclick="toggleScanner()">📷 点击扫码卖出</button>
        <div id="reader"></div>
        <input type="text" id="barcodeInput" placeholder="栏位无法扫码时，请在此手动输入条码">
        <button class="btn" onclick="submitCheckout()">确认核销出库</button>
        <div class="tips" style="color: #ff9500;">⚠️ 提示：若点击扫码无反应，请点击微信右上角「...」选择「在浏览器中打开」即可完美解锁摄像头！</div>
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
                <tbody id="inventoryBody">
                    </tbody>
            </table>
        </div>
    </div>

    <script>
        let html5QrcodeScanner = null;

        // 页面加载自动刷新库存
        window.onload = loadInventory;

        function loadInventory() {
            fetch('/api/inventory')
                .then(res => res.json())
                .then(data => {
                    const tbody = document.getElementById('inventoryBody');
                    tbody.innerHTML = '';
                    if(data.length === 0) {
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
                });
        }

        // 智能 Excel 上传
        function uploadExcel() {
            const fileInput = document.getElementById('excelFile');
            if (!fileInput.files[0]) {
                alert('请先选择一个 Excel 文件！');
                return;
            }
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            fetch('/api/import', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(res => {
                    alert(res.msg);
                    if (res.success) {
                        loadInventory();
                    }
                })
                .catch(() => alert('网络异常，Excel 解析失败，请检查文件格式'));
        }

        // 扫码控制开关
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
                        alert('成功扫码识别条码: ' + decodedText + ' ！请点击下方确认出库。');
                    },
                    () => {} // 忽略暂未扫到时的静默
                ).catch(err => {
                    alert("摄像头开启失败。若在微信内，请点击右上角...选择在浏览器中打开！");
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

        // 核销出库
        function submitCheckout() {
            const code = document.getElementById('barcodeInput').value.trim();
            if (!code) {
                alert('请输入或扫码录入条码！');
                return;
            }
            fetch('/api/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: json.stringify({ code: code })
            })
            .then(res => res.json())
            .then(res => {
                alert(res.msg);
                if (res.success) {
                    document.getElementById('barcodeInput').value = '';
                    loadInventory();
                }
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

@app.route('/api/import', methods=['POST'])
def import_excel():
    if 'file' not in request.files:
        return jsonify({'success': False, 'msg': '未找到上传文件'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'msg': '未选择任何文件'})
    
    try:
        # 读取 Excel 文件
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns] # 清洗列名空格
        
        # 智能模糊匹配列名映射逻辑（与 HTML 预期完全一致）
        code_col, name_col, weight_col, qty_col = None, None, None, None
        
        for col in df.columns:
            low_col = col.lower()
            if any(k in low_col for k in ['标签', '条码', '编码', '码', 'code', 'id']):
                code_col = col
            elif any(k in low_col for k in ['名', '货品', '商品', '款式', 'name']):
                name_col = col
            elif any(k in low_col for k in ['重', '金重', '克重', '重量', 'weight']):
                weight_col = col
            elif any(k in low_col for k in ['件', '数量', '数', 'quantity', 'qty']):
                qty_col = col

        if not code_col:
            return jsonify({'success': False, 'msg': f'导入失败：Excel 中找不到包含“标签”或“条码”的列名。当前列名有: {list(df.columns)}'})

        current_data = load_data()
        existing_codes = {str(item['code']) for item in current_data}
        new_count = 0

        # 逐行处理数据，允许部分空值，确保高鲁棒性
        for _, row in df.iterrows():
            raw_code = row[code_col]
            if pd.isna(raw_code):
                continue # 条码为空的行直接跳过
                
            code_str = str(raw_code).strip().split('.')[0] # 防止条码变成浮点数带.0
            if not code_str or code_str in existing_codes:
                continue # 跳过空条码或重复记录

            # 提取其他字段，若为空则赋予安全的默认值
            name_val = str(row[name_col]).strip() if (name_col and not pd.isna(row[name_col])) else "未命名珠宝"
            weight_val = ""
            if weight_col and not pd.isna(row[weight_col]):
                try:
                    weight_val = str(round(float(row[weight_col]), 3))
                except:
                    weight_val = str(row[weight_col]).strip()
            
            qty_val = 1
            if qty_col and not pd.isna(row[qty_col]):
                try:
                    qty_val = int(row[qty_col])
                except:
                    qty_val = 1

            current_data.append({
                "code": code_str,
                "name": name_val,
                "weight": weight_val,
                "quantity": qty_val,
                "status": "在售"
            })
            existing_codes.add(code_str)
            new_count += 1

        save_data(current_data)
        return jsonify({'success': True, 'msg': f'🎉 成功智能导入 {new_count} 件全新货品！'})

    except Exception as e:
        return jsonify({'success': False, 'msg': f'Excel 解析失败，错误原因: {str(e)}'})

@app.route('/api/checkout', methods=['POST'])
def checkout():
    req = request.get_json() or {}
    code = str(req.get('code', '')).strip()
    if not code:
        return jsonify({'success': False, 'msg': '无效的条码'})
        
    current_data = load_data()
    found = False
    for item in current_data:
        if str(item['code']).strip() == code:
            if item['status'] == '已售出':
                return jsonify({'success': False, 'msg': f'提示：条码 {code} 之前已经核销过，属于已售状态！'})
            item['status'] = '已售出'
            found = True
            break
            
    if found:
        save_data(current_data)
        return jsonify({'success': True, 'msg': f'🛍️ 珠宝 {code} 核销成功！状态已变更为已售出。'})
    else:
        return jsonify({'success': False, 'msg': f'❌ 核销失败：在系统库中未找到条码为 {code} 的货品，请确认是否已导入该 Excel。'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
