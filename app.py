import os
import json
import base64
from flask import Flask, request, jsonify, render_template_string, Response
import pandas as pd
from datetime import datetime, timedelta
import urllib.request
from functools import wraps

app = Flask(__name__)
DATA_FILE = 'jewelry_data.json'
STOCKTAKE_FILE = 'stocktake_records.json'

# ================= 🔐 安全登录配置区 (已按要求固化) =================
USER_ACCOUNT = "fenggao"
USER_PASSWORD = "123456" 
# ===================================================================

GH_TOKEN = os.environ.get('GH_TOKEN')
GH_REPO = os.environ.get('GH_REPO')

def check_auth(username, password):
    return username == USER_ACCOUNT and password == USER_PASSWORD

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                '<h1>🔒 峰高珠宝管理系统：未授权访问</h1><p>请输入正确的管理员账号与密码。</p>', 
                401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return []

def save_data(data, filename=DATA_FILE, commit_msg="🔄 数据同步"):
    content_str = json.dumps(data, ensure_ascii=False, indent=4)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content_str)
    if not GH_TOKEN or not GH_REPO: return
    try:
        url = f"https://api.github.com/repos/{GH_REPO}/contents/{filename}"
        sha = None
        try:
            req_get = urllib.request.Request(url)
            req_get.add_header('Authorization', f'token {GH_TOKEN}')
            req_get.add_header('User-Agent', 'Flask-App')
            with urllib.request.urlopen(req_get, timeout=3) as resp:
                sha = json.loads(resp.read().decode('utf-8')).get('sha')
        except: pass
        put_data = {
            "message": commit_msg,
            "content": base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
        }
        if sha: put_data["sha"] = sha
        req_put = urllib.request.Request(url, method='PUT', data=json.dumps(put_data).encode('utf-8'))
        req_put.add_header('Authorization', f'token {GH_TOKEN}')
        req_put.add_header('Content-Type', 'application/json')
        req_put.add_header('User-Agent', 'Flask-App')
        with urllib.request.urlopen(req_put, timeout=5) as resp: print(f"{filename} 同步成功")
    except Exception as e: print(f"同步失败:", str(e))

def load_stocktake_records():
    if os.path.exists(STOCKTAKE_FILE):
        try:
            with open(STOCKTAKE_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return []

def get_bj_today():
    bj_time = datetime.utcnow() + timedelta(hours=8)
    return bj_time.strftime('%Y-%m-%d %H:%M:%S')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>峰高珠宝管理系统 7.2 视觉精调版</title>
    <script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f5f7; margin: 0; padding: 10px; color: #333; }
        .card { background: white; padding: 12px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); margin-bottom: 12px; box-sizing: border-box; }
        
        .sales-dashboard { background: linear-gradient(135deg, #ff9500, #ff3b30); color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(255,59,48,0.2); }
        .sales-dashboard h3 { margin: 0; font-size: 13px; opacity: 0.9; font-weight: normal; }
        .sales-dashboard .count { font-size: 30px; font-weight: bold; margin: 6px 0; font-family: Arial, sans-serif; }
        
        /* 💡 升级：第一组 Tab 基础容器与独立变色设计 (前台操作区) */
        .tab-header-op { display: flex; background: #eef0f3; border-radius: 8px; padding: 2px; margin-bottom: 12px; gap: 2px; }
        .tab-btn-op { flex: 1; text-align: center; padding: 10px 0; font-size: 12px; cursor: pointer; border-radius: 6px; font-weight: bold; color: #555; transition: all 0.2s; }
        
        /* 激活时的雅致色彩区分 */
        #tabOp1.active { background: #fff1f0; color: #e03131; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 2px solid #ff3b30; }
        #tabOp2.active { background: #e6f7ff; color: #096dd9; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 2px solid #007aff; }
        #tabOp3.active { background: #f9f0ff; color: #531dab; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 2px solid #5856d6; }
        
        /* 💡 升级：第二组 Tab 基础容器与独立变色设计 (后台看板区) */
        .tab-header-view { display: flex; background: #eef0f3; border-radius: 8px; padding: 2px; margin-bottom: 12px; gap: 2px; }
        .tab-btn-view { flex: 1; text-align: center; padding: 10px 0; font-size: 12px; cursor: pointer; border-radius: 6px; font-weight: bold; color: #555; transition: all 0.2s; }
        
        /* 激活时的雅致色彩区分 */
        #tabView1.active { background: #f6ffed; color: #389e0d; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 2px solid #34c759; }
        #tabView2.active { background: #fff7e6; color: #d46b08; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 2px solid #ff9500; }
        #tabView3.active { background: #f0f5ff; color: #1d39c4; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 2px solid #2f54eb; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        h2 { margin-top: 0; margin-bottom: 10px; color: #111; font-size: 14px; border-left: 4px solid #ff3b30; padding-left: 6px; }
        .btn { background: #ff3b30; color: white; border: none; padding: 10px; border-radius: 8px; font-size: 13px; width: 100%; cursor: pointer; font-weight: bold; }
        .btn-green { background: #34c759; }
        .btn-blue { background: #007aff; }
        .btn-purple { background: #5856d6; }
        .btn-scan { background: #5856d6; margin-bottom: 8px; }
        
        .action-toggle { display: flex; gap: 10px; margin-bottom: 10px; }
        .action-radio { flex: 1; text-align: center; padding: 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer; background: #fafafa; }
        .action-radio.selected-sale { background: #fff5f5; border-color: #ff3b30; color: #ff3b30; }
        .action-radio.selected-return { background: #f0f7ff; border-color: #007aff; color: #007aff; }

        input[type="file"], input[type="text"], input[type="number"] { width: 100%; padding: 10px; margin: 4px 0 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 14px; }
        
        .table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid #eee; border-radius: 6px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; white-space: nowrap; }
        th, td { padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #f9f9f9; font-weight: 600; color: #666; }
        
        .type-tag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        
        .pagination-container { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; padding-top: 4px; font-size: 12px; color: #555; }
        .page-btn { background: #eef0f3; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight: bold; margin-left: 4px; }
        .page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .page-size-select { padding: 4px; border-radius: 4px; border: 1px solid #ccc; font-size: 12px; }

        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; padding: 15px; box-sizing: border-box; }
        .modal-content { background: white; border-radius: 14px; width: 100%; max-width: 500px; padding: 15px; box-sizing: border-box; box-shadow: 0 4px 15px rgba(0,0,0,0.15); animation: fadeIn 0.2s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        
        .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; }
        .badge-red { background: #ff3b30; }
        .badge-green { background: #34c759; }
        #reader, #stocktakeReader { width: 100%; max-width: 350px; margin: 0 auto; background: #000; border-radius: 8px; overflow: hidden; display: none; }
        .preview-zone { display: none; background: #fff9e6; border: 1px dashed #ff9500; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
    </style>
</head>
<body>

    <div class="sales-dashboard" onclick="toggleSection('todayDetailBox')">
        <h3>💰 今日累计销售额</h3>
        <div class="count" id="todayAmount">¥ 0.00</div>
        <div id="todayCount" style="font-size: 12px; opacity: 0.9;">今天已成功卖出: 0 件货品</div>
    </div>

    <div class="card" id="todayDetailBox" style="display:none;">
        <h2>🛍️ 今日卖出商品明细</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr style="background: #fff5f5;">
                        <th>条码/标签</th><th>货品名称</th><th>品类</th><th>金重(g)</th><th>实际成交售价</th>
                    </tr>
                </thead>
                <tbody id="todaySalesBody"></tbody>
            </table>
        </div>
        <div class="pagination-container" id="pagerToday"></div>
    </div>

    <div class="card">
        <div class="tab-header-op">
            <div class="tab-btn-op active" id="tabOp1" onclick="switchTab('Op', 1)">🛒 柜台商品销售</div>
            <div class="tab-btn-op" id="tabOp2" onclick="switchTab('Op', 2)">📦 批量货品入库</div>
            <div class="tab-btn-op" id="tabOp3" onclick="switchTab('Op', 3)">🔍 手机极速盘点</div>
        </div>
        
        <div class="tab-content active" id="contentOp1">
            <button class="btn btn-scan" id="scanBtn" onclick="toggleScanner('normal')">📷 开启摄像头扫码</button>
            <div id="reader"></div>
            
            <div style="font-size: 12px; color: #666; font-weight: bold; margin-top:6px;">请选择当前柜台操作：</div>
            <div class="action-toggle">
                <div class="action-radio selected-sale" id="modeSale" onclick="setMode('sale')">🛍️ 正常销售记账</div>
                <div class="action-radio" id="modeReturn" onclick="setMode('return')">🔄 办理退货核销</div>
            </div>

            <div style="font-size: 12px; color: #666; font-weight: bold;" id="barcodeTitle">第一步：输入或扫描货品条码</div>
            <input type="text" id="barcodeInput" placeholder="请扫码或在此手动输入条码/货号">
            
            <div id="priceInputArea">
                <div style="font-size: 12px; color: #ff3b30; font-weight: bold;">第二步：实收客户金额 (实际售价 ¥)</div>
                <input type="number" id="actualPriceInput" step="0.01" placeholder="请输入最终实收总价">
            </div>
            
            <button class="btn" id="submitOpBtn" onclick="executeOperation()">💰 确认销售并记账</button>
        </div>
        
        <div class="tab-content" id="contentOp2">
            <input type="file" id="excelFile" accept=".xlsx, .xls">
            <button class="btn btn-green" onclick="uploadExcel()">选择并解析新货 Excel</button>
        </div>

        <div class="tab-content" id="contentOp3">
            <div id="stocktakeSetup">
                <button class="btn btn-purple" onclick="startLocalStocktake()">🟢 开启手机离线盘点</button>
            </div>

            <div id="stocktakeActiveZone" style="display:none;">
                <div style="background:#f5f0ff; padding:10px; border-radius:8px; margin-bottom:10px; font-size:13px;">
                    <div>📊 盘点进度：<b id="stProgressText" style="color:#5856d6; font-size:16px;">0 / 0</b></div>
                </div>

                <button class="btn btn-scan" id="stocktakeScanBtn" onclick="toggleScanner('stocktake')">📷 开启盘点专用扫码</button>
                <div id="stocktakeReader"></div>

                <input type="text" id="stocktakeBarcodeInput" placeholder="若摄像头不方便，可在此手输条码" onkeydown="if(event.keyCode==13)manualStocktakeCheck()">

                <h2 style="border-left-color: #5856d6; color:#5856d6; margin-top:15px;">🔍 尚未盘到的货品 (待寻找名单)</h2>
                <div class="table-container" style="max-height: 250px; background: #fff;">
                    <table>
                        <thead>
                            <tr style="background:#f5f0ff;"><th>条码</th><th>货品名称</th><th>品类</th><th>金重</th></tr>
                        </thead>
                        <tbody id="stocktakeMissingBody"></tbody>
                    </table>
                </div>

                <div style="display:flex; gap:10px; margin-top:15px;">
                    <button class="btn btn-green" style="flex:1;" onclick="finishStocktakeSubmit()">🏁 结束盘点并保存记录</button>
                    <button class="btn" style="background:#666; width:80px;" onclick="cancelStocktakeReset()">放弃</button>
                </div>
            </div>
        </div>
    </div>

    <div class="preview-zone" id="previewZone">
        <h2 style="border-left-color: #ff9500; font-size:13px;">⚠️ 待入库新货安全预览</h2>
        <div class="table-container" style="max-height: 150px; background: white;">
            <table>
                <thead>
                    <tr><th>条码</th><th>货品名称</th><th>品类</th><th>金重</th></tr>
                </thead>
                <tbody id="previewBody"></tbody>
            </table>
        </div>
        <div style="display:flex; gap:8px; margin-top:8px;">
            <button class="btn btn-green" style="padding:8px; font-size:12px;" onclick="confirmImport()">确认锁库存上架</button>
            <button class="btn" style="background:#666; padding:8px; font-size:12px;" onclick="cancelImport()">取消</button>
        </div>
    </div>

    <div class="card">
        <div class="tab-header-view">
            <div class="tab-btn-view active" id="tabView1" onclick="switchTab('View', 1)">🟢 店内当前在售存货</div>
            <div class="tab-btn-view" id="tabView2" onclick="switchTab('View', 2)">📜 历史已售出累计账本</div>
            <div class="tab-btn-view" id="tabView3" onclick="switchTab('View', 3)">📋 历史盘点报告</div>
        </div>
        
        <div class="tab-content active" id="contentView1">
            <div class="table-container">
                <table>
                    <thead>
                        <tr><th>条码/标签</th><th>货品名称</th><th>品类</th><th>金重(g)</th><th>状态</th></tr>
                    </thead>
                    <tbody id="inventoryBody"></tbody>
                </table>
            </div>
            <div class="pagination-container" id="pagerInventory"></div>
        </div>
        
        <div class="tab-content" id="contentView2">
            <div class="table-container">
                <table>
                    <thead>
                        <tr style="background: #fdf2f2;">
                            <th>条码/标签</th><th>货品名称</th><th>品类</th><th>金重(g)</th><th style="color: #ff3b30;">成交售价</th><th>售出日期</th>
                        </tr>
                    </thead>
                    <tbody id="soldBody"></tbody>
                </table>
            </div>
            <div class="pagination-container" id="pagerSold"></div>
        </div>

        <div class="tab-content" id="contentView3">
            <div class="table-container">
                <table>
                    <thead>
                        <tr style="background: #f0f7ff;">
                            <th>盘点时间</th><th>账面应有</th><th>实盘抓到</th><th>盘亏(丢失)</th><th>亏损详细</th>
                        </tr>
                    </thead>
                    <tbody id="stocktakeHistoryBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="detailModal">
        <div class="modal-content">
            <h2 style="border-left-color: #ff3b30; font-size:15px; margin-bottom:12px;">❌ 盘亏缺失货品详细名单</h2>
            <div class="table-container" style="max-height: 280px;">
                <table style="width:100%;">
                    <thead>
                        <tr style="background:#fff0f0;"><th>条码/货号</th><th>货品名称</th><th>品类</th><th>金重</th></tr>
                    </thead>
                    <tbody id="modalTableBody"></tbody>
                </table>
            </div>
            <button class="btn btn-blue" style="margin-top:15px;" onclick="closeModal()">我知道了，关闭窗口</button>
        </div>
    </div>

    <script>
        let html5QrcodeScanner = null;
        let tempParsedData = null;
        let currentMode = 'sale';
        
        let backendActiveData = [];
        let backendSoldData = [];
        let backendTodayData = [];
        let localStocktakeItems = [];

        let pagerConfig = {
            inventory: { currentPage: 1, pageSize: 10 },
            sold: { currentPage: 1, pageSize: 10 },
            today: { currentPage: 1, pageSize: 10 }
        };

        window.onload = loadAllData;

        function getTypeTagHtml(typeStr) {
            const val = String(typeStr || '').trim();
            let bg = '#f1f3f5', color = '#495057';
            
            if (val.includes('足金') || val.includes('黄金')) { bg = '#fef6e0'; color = '#b27b00'; }
            else if (val.includes('K金') || val.includes('18K')) { bg = '#faecea'; color = '#be5a4d'; }
            else if (val.includes('钻石') || val.includes('铂金')) { bg = '#eaf2f8'; color = '#2e6da4'; }
            else if (val.includes('翡翠') || val.includes('玉')) { bg = '#eafaf1'; color = '#278946'; }
            else if (val.includes('银')) { bg = '#f3f4f7'; color = '#6c757d'; }
            
            return `<span class="type-tag" style="background: ${bg}; color: ${color};">${val}</span>`;
        }

        function switchTab(moduleName, index) {
            const lower = moduleName.toLowerCase();
            document.querySelectorAll(`.tab-btn-${lower}`).forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll(`[id^="content${moduleName}"]`).forEach(content => content.classList.remove('active'));
            
            document.getElementById(`tab${moduleName}${index}`).classList.add('active');
            document.getElementById(`content${moduleName}${index}`).classList.add('active');
            
            if(moduleName === 'View' && index === 3) { loadStocktakeHistory(); }
        }

        function toggleSection(id) {
            const el = document.getElementById(id);
            el.style.display = (el.style.display === 'none') ? 'block' : 'none';
        }

        function setMode(mode) {
            currentMode = mode;
            const modeSale = document.getElementById('modeSale');
            const modeReturn = document.getElementById('modeReturn');
            const priceInputArea = document.getElementById('priceInputArea');
            const submitOpBtn = document.getElementById('submitOpBtn');

            if (mode === 'sale') {
                modeSale.classList.add('selected-sale'); modeReturn.classList.remove('selected-return');
                priceInputArea.style.display = 'block'; submitOpBtn.innerText = '💰 确认销售并记账'; submitOpBtn.className = 'btn';
            } else {
                modeSale.classList.remove('selected-sale'); modeReturn.classList.add('selected-return');
                priceInputArea.style.display = 'none'; submitOpBtn.innerText = '🔄 确认退货并恢复库存'; submitOpBtn.className = 'btn btn-blue';
            }
        }

        function loadAllData() {
            fetch('/api/inventory')
                .then(res => res.json())
                .then(res => {
                    backendActiveData = res.active || [];
                    backendSoldData = res.sold || [];
                    backendTodayData = res.today_list || [];

                    document.getElementById('todayAmount').innerText = '¥ ' + res.today_money.toFixed(2);
                    document.getElementById('todayCount').innerText = '今天已成功卖出: ' + res.today_count + ' 件货品';

                    renderPagedTable('inventory');
                    renderPagedTable('sold');
                    renderPagedTable('today');
                });
        }

        function renderPagedTable(key) {
            const config = pagerConfig[key];
            let data = [];
            let tbody = null;
            let pagerDiv = null;

            if (key === 'inventory') { data = backendActiveData; tbody = document.getElementById('inventoryBody'); pagerDiv = document.getElementById('pagerInventory'); }
            else if (key === 'sold') { data = backendSoldData; tbody = document.getElementById('soldBody'); pagerDiv = document.getElementById('pagerSold'); }
            else if (key === 'today') { data = backendTodayData; tbody = document.getElementById('todaySalesBody'); pagerDiv = document.getElementById('pagerToday'); }

            tbody.innerHTML = '';
            
            if(data.length === 0) {
                const cols = key === 'sold' ? 6 : 5;
                tbody.innerHTML = `<tr><td colspan="${cols}" style="text-align:center; color:#999; padding:15px;">暂无对应账目记录</td></tr>`;
                pagerDiv.innerHTML = '';
                return;
            }

            let totalItems = data.length;
            let totalPages = Math.ceil(totalItems / config.pageSize);
            if (config.currentPage > totalPages) config.currentPage = totalPages;
            if (config.currentPage < 1) config.currentPage = 1;

            let startIndex = (config.currentPage - 1) * config.pageSize;
            let endIndex = Math.min(startIndex + config.pageSize, totalItems);
            let pageData = data.slice(startIndex, endIndex);

            pageData.forEach(item => {
                const tagHtml = getTypeTagHtml(item.category || '其他');
                if (key === 'inventory') {
                    tbody.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${tagHtml}</td><td>${item.weight}g</td><td style="color:#34c759;font-weight:bold;">在售</td></tr>`;
                } else if (key === 'sold') {
                    tbody.innerHTML += `<tr><td><del>${item.code}</del></td><td>${item.name}</td><td>${tagHtml}</td><td>${item.weight}g</td><td style="color:#ff3b30; font-weight:bold;">¥ ${item.sold_price}</td><td>${item.sold_date}</td></tr>`;
                } else if (key === 'today') {
                    tbody.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${tagHtml}</td><td>${item.weight}g</td><td style="color:#ff3b30; font-weight:bold;">¥ ${item.sold_price}</td></tr>`;
                }
            });

            pagerDiv.innerHTML = `
                <div>
                    显示 ${startIndex + 1}-${endIndex} / 共 ${totalItems} 条 
                    <select class="page-size-select" onchange="changePageSize('${key}', this.value)">
                        <option value="10" ${config.pageSize==10?'selected':''}>10行/页</option>
                        <option value="20" ${config.pageSize==20?'selected':''}>20行/页</option>
                        <option value="50" ${config.pageSize==50?'selected':''}>50行/页</option>
                        <option value="100" ${config.pageSize==100?'selected':''}>100行/页</option>
                    </select>
                </div>
                <div>
                    <button class="page-btn" ${config.currentPage==1?'disabled':''} onclick="goToPage('${key}', ${config.currentPage - 1})">◀</button>
                    <span style="margin: 0 4px; font-weight:bold;">${config.currentPage} / ${totalPages}</span>
                    <button class="page-btn" ${config.currentPage==totalPages?'disabled':''} onclick="goToPage('${key}', ${config.currentPage + 1})">▶</button>
                </div>
            `;
        }

        function goToPage(key, page) { pagerConfig[key].currentPage = page; renderPagedTable(key); }
        function changePageSize(key, size) { pagerConfig[key].pageSize = parseInt(size); pagerConfig[key].currentPage = 1; renderPagedTable(key); }

        function startLocalStocktake() {
            fetch('/api/inventory')
                .then(res => res.json())
                .then(res => {
                    if(!res.active || res.active.length === 0) { alert("当前店内在售库存为空，无需盘点！"); return; }
                    localStocktakeItems = res.active.map(item => { return { ...item, scanned: false }; });
                    document.getElementById('stocktakeSetup').style.display = 'none';
                    document.getElementById('stocktakeActiveZone').style.display = 'block';
                    renderStocktakeMissingList();
                });
        }

        function renderStocktakeMissingList() {
            const missingBody = document.getElementById('stocktakeMissingBody');
            missingBody.innerHTML = '';
            const missingItems = localStocktakeItems.filter(item => !item.scanned);
            const scannedCount = localStocktakeItems.filter(item => item.scanned).length;
            
            document.getElementById('stProgressText').innerText = `${scannedCount}已盘 / ${localStocktakeItems.length}账面总数`;

            if(missingItems.length === 0) {
                missingBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#34c759; font-weight:bold; padding:20px;">🎉 账面所有货品已盘齐！</td></tr>';
                return;
            }
            missingItems.forEach(item => {
                missingBody.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${getTypeTagHtml(item.category)}</td><td>${item.weight}g</td></tr>`;
            });
        }

        function processStocktakeCode(code) {
            const codeStr = String(code).trim();
            let found = false;
            for(let i=0; i<localStocktakeItems.length; i++) {
                if(String(localStocktakeItems[i].code).trim() === codeStr) {
                    if(localStocktakeItems[i].scanned) { alert(`条码 [${codeStr}] 刚才已经盘过了。`); } 
                    else { localStocktakeItems[i].scanned = true; }
                    found = true; break;
                }
            }
            if(!found) { alert(`⚠️ 警告：条码 [${codeStr}] 不在系统在售存货账本中！`); }
            renderStocktakeMissingList();
        }

        function manualStocktakeCheck() {
            const inputEl = document.getElementById('stocktakeBarcodeInput');
            if(inputEl.value.trim()) { processStocktakeCode(inputEl.value.trim()); inputEl.value = ''; }
        }

        function finishStocktakeSubmit() {
            const missingItems = localStocktakeItems.filter(item => !item.scanned);
            const scannedItems = localStocktakeItems.filter(item => item.scanned);
            
            if(!confirm(`确认结束盘点吗？\n✅ 实盘：${scannedItems.length}件\n❌ 盘亏：${missingItems.length}件`)) return;

            const report = {
                total_expected: localStocktakeItems.length,
                total_found: scannedItems.length,
                total_missing: missingItems.length,
                missing_details: missingItems.map(i => ({ code: i.code, name: i.name, category: i.category || '其他', weight: i.weight }))
            };

            fetch('/api/stocktake/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(report)
            })
            .then(res => res.json())
            .then(res => { alert(res.msg); cancelStocktakeReset(); });
        }

        function cancelStocktakeReset() {
            localStocktakeItems = []; stopScanner();
            document.getElementById('stocktakeActiveZone').style.display = 'none';
            document.getElementById('stocktakeSetup').style.display = 'block';
        }

        function loadStocktakeHistory() {
            fetch('/api/stocktake/history')
                .then(res => res.json())
                .then(data => {
                    const tbody = document.getElementById('stocktakeHistoryBody');
                    tbody.innerHTML = '';
                    if(data.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#999; padding:12px;">暂无历史盘点报告</td></tr>';
                        return;
                    }
                    data.reverse().forEach((r, idx) => {
                        const badgeClass = r.total_missing > 0 ? 'badge-red' : 'badge-green';
                        
                        let actionBtnHtml = '-';
                        if(r.total_missing > 0) {
                            actionBtnHtml = `<button class="page-btn" style="background:#2f54eb; color:white; font-size:11px; padding:3px 7px;" onclick="showMissingDetailPopup(${idx}, ${data.length})">🔍 查看明细</button>`;
                        }

                        tbody.innerHTML += `<tr>
                            <td>${r.timestamp}</td>
                            <td>${r.total_expected} 件</td>
                            <td>${r.total_found} 件</td>
                            <td><span class="badge ${badgeClass}">${r.total_missing} 件</span></td>
                            <td>${actionBtnHtml}</td>
                        </tr>`;
                    });
                });
        }

        function showMissingDetailPopup(reverseIdx, totalLength) {
            fetch('/api/stocktake/history')
                .then(res => res.json())
                .then(data => {
                    const realIdx = totalLength - 1 - reverseIdx;
                    const report = data[realIdx];
                    
                    const mbody = document.getElementById('modalTableBody');
                    mbody.innerHTML = '';
                    
                    const details = report.missing_details || [];
                    if(details.length === 0) {
                        mbody.innerHTML = `<tr><td colspan="4" style="color:#999; text-align:center;">该报告未录入特征数据</td></tr>`;
                    } else {
                        details.forEach(item => {
                            mbody.innerHTML += `<tr>
                                <td><b>${item.code}</b></td>
                                <td>${item.name}</td>
                                <td>${getTypeTagHtml(item.category)}</td>
                                <td>${item.weight}g</td>
                            </tr>`;
                        });
                    }
                    document.getElementById('detailModal').style.display = 'flex';
                });
        }

        function closeModal() { document.getElementById('detailModal').style.display = 'none'; }

        function toggleScanner(type) {
            const isStocktake = (type === 'stocktake');
            const readerId = isStocktake ? 'stocktakeReader' : 'reader';
            const btnId = isStocktake ? 'stocktakeScanBtn' : 'scanBtn';
            const readerDiv = document.getElementById(readerId);
            const scanBtn = document.getElementById(btnId);
            
            if (readerDiv.style.display === 'block') { stopScanner(); } else {
                readerDiv.style.display = 'block'; scanBtn.innerText = '🛑 关闭扫码器';
                html5QrcodeScanner = new Html5Qrcode(readerId);
                html5QrcodeScanner.start(
                    { facingMode: "environment" }, { fps: 12, qrbox: { width: 220, height: 220 } },
                    (decodedText) => {
                        if(isStocktake) { processStocktakeCode(decodedText); } 
                        else { document.getElementById('barcodeInput').value = decodedText; stopScanner(); }
                    }, () => {}
                ).catch(() => { alert("未检测到摄像头授权。"); stopScanner(); });
            }
        }

        function stopScanner() {
            if (html5QrcodeScanner) {
                html5QrcodeScanner.stop().then(() => {
                    document.getElementById('reader').style.display = 'none';
                    document.getElementById('stocktakeReader').style.display = 'none';
                    document.getElementById('scanBtn').innerText = '📷 开启摄像头扫码';
                    document.getElementById('stocktakeScanBtn').innerText = '📷 开启盘点专用扫码';
                }).catch(() => {});
            }
        }

        function uploadExcel() {
            const fileInput = document.getElementById('excelFile');
            if (!fileInput.files[0]) { alert('请选择 Excel 文件！'); return; }
            const formData = new FormData(); formData.append('file', fileInput.files[0]);

            fetch('/api/parse_preview', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(res => {
                    if (res.success) {
                        tempParsedData = res.data;
                        const pbody = document.getElementById('previewBody'); pbody.innerHTML = '';
                        res.data.forEach(item => {
                            pbody.innerHTML += `<tr><td>${item.code}</td><td>${item.name}</td><td>${item.category}</td><td>${item.weight}g</td></tr>`;
                        });
                        document.getElementById('previewZone').style.display = 'block';
                    } else { alert('解析失败：' + res.msg); }
                });
        }

        function confirmImport() {
            if (!tempParsedData) return;
            fetch('/api/confirm_save', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ data: tempParsedData })
            })
            .then(res => res.json()).then(res => { alert(res.msg); cancelImport(); loadAllData(); });
        }

        function cancelImport() { tempParsedData = null; document.getElementById('previewZone').style.display = 'none'; document.getElementById('excelFile').value = ''; }

        function executeOperation() {
            const code = document.getElementById('barcodeInput').value.trim();
            if (!code) { alert('请先输入货品条码！'); return; }

            if (currentMode === 'sale') {
                const actualPrice = document.getElementById('actualPriceInput').value.trim();
                if (!actualPrice) { alert('请输入实收金额！'); return; }
                fetch('/api/checkout', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: code, sold_price: actualPrice })
                })
                .then(res => res.json()).then(res => { alert(res.msg); if (res.success) { document.getElementById('barcodeInput').value = ''; document.getElementById('actualPriceInput').value = ''; loadAllData(); } });
            } else {
                if (!confirm(`确认要为条码 [${code}] 办理退货核销吗？`)) return;
                fetch('/api/return_item', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: code })
                })
                .then(res => res.json()).then(res => { alert(res.msg); if (res.success) { document.getElementById('barcodeInput').value = ''; loadAllData(); } });
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
@requires_auth
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/inventory', methods=['GET'])
@requires_auth
def get_inventory():
    all_data = load_data()
    today_str = get_bj_today().split(' ')[0]
    active_list, sold_list, today_sales_list = [], [], []
    today_money = 0.0
    
    for item in all_data:
        status = item.get('status', '在售')
        if status == '已售出':
            sold_list.append(item)
            if item.get('sold_date') == today_str:
                today_sales_list.append(item)
                try: today_money += float(item.get('sold_price', 0) or 0)
                except: pass
        else: active_list.append(item)
            
    return jsonify({
        'active': active_list, 'sold': sold_list,
        'today_count': len(today_sales_list), 'today_money': today_money, 'today_list': today_sales_list
    })

@app.route('/api/parse_preview', methods=['POST'])
@requires_auth
def parse_preview():
    if 'file' not in request.files: return jsonify({'success': False, 'msg': '未找到文件'})
    file = request.files['file']
    if file.filename == '': return jsonify({'success': False, 'msg': '文件名为空'})
    try:
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        code_col, name_col, cate_col, weight_col = None, None, None, None
        for col in df.columns:
            low_col = col.lower()
            if any(k in low_col for k in ['条码', '标签', '编码', '码', 'code']): code_col = col
            elif any(k in low_col for k in ['货品名称', '名称', '款式', 'name']): name_col = col
            elif any(k in low_col for k in ['品类', '类型', '分类', 'category']): cate_col = col
            elif any(k in low_col for k in ['克重', '金重', '重量', 'weight']): weight_col = col

        if not code_col: return jsonify({'success': False, 'msg': '未找到条码列'})

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
            preview_list.append({"code": code_str, "name": name_val, "category": cate_val, "weight": weight_val})
        return jsonify({'success': True, 'data': preview_list})
    except Exception as e: return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/confirm_save', methods=['POST'])
@requires_auth
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
                "weight": item['weight'], "status": "在售"
            })
            existing_codes.add(item['code'])
            added_count += 1
    save_data(current_data, commit_msg=f"🎉 成功入库 {added_count} 件新品")
    return jsonify({'success': True, 'msg': f'🎉 成功入库 {added_count} 件新品！'})

@app.route('/api/checkout', methods=['POST'])
@requires_auth
def checkout():
    req = request.get_json() or {}
    code = str(req.get('code', '')).strip()
    sold_price = str(req.get('sold_price', '')).strip()
    current_data = load_data()
    today_str = get_bj_today().split(' ')[0]
    for item in current_data:
        if str(item['code']).strip() == code:
            if item['status'] == '已售出': return jsonify({'success': False, 'msg': '⚠️ 该货品已售出'})
            item['status'] = '已售出'
            item['sold_date'] = today_str
            item['sold_price'] = sold_price
            save_data(current_data, commit_msg=f"🛍 货品 {code} 售出记账")
            return jsonify({'success': True, 'msg': '🛍 销售成功！'})
    return jsonify({'success': False, 'msg': '❌ 未找到该货品'})

@app.route('/api/return_item', methods=['POST'])
@requires_auth
def return_item():
    req = request.get_json() or {}
    code = str(req.get('code', '')).strip()
    current_data = load_data()
    for item in current_data:
        if str(item['code']).strip() == code:
            if item['status'] == '在售': return jsonify({'success': False, 'msg': '⚠️ 该货品当前在售'})
            item['status'] = '在售'
            if 'sold_date' in item: del item['sold_date']
            if 'sold_price' in item: del item['sold_price']
            save_data(current_data, commit_msg=f"🔄 货品 {code} 退货核销恢复库存")
            return jsonify({'success': True, 'msg': '🔄 退货核销成功！'})
    return jsonify({'success': False, 'msg': '❌ 未找到记录'})

@app.route('/api/stocktake/submit', methods=['POST'])
@requires_auth
def stocktake_submit():
    report = request.get_json() or {}
    report['timestamp'] = get_bj_today()
    history = load_stocktake_records()
    history.append(report)
    save_data(history, filename=STOCKTAKE_FILE, commit_msg=f"📋 上传新盘点报告 - 盘亏 {report['total_missing']} 件")
    return jsonify({'success': True, 'msg': '🏁 盘点报告已成功上传！'})

@app.route('/api/stocktake/history', methods=['GET'])
@requires_auth
def stocktake_history():
    if GH_TOKEN and GH_REPO and not os.path.exists(STOCKTAKE_FILE):
        try:
            url = f"https://api.github.com/repos/{GH_REPO}/contents/{STOCKTAKE_FILE}"
            req = urllib.request.Request(url)
            req.add_header('Authorization', f'token {GH_TOKEN}')
            req.add_header('User-Agent', 'Flask-App')
            with urllib.request.urlopen(req, timeout=3) as resp:
                res_data = json.loads(resp.read().decode('utf-8'))
                content = base64.b64decode(res_data['content']).decode('utf-8')
                with open(STOCKTAKE_FILE, 'w', encoding='utf-8') as f: f.write(content)
        except: pass
    return jsonify(load_stocktake_records())

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
