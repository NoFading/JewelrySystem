import os
import json
from flask import Flask, request, jsonify, render_template_string
import pandas as pd
from datetime import datetime, timedelta

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

# 获取当前北京时间日期字符串 (YYYY-MM-DD)
def get_bj_today():
    # Render 服务器通常是 UTC 时间，通过增加 8 小时得到北京时间
    bj_time = datetime.utcnow() + timedelta(hours=8)
    return bj_time.strftime('%Y-%m-%d')

# 3.0 销售业绩看板一体化前端
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>丰高珠宝库存管理系统 3.0 销售看板版</title>
    <script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <style>
        body { font-family: -apple-system, sans-serif; background: #f4f5f7; margin: 0; padding: 15px; color: #333; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 15px; }
        
        /* 今日业绩高亮卡片 */
        .sales-dashboard { background: linear-gradient(135deg, #007aff, #5856d6); color: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,122,255,0.2); margin-bottom: 15px; text-align: center; }
        .sales-dashboard h3 { margin: 0; font-size: 15px; opacity: 0.9; font-weight: normal; }
        .sales-dashboard .count { font-size: 36px; font-weight: bold; margin: 10px 0 5px 0; }
        
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
        
        /* 折叠样式 */
        .toggle-title { display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
        .toggle-content { display: none; margin-top: 15px; }
        .arrow { font-size: 14px; transition: transform 0.2s; }
    </style>
</head>
<body>

    <div class="sales-dashboard">
        <h3>💰 今天的销售情况</h3>
        <div class="count" id="todayCount">0 件</div>
        <div id="todayWeight" style="font-size: 13px; opacity: 0.9;">今日出库总金重: 0g</div>
    </div>

    <div class="card">
        <div class="toggle-title" onclick="toggleSection('todayDetailContent', 'todayArrow')">
            <h2>🛍️ 今日卖出的货品明细</h2>
            <span class="arrow" id="todayArrow">▼ 点击展开</span>
        </div>
        <div class="toggle-content" id="todayDetailContent" style="display: block;"> <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr style="background: #fff5f5;">
                            <th>标签号/条码</th>
                            <th>货品名称</th>
                            <th>金重(g)</th>
                            <th>核销时间</th>
                        </tr>
                    </thead>
                    <tbody id="todaySalesBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="preview-zone" id="previewZone">
        <h2 style="border-left-color: #ff9500; color: #000;">⚠️ 侦测到待导入数据（安全预览中）</h2>
        <p class="tips" style="color: #ff9500; font-weight: bold;">提示：此时数据尚未写入云端，如不对请点「取消导入」！</p>
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
            <button class="btn btn-red" style="flex: 1;" onclick="cancelImport()">❌ 取消导入</button>
        </div>
    </div>

    <div class="card">
        <h2>📦 货品入库 (安全 Excel 渠道)</h2>
        <input type="file" id="excelFile" accept=".xlsx, .xls">
        <button class="btn btn-green" onclick="uploadExcel()">选择并解析 Excel 文件</button>
    </div>

    <div class="card">
        <h2>🛒 商品出库 (扫码/手动)</h2>
        <button class="btn btn-scan" id="scanBtn" onclick="toggleScanner()">📷 点击扫码卖出</button>
        <div id="reader"></div>
        <input type="text" id="barcodeInput" placeholder="栏位无法扫码时，请在此手动输入条码">
        <button class="btn" onclick="submitCheckout()">确认核销出库</button>
        <div class="tips" style="color: #ff9500;">⚠️ 提示：若浏览器无法唤醒摄像头，可以直接在上方框内输入条码核销。</div>
    </div>

    <div class="card">
        <h2>💎 当前【在售】库存看板</h2>
        <div class="tips" style="margin-bottom: 10px; color: #34c759; font-weight: bold;">📊 提示：此处已自动过滤已售货品，仅显示店内存货。</div>
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

    <div class="card">
        <div class="toggle-title" onclick="toggleSection('soldContent', 'soldArrow')">
            <h2>📜 历史【已售出】累计账本</h2>
            <span class="arrow" id="soldArrow">▼ 点击展开</span>
        </div>
        <div class="toggle-content" id="soldContent">
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr style="background: #fdf2f2;">
                            <th>标签号/条码</th>
                            <th>货品名称</th>
                            <th>金重(g)</th>
                            <th>售出日期</th>
                            <th>状态</th>
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

        function loadAllData() {
            fetch('/api/inventory')
                .then(res => res.json())
                .then(res => {
                    // 1. 渲染在售库存
                    const tbody = document.getElementById('inventoryBody');
                    tbody.innerHTML = '';
                    if(!res.active || res.active.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#999;">暂无在售库存，请先导入 Excel</td></tr>';
                    } else {
                        res.active.forEach(item => {
                            tbody.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${item.weight}g</td><td>${item.quantity}</td><td style="color:#34c759; font-weight:bold;">在售</td></tr>`;
                        });
                    }

                    // 2. 渲染历史已售
                    const sbody = document.getElementById('soldBody');
                    sbody.innerHTML = '';
                    if(!res.sold || res.sold.length === 0) {
                        sbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#999;">暂无售出记录</td></tr>';
                    } else {
                        res.sold.forEach(item => {
                            sbody.innerHTML += `<tr><td><del>${item.code}</del></td><td>${item.name}</td><td>${item.weight}g</td><td>${item.sold_date || '-'}</td><td style="color:#ff3b30; font-weight:bold;">已售出</td></tr>`;
                        });
                    }

                    // 3. 渲染今日战报与明细
                    document.getElementById('todayCount').innerText = res.today_count + ' 件';
                    document.getElementById('todayWeight').innerText = '今日出库总金重: ' + res.today_weight.toFixed(3) + 'g';

                    const tbodyToday = document.getElementById('todaySalesBody');
                    tbodyToday.innerHTML = '';
                    if(!res.today_list || res.today_list.length === 0) {
                        tbodyToday.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#999;">今天还没有货品出库</td></tr>';
                    } else {
                        res.today_list.forEach(item => {
                            tbodyToday.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${item.weight}g</td><td>${item.sold_date || '-'}</td></tr>`;
                        });
                    }
                }).catch(() => alert('读取数据失败，请检查网络'));
        }

        // 折叠/展开控制
        function toggleSection(contentId, arrowId) {
            const content = document.getElementById(contentId);
            const arrow = document.getElementById(arrowId);
            if(content.style.display === 'block' || content.style.display === '') {
                content.style.display = 'none';
                arrow.innerText = '▼ 点击展开';
            } else {
                content.style.display = 'block';
                arrow.innerText = '▲ 点击收起';
            }
        }

        // 导入 Excel 解析
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
                }).catch(() => alert('Excel 解析异常'));
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

        // 扫码器控制
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
                        alert('扫码读取成功: ' + decodedText);
                    },
                    () => {}
                ).catch(() => {
                    alert("无法开启摄像头。微信内请点右上角...选择在浏览器打开");
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

        // 确认核销
        function submitCheckout() {
            const code = document.getElementById('barcodeInput').value.trim();
            if (!code) {
                alert('请输入或扫码录入条码！');
                return;
            }
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
            }).catch(() => alert('核销出库失败，请检查网络并确认条码。'));
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# 升级：返回分类并流、包含今日业绩计算的核心数据接口
@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    all_data = load_data()
    today_str = get_bj_today()
    
    active_list = []
    sold_list = []
    today_sales_list = []
    
    today_weight = 0.0
    
    for item in all_data:
        status = item.get('status', '在售')
        if status == '已售出':
            sold_list.append(item)
            # 检查是否是今天卖出的
            if item.get('sold_date') == today_str:
                today_sales_list.append(item)
                try:
                    today_weight += float(item.get('weight', 0) or 0)
                except:
                    pass
        else:
            active_list.append(item)
            
    return jsonify({
        'active': active_list,
        'sold': sold_list,
        'today_count': len(today_sales_list),
        'today_weight': today_weight,
        'today_list': today_sales_list
    })

@app.route('/api/parse_preview', methods=['POST'])
def parse_preview():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '未找到文件'})
    file = request.files['file']
    if file.filename == '': return jsonify({'success': False, 'msg': '文件名为空'})
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

        if not code_col: return jsonify({'success': False, 'msg': '找不到包含“标签”或“条码”的列。'})

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

            preview_list.append({"code": code_str, "name": name_val, "weight": weight_val, "quantity": qty_val})
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
                "code": item['code'], "name": item['name'], "weight": item['weight'], "quantity": item['quantity'], "status": "在售"
            })
            existing_codes.add(item['code'])
            added_count += 1
    save_data(current_data)
    return jsonify({'success': True, 'msg': f'🎉 成功将 {added_count} 件新品并入在售库存！'})

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
                return jsonify({'success': False, 'msg': f'⚠️ 提示：条码 {code} 之前早已卖出，售出日期: {item.get("sold_date","未知")}'})
            item['status'] = '已售出'
            item['sold_date'] = today_str # 记录出库日期为北京时间当天
            save_data(current_data)
            return jsonify({'success': True, 'msg': f'🛍   货品 {code} 核销出库成功！已计入今日销售业绩。'})
            
    return jsonify({'success': False, 'msg': f'❌ 未能在系统库存中找到条码为 [{code}] 的货品。'})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
