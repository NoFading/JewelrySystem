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
            "message": "🔄 5.0 支持退货核销账本同步",
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>丰高珠宝管理系统 5.0 退货核销版</title>
    <script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f5f7; margin: 0; padding: 10px; color: #333; -webkit-text-size-adjust: 100%; }
        .card { background: white; padding: 12px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); margin-bottom: 10px; box-sizing: border-box; }
        
        /* 今日出库简报 */
        .sales-dashboard { background: linear-gradient(135deg, #ff9500, #ff3b30); color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(255,59,48,0.2); }
        .sales-dashboard h3 { margin: 0; font-size: 13px; opacity: 0.9; font-weight: normal; letter-spacing: 1px; }
        .sales-dashboard .count { font-size: 30px; font-weight: bold; margin: 6px 0; font-family: Arial, sans-serif; }
        
        /* Tab 标签切换样式 */
        .tab-header { display: flex; background: #eee; border-radius: 8px; padding: 2px; margin-bottom: 10px; }
        .tab-btn { flex: 1; text-align: center; padding: 9px 0; font-size: 13px; cursor: pointer; border-radius: 6px; font-weight: bold; color: #666; transition: all 0.2s; }
        .tab-btn.active { background: white; color: #ff3b30; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        h2 { margin-top: 0; margin-bottom: 8px; color: #111; font-size: 14px; border-left: 4px solid #ff3b30; padding-left: 6px; }
        .btn { background: #ff3b30; color: white; border: none; padding: 11px; border-radius: 8px; font-size: 14px; width: 100%; cursor: pointer; font-weight: bold; }
        .btn-green { background: #34c759; }
        .btn-blue { background: #007aff; }
        .btn-scan { background: #5856d6; margin-bottom: 8px; }
        
        /* 内部小切换，用于区分销售和退货 */
        .action-toggle { display: flex; gap: 10px; margin-bottom: 10px; }
        .action-radio { flex: 1; text-align: center; padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer; background: #fafafa; }
        .action-radio.selected-sale { background: #fff5f5; border-color: #ff3b30; color: #ff3b30; }
        .action-radio.selected-return { background: #f0f7ff; border-color: #007aff; color: #007aff; }

        .input-title { font-size: 12px; color: #666; margin-top: 6px; font-weight: bold; }
        input[type="file"], input[type="text"], input[type="number"] { width: 100%; padding: 10px; margin: 4px 0 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 14px; }
        
        /* 看板手势横滑 */
        .table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid #eee; border-radius: 6px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; white-space: nowrap; }
        th, td { padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #f9f9f9; font-weight: 600; color: #666; }
        
        .tips { font-size: 11px; color: #888; margin-top: 4px; line-height: 1.4; }
        #reader { width: 100%; max-width: 350px; margin: 0 auto; background: #000; border-radius: 8px; overflow: hidden; display: none; }
        .preview-zone { display: none; background: #fff9e6; border: 1px dashed #ff9500; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
    </style>
</head>
<body>

    <!-- ⚡ 今日业绩速报 (支持退货负向扣减) -->
    <div class="sales-dashboard" onclick="toggleSection('todayDetailBox')">
        <h3>💰 今日累计销售额</h3>
        <div class="count" id="todayAmount">¥ 0.00</div>
        <div id="todayCount" style="font-size: 12px; opacity: 0.9;">今天已成功卖出: 0 件货品</div>
    </div>

    <!-- 🛍️ 今日销售明细 -->
    <div class="card" id="todayDetailBox">
        <h2>🛍️ 今日卖出商品明细 (横滑可看售价)</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr style="background: #fff5f5;">
                        <th>条码/标签</th><th>货品名称</th><th>品类</th><th>金重(g)</th><th>标签标价</th><th>工费</th><th>实际成交售价</th>
                    </tr>
                </thead>
                <tbody id="todaySalesBody"></tbody>
            </table>
        </div>
    </div>

    <!-- 🔄 模块一：【前台收银与日常操作中心】 -->
    <div class="card">
        <div class="tab-header">
            <div class="tab-btn active" id="tabOp1" onclick="switchTab('Op', 1)">🛒 柜台商品销售 (收银)</div>
            <div class="tab-btn" id="tabOp2" onclick="switchTab('Op', 2)">📦 批量货品入库 (Excel)</div>
        </div>
        
        <!-- 子页1：前台销售 & 退货 -->
        <div class="tab-content active" id="contentOp1">
            <button class="btn btn-scan" id="scanBtn" onclick="toggleScanner()">📷 开启摄像头扫码</button>
            <div id="reader"></div>
            
            <!-- 💡 优化项：销售与退货模式切换 -->
            <div class="input-title">请选择当前柜台操作：</div>
            <div class="action-toggle">
                <div class="action-radio selected-sale" id="modeSale" onclick="setMode('sale')">🛍️ 正常销售记账</div>
                <div class="action-radio" id="modeReturn" onclick="setMode('return')">🔄 办理退货核销</div>
            </div>

            <div class="input-title" id="barcodeTitle">第一步：输入或扫描货品条码</div>
            <input type="text" id="barcodeInput" placeholder="请扫码或在此手动输入条码/货号">
            
            <div id="priceInputArea">
                <div class="input-title" style="color: #ff3b30;">第二步：实收客户金额 (实际售价 ¥)</div>
                <input type="number" id="actualPriceInput" step="0.01" placeholder="请输入跟客户谈拢的最终实收总价">
            </div>
            
            <button class="btn" id="submitOpBtn" onclick="executeOperation()">💰 确认销售并记账</button>
            <div class="tips" id="modeTips">提示：点击上方按钮后，货品将自动转入已售账本，并实时累加到今日总销售额中。</div>
        </div>
        
        <!-- 子页2：后台入库 -->
        <div class="tab-content" id="contentOp2">
            <input type="file" id="excelFile" accept=".xlsx, .xls">
            <button class="btn btn-green" onclick="uploadExcel()">选择并解析新货 Excel</button>
            <div class="tips">
                💡 <b>最新 Excel 标准列名：</b><br>
                1. 条码/标签 | 2. 货品名称/名称 | 3. 品类 | 4. 克重/金重 | 5. 标价 | 6. 工费
            </div>
        </div>
    </div>

    <!-- 安全入库预览 -->
    <div class="preview-zone" id="previewZone">
        <h2 style="border-left-color: #ff9500; font-size:13px;">⚠️ 待入库新货安全预览</h2>
        <div class="table-container" style="max-height: 150px; background: white;">
            <table>
                <thead>
                    <tr><th>条码</th><th>货品名称</th><th>品类</th><th>金重</th><th>标价</th><th>工费</th></tr>
                </thead>
                <tbody id="previewBody"></tbody>
            </table>
        </div>
        <div style="display:flex; gap:8px; margin-top:8px;">
            <button class="btn btn-green" style="padding:8px; font-size:12px;" onclick="confirmImport()">确认锁库存上架</button>
            <button class="btn" style="background:#666; padding:8px; font-size:12px;" onclick="cancelImport()">取消</button>
        </div>
    </div>

    <!-- 💎 模块二：【后台库存看板中心】 -->
    <div class="card">
        <div class="tab-header">
            <div class="tab-btn active" id="tabView1" onclick="switchTab('View', 1)">🟢 店内当前在售存货</div>
            <div class="tab-btn" id="tabView2" onclick="switchTab('View', 2)">📜 历史已售出累计账本</div>
        </div>
        
        <!-- 存货 -->
        <div class="tab-content active" id="contentView1">
            <div class="table-container">
                <table>
                    <thead>
                        <tr><th>条码/标签</th><th>货品名称</th><th>品类</th><th>金重(g)</th><th>标签标价</th><th>工费</th><th>状态</th></tr>
                    </thead>
                    <tbody id="inventoryBody"></tbody>
                </table>
            </div>
        </div>
        
        <!-- 历史已售 -->
        <div class="tab-content" id="contentView2">
            <div class="table-container">
                <table>
                    <thead>
                        <tr style="background: #fdf2f2;">
                            <th>条码/标签</th><th>货品名称</th><th>品类</th><th>金重(g)</th><th>标签标价</th><th>工费</th><th style="color: #ff3b30; font-weight: bold;">成交售价</th><th>售出日期</th>
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
        let currentMode = 'sale'; // 'sale' 或 'return'

        window.onload = loadAllData;

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

        // 💡 优化项：动态切换销售和退货的前端视觉
        function setMode(mode) {
            currentMode = mode;
            const modeSale = document.getElementById('modeSale');
            const modeReturn = document.getElementById('modeReturn');
            const priceInputArea = document.getElementById('priceInputArea');
            const submitOpBtn = document.getElementById('submitOpBtn');
            const modeTips = document.getElementById('modeTips');

            if (mode === 'sale') {
                modeSale.classList.add('selected-sale');
                modeReturn.classList.remove('selected-return');
                priceInputArea.style.display = 'block';
                submitOpBtn.innerText = '💰 确认销售并记账';
                submitOpBtn.className = 'btn';
                modeTips.innerText = '提示：点击上方按钮后，货品将自动转入已售账本，并实时累加到今日总销售额中。';
            } else {
                modeSale.remove('selected-sale');
                modeSale.classList.remove('selected-sale');
                modeReturn.classList.add('selected-return');
                priceInputArea.style.display = 'none';
                submitOpBtn.innerText = '🔄 确认退货并恢复库存';
                submitOpBtn.className = 'btn btn-blue';
                modeTips.innerText = '提示：办理退货后，该货品将从已售账本中剔除、重新回到在售库存，且今日大盘销售额会自动扣减这笔退款。';
            }
        }

        function loadAllData() {
            fetch('/api/inventory')
                .then(res => res.json())
                .then(res => {
                    const tbody = document.getElementById('inventoryBody');
                    tbody.innerHTML = '';
                    if(!res.active || res.active.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#999;">暂无在售存货</td></tr>';
                    } else {
                        res.active.forEach(item => {
                            tbody.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${item.category || '-'}</td><td>${item.weight}g</td><td>${item.tag_price || '-'}</td><td>${item.wage || '-'}</td><td style="color:#34c759;font-weight:bold;">在售</td></tr>`;
                        });
                    }

                    const sbody = document.getElementById('soldBody');
                    sbody.innerHTML = '';
                    if(!res.sold || res.sold.length === 0) {
                        sbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:#999;">暂无历史售出账目</td></tr>';
                    } else {
                        res.sold.forEach(item => {
                            sbody.innerHTML += `<tr><td><del>${item.code}</del></td><td>${item.name}</td><td>${item.category || '-'}</td><td>${item.weight}g</td><td>${item.tag_price || '-'}</td><td>${item.wage || '-'}</td><td style="color:#ff3b30; font-weight:bold;">¥ ${item.sold_price || '-'}</td><td>${item.sold_date || '-'}</td></tr>`;
                        });
                    }

                    document.getElementById('todayAmount').innerText = '¥ ' + res.today_money.toFixed(2);
                    document.getElementById('todayCount').innerText = '今天已成功卖出: ' + res.today_count + ' 件货品';

                    const tbodyToday = document.getElementById('todaySalesBody');
                    tbodyToday.innerHTML = '';
                    if(!res.today_list || res.today_list.length === 0) {
                        tbodyToday.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#999;">今天还没有产生销售业绩</td></tr>';
                    } else {
                        res.today_list.forEach(item => {
                            tbodyToday.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${item.category || '-'}</td><td>${item.weight}g</td><td>${item.tag_price || '-'}</td><td>${item.wage || '-'}</td><td style="color:#ff3b30; font-weight:bold;">¥ ${item.sold_price || '-'}</td></tr>`;
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
                            pbody.innerHTML += `<tr><td>${item.code}</td><td>${item.name}</td><td>${item.category}</td><td>${item.weight}g</td><td>${item.tag_price}</td><td>${item.wage}</td></tr>`;
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
                    },
                    () => {}
                ).catch(() => { alert("未检测到摄像头授权。"); stopScanner(); });
            }
        }

        function stopScanner() {
            if (html5QrcodeScanner) {
                html5QrcodeScanner.stop().then(() => {
                    document.getElementById('reader').style.display = 'none';
                    document.getElementById('scanBtn').innerText = '📷 开启摄像头扫码';
                }).catch(() => {
                    document.getElementById('reader').style.display = 'none';
                    document.getElementById('scanBtn').innerText = '📷 开启摄像头扫码';
                });
            }
        }

        // 💡 核心操作分流控制
        function executeOperation() {
            const code = document.getElementById('barcodeInput').value.trim();
            if (!code) { alert('请先输入或扫描货品条码！'); return; }

            if (currentMode === 'sale') {
                const actualPrice = document.getElementById('actualPriceInput').value.trim();
                if (!actualPrice) { alert('请输入实收客户的最终金额（售价）！'); return; }
                
                fetch('/api/checkout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: code, sold_price: actualPrice })
                })
                .then(res => res.json())
                .then(res => {
                    alert(res.msg);
                    if (res.success) {
                        document.getElementById('barcodeInput').value = '';
                        document.getElementById('actualPriceInput').value = '';
                        loadAllData();
                    }
                });
            } else {
                // 💡 退货处理
                if (!confirm(`确认要为条码 [${code}] 办理退货核销吗？该货品将重新上架为在售库存。`)) return;
                fetch('/api/return_item', {
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
    today_money = 0.0
    
    for item in all_data:
        status = item.get('status', '在售')
        if status == '已售出':
            sold_list.append(item)
            if item.get('sold_date') == today_str:
                today_sales_list.append(item)
                try: 
                    today_money += float(item.get('sold_price', 0) or 0)
                except: 
                    pass
        else:
            active_list.append(item)
            
    return jsonify({
        'active': active_list, 'sold': sold_list,
        'today_count': len(today_sales_list), 'today_money': today_money, 'today_list': today_sales_list
    })

@app.route('/api/parse_preview', methods=['POST'])
def parse_preview():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '未找到文件'})
    file = request.files['file']
    if file.filename == '': return jsonify({'success': False, 'msg': '文件名为空'})
    try:
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        
        code_col, name_col, cate_col, weight_col, tag_col, wage_col = None, None, None, None, None, None
        
        for col in df.columns:
            low_col = col.lower()
            if any(k in low_col for k in ['条码', '标签', '编码', '码', 'code']): code_col = col
            elif any(k in low_col for k in ['货品名称', '名称', '款式', 'name']): name_col = col
            elif any(k in low_col for k in ['品类', '类型', '分类', 'category']): cate_col = col
            elif any(k in low_col for k in ['克重', '金重', '重量', 'weight']): weight_col = col
            elif any(k in low_col for k in ['标价', '售价', '价格', '零售价', 'price']): tag_col = col
            elif any(k in low_col for k in ['工费', 'wage', 'fee']): wage_col = col

        if not code_col: return jsonify({'success': False, 'msg': 'Excel 中未能识别到“条码”或“标签”列！'})

        preview_list = []
        for _, row in df.iterrows():
            raw_code = row[code_col]
            if pd.isna(raw_code): continue
            code_str = str(raw_code).strip().split('.')[0]
            if not code_str: continue

            name_val = str(row[name_col]).strip() if (name_col and not pd.isna(row[name_col])) else "未命名货品"
            cate_val = str(row[cate_col]).strip() if (cate_col and not pd.isna(row[cate_col])) else "其他"
            
            weight_val = "0"
            if weight_col and not pd.isna(row[weight_col]):
                try: weight_val = str(round(float(row[weight_col]), 3))
                except: weight_val = str(row[weight_col]).strip()
                
            tag_val = ""
            if tag_col and not pd.isna(row[tag_col]):
                try: tag_val = str(round(float(row[tag_col]), 2))
                except: tag_val = str(row[tag_col]).strip()
                
            wage_val = ""
            if wage_col and not pd.isna(row[wage_col]):
                try: wage_val = str(round(float(row[wage_col]), 2))
                except: wage_val = str(row[wage_col]).strip()

            preview_list.append({
                "code": code_str, "name": name_val, "category": cate_val,
                "weight": weight_val, "tag_price": tag_val, "wage": wage_val
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
                "code": item['code'], "name": item['name'], "category": item.get('category', '其他'),
                "weight": item['weight'], "tag_price": item.get('tag_price', ''), "wage": item.get('wage', ''),
                "status": "在售"
            })
            existing_codes.add(item['code'])
            added_count += 1
    save_data(current_data)
    return jsonify({'success': True, 'msg': f'🎉 成功入库 {added_count} 件新品！'})

@app.route('/api/checkout', methods=['POST'])
def checkout():
    req = request.get_json() or {}
    code = str(req.get('code', '')).strip()
    sold_price = str(req.get('sold_price', '')).strip()
        
    current_data = load_data()
    today_str = get_bj_today()
    for item in current_data:
        if str(item['code']).strip() == code:
            if item['status'] == '已售出':
                return jsonify({'success': False, 'msg': f'⚠️ 提示：条码 {code} 早已卖出，售价为 ¥{item.get("sold_price","0")}'})
            
            item['status'] = '已售出'
            item['sold_date'] = today_str
            try:
                item['sold_price'] = str(round(float(sold_price), 2))
            except:
                item['sold_price'] = sold_price
                
            save_data(current_data)
            return jsonify({'success': True, 'msg': f'🛍 货品 {code} 成功售出！实收金额 ¥{item["sold_price"]} 已记入今日大盘。'})
    return jsonify({'success': False, 'msg': f'❌ 未能在店内库存中找到条码为 [{code}] 的货品。'})

# 💡 升级核心：新增退货接口逻辑
@app.route('/api/return_item', methods=['POST'])
def return_item():
    req = request.get_json() or {}
    code = str(req.get('code', '')).strip()
    
    current_data = load_data()
    for item in current_data:
        if str(item['code']).strip() == code:
            if item['status'] == '在售':
                return jsonify({'success': False, 'msg': f'⚠️ 提示：该货品 [ {code} ] 当前本来就在在售库存中，无需退货。'})
            
            # 还原状态，抹除历史售价与售出日期
            old_price = item.get('sold_price', '0')
            item['status'] = '在售'
            if 'sold_date' in item: del item['sold_date']
            if 'sold_price' in item: del item['sold_price']
            
            save_data(current_data)
            return jsonify({'success': True, 'msg': f'🔄 退货核销成功！货品 {code} 已重新上架。大盘已扣减该笔金额 ¥{old_price}。'})
            
    return jsonify({'success': False, 'msg': f'❌ 未能在系统大账本中找到条码为 [{code}] 的任何货品记录。'})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
