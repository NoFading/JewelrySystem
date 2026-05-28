from flask import Flask, request, jsonify, render_template_string
import json
import os

app = Flask(__name__)

DB_FILE = os.path.join(os.path.dirname(__file__), 'jewelry_data.json')

if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False)

def read_db():
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    html_content = '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>珠宝店多端同步云助手 v4.0</title>
        <script src="https://lf26-cdn-tos.bytecdntp.com/cdn/expire-1-M/html5-qrcode/2.1.6/html5-qrcode.min.js"></script>
        <script src="https://lf3-cdn-tos.bytecdntp.com/cdn/expire-1-M/xlsx/0.18.5/xlsx.full.min.js"></script>
        <style>
            :root { --primary-color: #2ecc71; --danger-color: #e74c3c; --bg-color: #333333; --card-bg: #444444; --text-color: #ffffff; }
            * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background-color: var(--bg-color); color: var(--text-color); padding: 10px; padding-bottom: 30px; font-size: 14px; }
            .kpi-container { display: flex; gap: 10px; margin-bottom: 15px; }
            .kpi-card { flex: 1; background: var(--card-bg); border-radius: 8px; padding: 12px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
            .kpi-title { font-size: 13px; color: #aaa; margin-bottom: 4px; }
            .kpi-value { font-size: 22px; font-weight: bold; }
            .kpi-value.stock { color: var(--primary-color); }
            .kpi-value.sold { color: var(--danger-color); }
            .section-title { font-size: 15px; font-weight: bold; margin: 15px 0 8px 0; }
            .btn { display: block; width: 100%; padding: 14px; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; color: white; text-align: center; cursor: pointer; box-shadow: 0 3px 6px rgba(0,0,0,0.3); margin-bottom: 12px; }
            .btn-sell { background: linear-gradient(135deg, #e74c3c, #c0392b); }
            .btn-import { background: linear-gradient(135deg, #2ecc71, #27ae60); position: relative; }
            .file-input { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
            .notice-box { background: rgba(241, 196, 15, 0.15); border-left: 4px solid #f1c40f; padding: 10px; border-radius: 4px; font-size: 12px; color: #f1c40f; margin-bottom: 15px; }
            .view-toggle { display: flex; background: var(--card-bg); border-radius: 8px; padding: 3px; margin-bottom: 12px; }
            .toggle-btn { flex: 1; padding: 10px; text-align: center; border-radius: 6px; font-weight: bold; font-size: 13px; cursor: pointer; }
            .toggle-btn.active { background: #555; color: var(--primary-color); }
            .data-list { background: var(--card-bg); border-radius: 8px; overflow: hidden; }
            .table-header, .table-row { display: flex; padding: 10px; border-bottom: 1px solid #555; align-items: center; }
            .table-header { background: #4f4f4f; font-weight: bold; font-size: 12px; color: #ddd; }
            .col-info { flex: 2.5; min-width: 0; }
            .col-cate { flex: 1.2; text-align: center; }
            .col-weight { flex: 1.2; text-align: right; }
            .col-price { flex: 1.5; text-align: right; font-weight: bold; }
            .col-fee { flex: 1.2; text-align: right; }
            .good-name { font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .good-barcode { font-size: 11px; color: #999; margin-top: 2px; font-family: monospace; }
            #reader { width: 100%; border-radius: 8px; overflow: hidden; margin-bottom: 15px; display: none; }
            .text-center { text-align: center; padding: 20px; color: #aaa; }
            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center; padding: 20px; }
            .modal-content { background: var(--card-bg); padding: 20px; border-radius: 12px; width: 100%; max-width: 400px; }
            .modal-title { font-size: 16px; font-weight: bold; margin-bottom: 12px; text-align: center; }
            .input-control { width: 100%; padding: 12px; border: 1px solid #555; background: #333; color: white; border-radius: 6px; font-size: 16px; margin-bottom: 15px; }
            .modal-foot { display: flex; gap: 10px; }
            .btn-m { flex: 1; padding: 10px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
            .btn-confirm { background: #f39c12; color: white; }
            .btn-cancel { background: #666; color: white; }
        </style>
    </head>
    <body>
        <div class="kpi-container">
            <div class="kpi-card"><div class="kpi-title">在库总件数</div><div class="kpi-value stock" id="kpi-stock">加载中...</div></div>
            <div class="kpi-card"><div class="kpi-title">今日已售</div><div class="kpi-value sold" id="kpi-sold">加载中...</div></div>
        </div>

        <div id="reader"></div>

        <div class="section-title">🛍️ 商品出库（卖出）</div>
        <button class="btn btn-sell" onclick="toggleScanner()">📷 点击扫码卖出</button>
        <button class="btn btn-sell" style="background: linear-gradient(135deg, #f39c12, #d35400); margin-top:-5px;" onclick="openManualModal()">✏️ 手动输入条码卖出</button>

        <div class="section-title">📥 货物入库（规范 Excel 导入）</div>
        <div class="notice-box">⚠️ Excel 必须包含这6列：<strong>条码、名称、品类、克重、标价、工费</strong></div>
        <button class="btn btn-import">
            💚 选择并导入 Excel 文件
            <input type="file" class="file-input" id="excel-file" accept=".xlsx, .xls" onchange="importExcel(this)">
        </button>

        <div class="view-toggle">
            <div class="toggle-btn active" id="btn-view-stock" onclick="switchView('stock')">当前在库清单</div>
            <div class="toggle-btn" id="btn-view-sold" onclick="switchView('sold')">看已售账本</div>
        </div>

        <div class="data-list">
            <div class="table-header">
                <div class="col-info">商品信息</div><div class="col-cate">品类</div><div class="col-weight">克重</div><div class="col-price">标价</div><div class="col-fee">工费</div>
            </div>
            <div id="table-body"></div>
        </div>

        <div class="modal" id="manual-modal">
            <div class="modal-content">
                <div class="modal-title">手动核销核对</div>
                <input type="text" class="input-control" id="manual-barcode" placeholder="请输入完整条码">
                <div class="modal-foot">
                    <button class="btn-m btn-confirm" onclick="submitManualSell()">确认卖出</button>
                    <button class="btn-m btn-cancel" onclick="closeManualModal()">取消</button>
                </div>
            </div>
        </div>

        <script>
            let db = [];
            let currentView = 'stock';
            let html5QrcodeScanner = null;

            window.onload = function() { loadDataFromServer(); };

            function loadDataFromServer() {
                fetch('/api/data')
                    .then(res => res.json())
                    .then(data => {
                        db = data;
                        refreshUI();
                    });
            }

            function syncDataToServer() {
                fetch('/api/sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(db)
                })
                .then(res => res.json())
                .then(res => { if(!res.success) alert("数据同步失败！"); });
            }

            function refreshUI() {
                const stockList = db.filter(item => !item.sold_time);
                const todayStr = new Date().toDateString();
                const soldTodayList = db.filter(item => item.sold_time && new Date(item.sold_time).toDateString() === todayStr);
                
                document.getElementById('kpi-stock').innerText = stockList.length + ' 件';
                document.getElementById('kpi-sold').innerText = soldTodayList.length + ' 件';
                
                const renderList = currentView === 'stock' ? stockList : db.filter(item => item.sold_time).sort((a,b)=>new Date(b.sold_time)-new Date(a.sold_time));
                const tbody = document.getElementById('table-body');
                tbody.innerHTML = '';
                
                if (renderList.length === 0) {
                    tbody.innerHTML = `<div class="text-center">暂无${currentView === 'stock'?'在库商品':'已售记录'}</div>`;
                    return;
                }
                
                renderList.forEach(item => {
                    const row = document.createElement('div');
                    row.className = 'table-row';
                    row.innerHTML = `
                        <div class="col-info">
                            <div class="good-name">${item.名称 || '未命名'}</div>
                            <div class="good-barcode">${item.条码}</div>
                            ${item.sold_time ? `<div style="font-size:11px; color:#e74c3c; margin-top:2px;">售出: ${new Date(item.sold_time).toLocaleTimeString()}</div>` : ''}
                        </div>
                        <div class="col-cate">${item.品类 || '-'}</div>
                        <div class="col-weight">${item.克重 ? parseFloat(item.克重).toFixed(2)+'g' : '0g'}</div>
                        <div class="col-price">${item.标价 ? '￥'+parseFloat(item.标价).toFixed(0) : '￥0'}</div>
                        <div class="col-fee">${item.工费 ? '￥'+parseFloat(item.工费).toFixed(0) : '￥0'}</div>
                    `;
                    tbody.appendChild(row);
                });
            }

            function switchView(view) {
                currentView = view;
                document.getElementById('btn-view-stock').className = view === 'stock' ? 'toggle-btn active' : 'toggle-btn';
                document.getElementById('btn-view-sold').className = view === 'sold' ? 'toggle-btn active' : 'toggle-btn';
                refreshUI();
            }

            function toggleScanner() {
                const readerDiv = document.getElementById('reader');
                if (readerDiv.style.display === 'block') { stopScanner(); } 
                else {
                    readerDiv.style.display = 'block';
                    html5QrcodeScanner = new Html5Qrcode("reader");
                    html5QrcodeScanner.start(
                        { facingMode: "environment" },
                        { fps: 10, qrbox: { width: 250, height: 150 } },
                        (decodedText) => { triggerSell(decodedText); stopScanner(); }
                    ).catch(err => {
                        alert("摄像头启动失败！由于您正在通过自定义内网环境运行，手机访问时请确保浏览器开启了摄像头权限。");
                        readerDiv.style.display = 'none';
                    });
                }
            }

            function stopScanner() {
                if (html5QrcodeScanner) { html5QrcodeScanner.stop().then(() => { document.getElementById('reader').style.display = 'none'; }); }
            }

            function triggerSell(barcode) {
                if (!barcode) return;
                barcode = barcode.trim();
                const index = db.findIndex(item => item.条码 === barcode);
                if (index === -1) { alert(`❌ 货品条码【${barcode}】未在库中找到！`); return; }
                if (db[index].sold_time) { alert(`⚠️ 【${db[index].名称}】之前已核销售出过！`); return; }
                
                db[index].sold_time = new Date().toISOString();
                alert(`🎉 核销成功！\n条码：${barcode}\n品名：${db[index].名称}`);
                refreshUI();
                syncDataToServer();
            }

            function openManualModal() { document.getElementById('manual-modal').style.display = 'flex'; document.getElementById('manual-barcode').focus(); }
            function closeManualModal() { document.getElementById('manual-modal').style.display = 'none'; document.getElementById('manual-barcode').value = ''; }
            function submitManualSell() {
                const barcode = document.getElementById('manual-barcode').value;
                if(!barcode) return;
                triggerSell(barcode);
                closeManualModal();
            }

            function importExcel(input) {
                const file = input.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = function(e) {
                    try {
                        const data = new Uint8Array(e.target.result);
                        const workbook = XLSX.read(data, { type: 'array' });
                        const rawJson = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]);
                        
                        rawJson.forEach(row => {
                            let barcode = row['条码'] ? String(row['条码']).trim() : '';
                            if (!barcode) return;
                            const existingIndex = db.findIndex(item => item.条码 === barcode);
                            if (existingIndex > -1) {
                                if (!db[existingIndex].sold_time) {
                                    db[existingIndex] = { ...db[existingIndex], 名称: row['名称'], 品类: row['品类'], 克重: row['克重'], 标价: row['标价'], 工费: row['工费'] };
                                }
                            } else {
                                db.push({ 条码: barcode, 名称: row['名称'], 品类: row['品类'], 克重: row['克重'], 标价: row['标价'], 工费: row['工费'], sold_time: null });
                            }
                        });
                        alert("📦 Excel 商品数据成功合并洗入云端库！");
                        refreshUI();
                        syncDataToServer();
                    } catch (err) { alert("Excel 解析失败！"); }
                    input.value = '';
                };
                reader.readAsArrayBuffer(file);
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html_content)

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify(read_db())

@app.route('/api/sync', methods=['POST'])
def sync_data():
    client_data = request.json
    write_db(client_data)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
