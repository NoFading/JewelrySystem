import os
import json
import base64
from flask import Flask, request, jsonify, render_template_string
import pandas as pd
from datetime import datetime, timedelta
import urllib.request

app = Flask(__name__)
DATA_FILE = 'jewelry_data.json'

GH_TOKEN = os.environ.get('GH_TOKEN')
GH_REPO = os.environ.get('GH_REPO')

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    if GH_TOKEN and GH_REPO:
        try:
            url = f"https://api.github.com/repos/{GH_REPO}/contents/{DATA_FILE}"
            req = urllib.request.Request(url)
            req.add_header('Authorization', f'token {GH_TOKEN}')
            req.add_header('Accept', 'application/vnd.github.v3+json')
            req.add_header('User-Agent', 'Flask-App')
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                content = base64.b64decode(res_data['content']).decode('utf-8')
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    f.write(content)
                return json.loads(content)
        except Exception as e:
            print("从 GitHub 恢复数据失败:", str(e))
    return []

def save_data(data):
    content_str = json.dumps(data, ensure_ascii=False, indent=4)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(content_str)
    if not GH_TOKEN or not GH_REPO:
        return
    try:
        url = f"https://api.github.com/repos/{GH_REPO}/contents/{DATA_FILE}"
        sha = None
        try:
            req_get = urllib.request.Request(url)
            req_get.add_header('Authorization', f'token {GH_TOKEN}')
            req_get.add_header('User-Agent', 'Flask-App')
            with urllib.request.urlopen(req_get, timeout=3) as resp:
                sha = json.loads(resp.read().decode('utf-8')).get('sha')
        except:
            pass
        put_data = {
            "message": "🔄 移动优化版系统账本自动同步",
            "content": base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
        }
        if sha: put_data["sha"] = sha
        req_put = urllib.request.Request(url, method='PUT', data=json.dumps(put_data).encode('utf-8'))
        req_put.add_header('Authorization', f'token {GH_TOKEN}')
        req_put.add_header('Content-Type', 'application/json')
        req_put.add_header('User-Agent', 'Flask-App')
        with urllib.request.urlopen(req_put, timeout=5) as resp:
            print("GitHub 云端同步成功")
    except Exception as e:
        print("同步到 GitHub 失败:", str(e))

def get_bj_today():
    bj_time = datetime.utcnow() + timedelta(hours=8)
    return bj_time.strftime('%Y-%m-%d')

# HTML 模板：融入 Tab 切换、横向滑动、售价与工费列
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>丰高珠宝库存管理系统 3.8 移动精简版</title>
    <script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f5f7; margin: 0; padding: 10px; color: #333; -webkit-text-size-adjust: 100%; }
        .card { background: white; padding: 12px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); margin-bottom: 10px; box-sizing: border-box; }
        
        /* 今日业绩迷你卡 */
        .sales-dashboard { background: linear-gradient(135deg, #007aff, #5856d6); color: white; padding: 12px; border-radius: 12px; text-align: center; margin-bottom: 10px; }
        .sales-dashboard h3 { margin: 0; font-size: 13px; opacity: 0.9; font-weight: normal; }
        .sales-dashboard .count { font-size: 26px; font-weight: bold; margin: 5px 0; }
        
        /* 💡 核心：Tab 标签切换样式 */
        .tab-header { display: flex; background: #eee; border-radius: 8px; padding: 2px; margin-bottom: 10px; }
        .tab-btn { flex: 1; text-align: center; padding: 8px 0; font-size: 14px; cursor: pointer; border-radius: 6px; font-weight: bold; color: #666; transition: all 0.2s; }
        .tab-btn.active { background: white; color: #007aff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        h2 { margin-top: 0; margin-bottom: 8px; color: #111; font-size: 15px; border-left: 4px solid #007aff; padding-left: 6px; }
        .btn { background: #007aff; color: white; border: none; padding: 10px; border-radius: 8px; font-size: 14px; width: 100%; cursor: pointer; font-weight: bold; }
        .btn-green { background: #34c759; }
        .btn-scan { background: #5856d6; margin-bottom: 8px; }
        
        input[type="file"], input[type="text"] { width: 100%; padding: 10px; margin: 6px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 14px; }
        
        /* 💡 核心：看板允许左右滑动，且强制文字单行不换行 */
        .table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid #eee; border-radius: 6px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; white-space: nowrap; }
        th, td { padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #f9f9f9; font-weight: 600; color: #666; position: sticky; top: 0; }
        
        .tips { font-size: 11px; color: #888; margin-top: 4px; }
        #reader { width: 100%; max-width: 350px; margin: 0 auto; background: #000; border-radius: 8px; overflow: hidden; display: none; }
        .preview-zone { display: none; background: #fff9e6; border: 1px dashed #ff9500; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
    </style>
</head>
<body>

    <div class="sales-dashboard" onclick="toggleSection('todayDetailBox')">
        <h3>💰 今日出库简报 (点击可展开/折叠明细)</h3>
        <div class="count" id="todayCount">0 件</div>
        <div id="todayWeight" style="font-size: 12px; opacity: 0.9;">总金重: 0g</div>
    </div>

    <div class="card" id="todayDetailBox">
        <h2>🛍️ 今日卖出明细 (横滑可看全)</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr style="background: #fff5f5;">
                        <th>条码/标签</th><th>货品名称</th><th>金重(g)</th><th>售价</th><th>工费</th><th>时间</th>
                    </tr>
                </thead>
                <tbody id="todaySalesBody"></tbody>
            </table>
        </div>
    </div>

    <div class="card">
        <div class="tab-header">
            <div class="tab-btn active" id="tabOp1" onclick="switchTab('Op', 1)">📦 货品入库 (Excel)</div>
            <div class="tab-btn" id="tabOp2" onclick="switchTab('Op', 2)">🛒 商品出库 (扫码)</div>
        </div>
        
        <div class="tab-content active" id="contentOp1">
            <input type="file" id="excelFile" accept=".xlsx, .xls">
            <button class="btn btn-green" onclick="uploadExcel()">选择并解析 Excel</button>
            <div class="tips">支持列名：标签/条码、货品/款式、金重/克重、售价、工费。</div>
        </div>
        
        <div class="tab-content" id="contentOp2">
            <button class="btn btn-scan" id="scanBtn" onclick="toggleScanner()">📷 开启摄像头扫码</button>
            <div id="reader"></div>
            <input type="text" id="barcodeInput" placeholder="在此手动输入条码核销">
            <button class="btn" onclick="submitCheckout()">确认出库</button>
        </div>
    </div>

    <div class="preview-zone" id="previewZone">
        <h2 style="border-left-color: #ff9500; font-size:14px;">⚠️ 待导入数据安全预览</h2>
        <div class="table-container" style="max-height: 150px; background: white;">
            <table>
                <thead>
                    <tr><th>条码</th><th>货品名称</th><th>金重</th><th>售价</th><th>工费</th></tr>
                </thead>
                <tbody id="previewBody"></tbody>
            </table>
        </div>
        <div style="display:flex; gap:8px; margin-top:8px;">
            <button class="btn btn-green" style="padding:8px;" onclick="confirmImport()">锁定上架</button>
            <button class="btn" style="background:#ff3b30; padding:8px;" onclick="cancelImport()">取消</button>
        </div>
    </div>

    <div class="card">
        <div class="tab-header">
            <div class="tab-btn active" id="tabView 1" onclick="switchTab('View', 1)">🟢 当前在售库存</div>
            <div class="tab-btn" id="tabView 2" onclick="switchTab('View', 2)">📜 历史已售累计</div>
        </div>
        
        <div class="tab-content active" id="contentView1">
            <div class="tips" style="color:#34c759; margin-bottom:6px;">💡 提示：下方表格可左右滑动查看售价、工费详情。</div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr><th>条码/标签</th><th>货品名称</th><th>金重(g)</th><th>售价</th><th>工费</th><th>状态</th></tr>
                    </thead>
                    <tbody id="inventoryBody"></tbody>
                </table>
            </div>
        </div>
        
        <div class="tab-content" id="contentView2">
            <div class="table-container">
                <table>
                    <thead>
                        <tr style="background: #fdf2f2;">
                            <th>条码/标签</th><th>货品名称</th><th>金重(g)</th><th>售价</th><th>工费</th><th>售出日期</th>
                        </tr>
                    </thead>
                    <tbody id="soldBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let html5QrcodeScanner = null;
        let tempParsedData = null;

        window.onload = loadAllData;

        // Tab 切换核心逻辑
        function switchTab(moduleName, index) {
            document.querySelectorAll(`[id^="tab${moduleName}"]`).forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll(`[id^="content${moduleName}"]`).forEach(content => content.classList.remove('active'));
            
            document.getElementById(`tab${moduleName}${index}`).classList.add('active');
            document.getElementById(`content${moduleName}${index}`).classList.add('active');
        }

        function toggleSection(id) {
            const el = document.getElementById(id);
            el.style.display = (el.style.display === 'none') ? 'block' : 'none';
        }

        function loadAllData() {
            fetch('/api/inventory')
                .then(res => res.json())
                .then(res => {
                    // 1. 渲染在售库存
                    const tbody = document.getElementById('inventoryBody');
                    tbody.innerHTML = '';
                    if(!res.active || res.active.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#999;">无存货</td></tr>';
                    } else {
                        res.active.forEach(item => {
                            tbody.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${item.weight}g</td><td>${item.price || '-'}</td><td>${item.wage || '-'}</td><td style="color:#34c759;font-weight:bold;">在售</td></tr>`;
                        });
                    }

                    // 2. 渲染历史已售
                    const sbody = document.getElementById('soldBody');
                    sbody.innerHTML = '';
                    if(!res.sold || res.sold.length === 0) {
                        sbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#999;">无记录</td></tr>';
                    } else {
                        res.sold.forEach(item => {
                            sbody.innerHTML += `<tr><td><del>${item.code}</del></td><td>${item.name}</td><td>${item.weight}g</td><td>${item.price || '-'}</td><td>${item.wage || '-'}</td><td style="color:#ff3b30;">${item.sold_date || '-'}</td></tr>`;
                        });
                    }

                    // 3. 今日大盘数字
                    document.getElementById('todayCount').innerText = res.today_count + ' 件';
                    document.getElementById('todayWeight').innerText = '总金重: ' + res.today_weight.toFixed(3) + 'g';

                    // 4. 今日出库明细
                    const tbodyToday = document.getElementById('todaySalesBody');
                    tbodyToday.innerHTML = '';
                    if(!res.today_list || res.today_list.length === 0) {
                        tbodyToday.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#999;">今日暂无出库</td></tr>';
                    } else {
                        res.today_list.forEach(item => {
                            tbodyToday.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${item.weight}g</td><td>${item.price || '-'}</td><td>${item.wage || '-'}</td><td>${(item.sold_date || '').substring(5)}</td></tr>`;
                        });
                    }
                });
        }

        function uploadExcel() {
            const fileInput = document.getElementById('excelFile');
            if (!fileInput.files[0]) { alert('请选择 Excel 文件！'); return; }
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
                            pbody.innerHTML += `<tr><td>${item.code}</td><td>${item.name}</td><td>${item.weight}g</td><td>${item.price}</td><td>${item.wage}</td></tr>`;
                        });
                        document.getElementById('previewZone').style.display = 'block';
                    } else { alert('解析失败：' + res.msg); }
                });
        }

        function confirmImport() {
            if (!tempParsedData) return;
            fetch('/api/confirm_save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: tempParsedData })
            })
            .then(res => res.json())
            .then(res => {
                alert(res.msg);
                cancelImport();
                loadAllData();
            });
        }

        function cancelImport() {
            tempParsedData = null;
            document.getElementById('previewZone').style.display = 'none';
            document.getElementById('excelFile').value = '';
        }

        function toggleScanner() {
            const readerDiv = document.getElementById('reader');
            const scanBtn = document.getElementById('scanBtn');
            if (readerDiv.style.display === 'block') { stopScanner(); } else {
                readerDiv.style.display = 'block';
                scanBtn.innerText = '🛑 关闭扫码器';
                html5QrcodeScanner = new Html5Qrcode("reader");
                html5QrcodeScanner.start(
                    { facingMode: "environment" },
                    { fps: 10, qrbox: { width: 220, height: 220 } },
                    (decodedText) => {
                        document.getElementById('barcodeInput').value = decodedText;
                        stopScanner();
                        alert('扫码成功: ' + decodedText);
                    },
                    () => {}
                ).catch(() => { alert("请在独立浏览器中打开网页以唤醒相机。"); stopScanner(); });
            }
        }

        function stopScanner() {
            if (html5QrcodeScanner) {
                html5QrcodeScanner.stop().then(() => {
                    document.getElementById('reader').style.display = 'none';
                    document.getElementById('scanBtn').innerText = '📷 开启东方扫码';
                }).catch(() => {
                    document.getElementById('reader').style.display = 'none';
                    document.getElementById('scanBtn').innerText = '📷 开启东方扫码';
                });
            }
        }

        function submitCheckout() {
            const code = document.getElementById('barcodeInput').value.trim();
            if (!code) { alert('请输入条码！'); return; }
            fetch('/api/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code })
            })
            .then(res => res.json())
            .then(res => {
                alert(res.msg);
                if (res.success) {
                    document.getElementById('barcodeInput').value = '';
                    loadAllData();
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
    all_data = load_data()
    today_str = get_bj_today()
    active_list, sold_list, today_sales_list = [], [], []
    today_weight = 0.0
    
    for item in all_data:
        status = item.get('status', '在售')
        if status == '已售出':
            sold_list.append(item)
            if item.get('sold_date') == today_str:
                today_sales_list.append(item)
                try: today_weight += float(item.get('weight', 0) or 0)
                except: pass
        else:
            active_list.append(item)
            
    return jsonify({
        'active': active_list, 'sold': sold_list,
        'today_count': len(today_sales_list), 'today_weight': today_weight, 'today_list': today_sales_list
    })

@app.route('/api/parse_preview', methods=['POST'])
def parse_preview():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '未找到文件'})
    file = request.files['file']
    if file.filename == '': return jsonify({'success': False, 'msg': '文件名为空'})
    try:
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        
        code_col, name_col, weight_col = None, None, None
        price_col, wage_col = None, None
        
        for col in df.columns:
            low_col = col.lower()
            if any(k in low_col for k in ['标签', '条码', '编码', '码', 'code']): code_col = col
            elif any(k in low_col for k in ['名', '货品', '商品', '款式', 'name']): name_col = col
            elif any(k in low_col for k in ['重', '金重', '克重', 'weight']): weight_col = col
            elif any(k in low_col for k in ['售价', '价格', '零售价', 'price']): price_col = col
            elif any(k in low_col for k in ['工费', '工费/克', '工费/件', 'wage', 'fee']): wage_col = col

        if not code_col: return jsonify({'success': False, 'msg': '找不到条码列'})

        preview_list = []
        for _, row in df.iterrows():
            raw_code = row[code_col]
            if pd.isna(raw_code): continue
            code_str = str(raw_code).strip().split('.')[0]
            if not code_str: continue

            name_val = str(row[name_col]).strip() if (name_col and not pd.isna(row[name_col])) else "珠宝货品"
            
            weight_val = ""
            if weight_col and not pd.isna(row[weight_col]):
                try: weight_val = str(round(float(row[weight_col]), 3))
                except: weight_val = str(row[weight_col]).strip()
                
            price_val = ""
            if price_col and not pd.isna(row[price_col]):
                try: price_val = str(round(float(row[price_col]), 2))
                except: price_val = str(row[price_col]).strip()
                
            wage_val = ""
            if wage_col and not pd.isna(row[wage_col]):
                try: wage_val = str(round(float(row[wage_col]), 2))
                except: wage_val = str(row[wage_col]).strip()

            preview_list.append({
                "code": code_str, "name": name_val, "weight": weight_val, 
                "price": price_val, "wage": wage_val, "quantity": 1
            })
        return jsonify({'success': True, 'data': preview_list})
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/confirm_save', methods=['POST'])
def confirm_save():
    req = request.get_json() or {}
    new_items = req.get('data', [])
    current_data = load_data()
    existing_codes = {str(item['code']) for item in current_data}
    added_count = 0
    for item in new_items:
        if item['code'] not in existing_codes:
            current_data.append({
                "code": item['code'], "name": item['name'], "weight": item['weight'], 
                "price": item.get('price', ''), "wage": item.get('wage', ''),
                "quantity": 1, "status": "在售"
            })
            existing_codes.add(item['code'])
            added_count += 1
    save_data(current_data)
    return jsonify({'success': True, 'msg': f'🎉 成功入库 {added_count} 件新品并同步！'})

@app.route('/api/checkout', methods=['POST'])
def checkout():
    req = request.get_json() or {}
    code = str(req.get('code', '')).strip()
    if not code: return jsonify({'success': False, 'msg': '请输入条码！'})
        
    current_data = load_data()
    today_str = get_bj_today()
    for item in current_data:
        if str(item['code']).strip() == code:
            if item['status'] == '已售出':
                return jsonify({'success': False, 'msg': f'⚠️ 条码 {code} 之前早已卖出'})
            item['status'] = '#已售出'
            item['status'] = '已售出'
            item['sold_date'] = today_str
            save_data(current_data)
            return jsonify({'success': True, 'msg': f'🛍 货品 {code} 核销出库成功！'})
    return jsonify({'success': False, 'msg': f'❌ 未找到条码 [{code}]'})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
