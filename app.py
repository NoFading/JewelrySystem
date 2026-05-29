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

# ================= 🔐 多账号密码配置区 =================
ACCOUNTS = {
    "fenggao": "123456",  # 正式主账号
    "test": "123456"      # 测试账号
}
# ===================================================================

GH_TOKEN = os.environ.get('GH_TOKEN')
GH_REPO = os.environ.get('GH_REPO')

def check_auth(username, password):
    return username in ACCOUNTS and ACCOUNTS[username] == password

def get_current_user():
    auth = request.authorization
    if auth and auth.username in ACCOUNTS:
        return auth.username
    return "guest"

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
            with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return []

def save_data(data, filename=DATA_FILE, commit_msg="🔄 数据同步"):
    content_str = json.dumps(data, ensure_ascii=False, indent=4)
    with open(filename, 'w', encoding='utf-8') as f: f.write(content_str)
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

def get_bj_date_nodash():
    bj_time = datetime.utcnow() + timedelta(hours=8)
    return bj_time.strftime('%Y-%m-%d')

# ================= 🛠️ API 后端核心升级区 =================

@app.route('/')
@requires_auth
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/inventory', methods=['GET'])
@requires_auth
def get_inventory():
    all_items = load_data()
    today_str = get_bj_date_nodash()
    
    # 严格区分在售与已售商品
    active_list = [item for item in all_items if item.get('status', '在售') == '在售']
    sold_list = [item for item in all_items if item.get('status') == '已售']
    
    # 筛选今日销售独立看板数据
    today_sales_list = []
    today_money = 0.0
    for item in sold_list:
        s_date = item.get('sold_date', '')
        if s_date and s_date.startswith(today_str):
            today_sales_list.append(item)
            try:
                today_money += float(item.get('sold_price', 0))
            except: pass

    return jsonify({
        "active": active_list,
        "sold": sold_list,
        "today_list": today_sales_list,
        "today_count": len(today_sales_list),
        "today_money": today_money
    })

@app.route('/api/parse_preview', methods=['POST'])
@requires_auth
def parse_preview():
    if 'file' not in request.files:
        return jsonify({"success": False, "msg": "未找到上传的文件"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "msg": "未选择任何有效文件"})
    
    try:
        df = pd.read_excel(file, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 建立灵活的列头联想映射映射字典
        mapping = {}
        for col in df.columns:
            if '条码' in col or '货号' in col: mapping['code'] = col
            elif '名称' in col or '货品' in col: mapping['name'] = col
            elif '品类' in col or '分类' in col: mapping['category'] = col
            elif '克量' in col or '金重' in col or '重量' in col: mapping['weight'] = col  # 优先匹配“克量”与“金重”
            elif '标价' in col: mapping['price'] = col  # 解析时严格将表格中的“标价”映射为商品的 price 属性
            elif '工费' in col: mapping['fee'] = col

        # 检查核心列满足度 (至少要识别出条码、货名、品类、金重/克量)
        required = ['code', 'name', 'category', 'weight']
        missing = [r for r in required if r not in mapping]
        if missing:
            return jsonify({"success": False, "msg": f"Excel缺少关键核心列头映射，无法识别。"})

        parsed_data = []
        for _, row in df.iterrows():
            code_val = row.get(mapping['code'], '')
            if pd.isna(code_val) or str(code_val).strip() == '':
                continue  # 忽略没有条码的空行
                
            name_val = row.get(mapping['name'], '')
            cat_val = row.get(mapping['category'], '其他')
            weight_val = row.get(mapping['weight'], '0')
            
            # 读取表格中对应的标签“标价”
            price_val = row.get(mapping.get('price'), '0') if 'price' in mapping else '0'
            fee_val = row.get(mapping.get('fee'), '0') if 'fee' in mapping else '0'

            # 格式清洗归一化
            if pd.isna(name_val): name_val = "未命名货品"
            if pd.isna(price_val) or str(price_val).strip() == '': price_val = "0"
            if pd.isna(fee_val) or str(fee_val).strip() == '': fee_val = "0"
            
            # 入库解析阶段：只保留商品标签属性“price(标价)”，绝不在此阶段产生任何售价数据，状态保持“在售”
            parsed_data.append({
                "code": str(code_val).strip(),
                "name": str(name_val).strip(),
                "category": str(cat_val).strip(),
                "weight": str(weight_val).strip(),
                "price": str(price_val).strip(),
                "fee": str(fee_val).strip(),
                "status": "在售"
            })
            
        return jsonify({"success": True, "data": parsed_data})
    except Exception as e:
        return jsonify({"success": False, "msg": f"解析异常: {str(e)}"})

@app.route('/api/confirm_save', methods=['POST'])
@requires_auth
def confirm_save():
    new_items = request.json.get('data', [])
    if not new_items:
        return jsonify({"success": False, "msg": "队列为空，无数据上架"})
        
    all_data = load_data()
    
    # 为了支持重复条码覆盖更新，我们建立一个以条码(code)为 Key 的字典
    data_dict = {item['code']: item for item in all_data}
    
    added_count = 0
    updated_count = 0
    
    for item in new_items:
        code = item['code']
        if code in data_dict:
            # 如果条码重复：清除旧的销售数据，用新导入的数据彻底覆盖它（实现更新）
            data_dict[code] = item
            updated_count += 1
        else:
            # 如果是全新条码：直接录入
            data_dict[code] = item
            added_count += 1
            
    # 将字典数据重新转回列表
    all_data = list(data_dict.values())
            
    if added_count > 0 or updated_count > 0:
        msg_detail = f"📥 批量处理完成：新上架 {added_count} 件"
        if updated_count > 0:
            msg_detail += f"，覆盖更新重复条码 {updated_count} 件"
        
        save_data(all_data, commit_msg=msg_detail)
        return jsonify({"success": True, "msg": f"{msg_detail}！"})
    else:
        return jsonify({"success": False, "msg": "未检测到任何有效数据变更"})

@app.route('/api/checkout', methods=['POST'])
@requires_auth
def api_checkout():
    code = request.json.get('code', '').strip()
    sold_price = request.json.get('sold_price', '').strip()
    all_data = load_data()
    
    found = False
    for item in all_data:
        if str(item['code']) == code and item.get('status', '在售') == '在售':
            item['status'] = '已售'
            item['sold_price'] = sold_price  # 只有在正式售出结账时，才会写入“实际售价”
            bj_time = datetime.utcnow() + timedelta(hours=8)
            item['sold_date'] = bj_time.strftime('%Y-%m-%d %H:%M:%S')
            found = True
            break
            
    if found:
        save_data(all_data, commit_msg=f"💰 销售出库账目更新: 条码 {code}")
        return jsonify({"success": True, "msg": "销售记账成功！该商品已转入历史账本。"})
    return jsonify({"success": False, "msg": "未在店内【在售】存货清单中找到此条码！"})

@app.route('/api/return_item', methods=['POST'])
@requires_auth
def api_return_item():
    code = request.json.get('code', '').strip()
    all_data = load_data()
    
    found = False
    for item in all_data:
        if str(item['code']) == code and item.get('status') == '已售':
            item['status'] = '在售'
            if 'sold_price' in item: del item['sold_price']  # 退货核销时，彻底擦除售价
            if 'sold_date' in item: del item['sold_date']
            found = True
            break
            
    if found:
        save_data(all_data, commit_msg=f"🔄 办理退货核销，恢复库存: 条码 {code}")
        return jsonify({"success": True, "msg": "退货完成！货品已安全退回到店内在售存货中。"})
    return jsonify({"success": False, "msg": "在历史【已售】记录里未查到当前条码，无法办理退货。"})

@app.route('/api/stocktake/submit', methods=['POST'])
@requires_auth
def stocktake_submit():
    report = request.json
    bj_time = datetime.utcnow() + timedelta(hours=8)
    report['timestamp'] = bj_time.strftime('%Y-%m-%d %H:%M:%S')
    
    records = load_stocktake_records()
    records.insert(0, report) # 最新报告放在最上面
    save_data(records, filename=STOCKTAKE_FILE, commit_msg="📋 保存极速盘点报告")
    return jsonify({"success": True, "msg": "盘点数据已成功存档至服务器！"})

@app.route('/api/stocktake/history', methods=['GET'])
@requires_auth
def stocktake_history():
    return jsonify(load_stocktake_records())

# ================= 🎨 前端看板核心优化升级 =================
# 此处保持您原有的 HTML_TEMPLATE 变量定义...
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>峰高珠宝管理系统 7.7 核心数据分离版</title>
    <script src="https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f5f7; margin: 0; padding: 10px; color: #333; }
        .card { background: white; padding: 12px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); margin-bottom: 12px; box-sizing: border-box; }
        
        .sales-dashboard { background: linear-gradient(135deg, #ff9500, #ff3b30); color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(255,59,48,0.2); cursor: pointer; }
        .sales-dashboard h3 { margin: 0; font-size: 13px; opacity: 0.9; font-weight: normal; }
        .sales-dashboard .count { font-size: 30px; font-weight: bold; margin: 6px 0; font-family: Arial, sans-serif; }
        
        .tab-header-op { display: flex; background: #eef0f3; border-radius: 8px; padding: 2px; margin-bottom: 12px; gap: 2px; }
        .tab-btn-op { flex: 1; text-align: center; padding: 10px 0; font-size: 12px; cursor: pointer; border-radius: 6px; font-weight: bold; color: #555; transition: all 0.2s; }
        
        #tabOp1.active { background: #fff1f0; color: #e03131; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 2px solid #ff3b30; }
        #tabOp2.active { background: #e6f7ff; color: #096dd9; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 2px solid #007aff; }
        #tabOp3.active { background: #f9f0ff; color: #531dab; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 2px solid #5856d6; }
        
        .tab-header-view { display: flex; background: #eef0f3; border-radius: 8px; padding: 2px; margin-bottom: 12px; gap: 2px; }
        .tab-btn-view { flex: 1; text-align: center; padding: 10px 0; font-size: 12px; cursor: pointer; border-radius: 6px; font-weight: bold; color: #555; transition: all 0.2s; }
        
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
        
        .search-box { background: #fff; border: 2px solid #ff3b30 !important; margin-bottom: 8px !important; font-weight: bold; }
        .search-box.green-border { border-color: #34c759 !important; }
        .search-box.orange-border { border-color: #ff9500 !important; }
        .search-box.purple-border { border-color: #5856d6 !important; }

        .table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid #eee; border-radius: 6px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; white-space: nowrap; }
        th, td { padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #f9f9f9; font-weight: 600; color: #666; }
        
        .type-tag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .pagination-container { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; padding-top: 4px; font-size: 12px; color: #555; }
        .page-btn { background: #eef0f3; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight: bold; margin-left: 4px; }
        .page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; padding: 15px; box-sizing: border-box; }
        .modal-content { background: white; border-radius: 14px; width: 100%; max-width: 500px; padding: 15px; box-sizing: border-box; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
        
        #reader, #stocktakeReader { width: 100%; max-width: 350px; margin: 0 auto; background: #000; border-radius: 8px; overflow: hidden; display: none; }
        .preview-zone { display: none; background: #fff9e6; border: 1px dashed #ff9500; border-radius: 12px; padding: 10px; margin-bottom: 10px; }
    </style>
</head>
<body>

    <div class="sales-dashboard" onclick="toggleSection('todayDetailBox')">
        <h3>💰 今日累计销售额 (点击可查看或隐藏明细)</h3>
        <div class="count" id="todayAmount">¥ 0.00</div>
        <div id="todayCount" style="font-size: 13px; opacity: 0.9; font-weight: bold;">今天已成功卖出: 0 件货品</div>
    </div>

    <div class="card" id="todayDetailBox">
        <h2>🛍️ 今日卖出商品精细明细栏</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr style="background: #fff5f5;">
                        <th>条码/货号</th><th>货品名称</th><th>品类</th><th>金重(g)</th><th>标签价</th><th>实际售价</th>
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
            <div style="background: #fff1f0; border: 1px solid #ffa39e; padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 13px; color: #a8071a; line-height: 1.5;">
                <b style="font-size: 14px; color: #cf1322;">⚠️ 批量导入 Excel 模糊联想规范：</b><br>
                <span style="display:inline-block; margin-top: 4px;">表格首行必须包含识别项（系统将智能分析并包容映射）：</span><br>
                <div style="margin: 6px 0; display: flex; flex-wrap: wrap; gap: 4px;">
                    <span style="background:#fff; padding:2px 6px; border:1px solid #ffa39e; border-radius:4px; font-weight:bold;">条码 / 货号</span>
                    <span style="background:#fff; padding:2px 6px; border:1px solid #ffa39e; border-radius:4px; font-weight:bold;">货品名称</span>
                    <span style="background:#fff; padding:2px 6px; border:1px solid #ffa39e; border-radius:4px; font-weight:bold;">品类 / 分类</span>
                    <span style="background:#fff; padding:2px 6px; border:1px solid #ffa39e; border-radius:4px; font-weight:bold;">金重 / 克量</span>
                    <span style="background:#fff; padding:2px 6px; border:1px solid #ffa39e; border-radius:4px; font-weight:bold;">标价</span>
                </div>
                <span style="color: #666; font-size:12px;">💡 系统已分离标价与售价。新货入库阶段仅记录【标价】属性，商品实销时由柜台单独输入【实际售价】进行销售记账。</span>
            </div>

            <input type="file" id="excelFile" accept=".xlsx, .xls">
            <button class="btn btn-green" onclick="uploadExcel()">选择并解析新货 Excel</button>
        </div>

        <div class="tab-content" id="contentOp3">
            <div id="stocktakeSetup"><button class="btn btn-purple" onclick="startLocalStocktake()">🟢 开启手机离线盘点</button></div>
            <div id="stocktakeActiveZone" style="display:none;">
                <div style="background:#f5f0ff; padding:10px; border-radius:8px; margin-bottom:10px; font-size:13px;">
                    <div>📊 盘点实时进度：<b id="stProgressText" style="color:#5856d6; font-size:16px;">0 / 0</b></div>
                </div>
                <button class="btn btn-scan" id="stocktakeScanBtn" onclick="toggleScanner('stocktake')">📷 开启盘点专用扫码</button>
                <div id="stocktakeReader"></div>
                <input type="text" id="stocktakeBarcodeInput" placeholder="可在此手动输入未盘货品条码" onkeydown="if(event.keyCode==13)manualStocktakeCheck()">
                
                <div class="table-container" style="background: #fff;">
                    <table>
                        <thead><tr style="background:#f5f0ff;"><th>条码/货号</th><th>货品名称</th><th>品类</th><th>金重</th></tr></thead>
                        <tbody id="stocktakeMissingBody"></tbody>
                    </table>
                </div>
                <div style="display:flex; gap:10px; margin-top:20px;">
                    <button class="btn btn-green" style="flex:1;" onclick="finishStocktakeSubmit()">🏁 结束盘点并安全保存</button>
                    <button class="btn" style="background:#666; width:80px;" onclick="cancelStocktakeReset()">放弃</button>
                </div>
            </div>
        </div>
    </div>

    <div class="preview-zone" id="previewZone">
        <h2 style="border-left-color: #ff9500; font-size:13px;">⚠️ 待入库新货安全校验预览区</h2>
        <div class="table-container" style="max-height: 180px; background: white;">
            <table>
                <thead>
                    <tr><th>条码/货号</th><th>货品名称</th><th>品类</th><th>金重/克量</th><th>匹配标签价</th><th>预估工费</th></tr>
                </thead>
                <tbody id="previewBody"></tbody>
            </table>
        </div>
        <div style="display:flex; gap:8px; margin-top:8px;">
            <button class="btn btn-green" style="padding:8px; font-size:12px;" onclick="confirmImport()">核对无误，确认锁库存上架</button>
            <button class="btn" style="background:#666; padding:8px; font-size:12px;" onclick="cancelImport()">取消</button>
        </div>
    </div>

    <div class="card">
        <div class="tab-header-view">
            <div class="tab-btn-view active" id="tabView1" onclick="switchTab('View', 1)">🟢 店内当前【在售】存货清单</div>
            <div class="tab-btn-view" id="tabView2" onclick="switchTab('View', 2)">📜 历史【已售出】累计数据账本</div>
            <div class="tab-btn-view" id="tabView3" onclick="switchTab('View', 3)">📋 历史盘点存档报告</div>
        </div>
        
        <div class="tab-content active" id="contentView1">
            <input type="text" id="inventorySearchInput" class="search-box green-border" placeholder="⚡ 在售库极速闪电查找 (输入条码、货名、品类)..." oninput="pagerConfig.inventory.currentPage=1; renderPagedTable('inventory');">
            <div class="table-container">
                <table>
                    <thead>
                        <tr style="background:#f6ffed;"><th>条码/货号</th><th>货品名称</th><th>品类</th><th>金重/克量</th><th>标签标价</th><th>工费</th></tr>
                    </thead>
                    <tbody id="inventoryBody"></tbody>
                </table>
            </div>
            <div class="pagination-container" id="pagerInventory"></div>
        </div>
        
        <div class="tab-content" id="contentView2">
            <input type="text" id="soldSearchInput" class="search-box orange-border" placeholder="⚡ 历史已售老账检索 (支持条码、日期、货名过滤)..." oninput="pagerConfig.sold.currentPage=1; renderPagedTable('sold');">
            <div class="table-container">
                <table>
                    <thead>
                        <tr style="background: #fff7e6;">
                            <th>条码/货号</th><th>货品名称</th><th>品类</th><th>金重/克量</th><th>原标签价</th><th style="color:#ff3b30;">最终实际售价</th><th>售出结算日期</th>
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
                        <tr style="background: #f0f5ff;"><th>盘点时间</th><th>账面应有件数</th><th>实盘扫到件数</th><th>盘亏缺失件数</th><th>缺失条码明细</th></tr>
                    </thead>
                    <tbody id="stocktakeHistoryBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="detailModal">
        <div class="modal-content">
            <h2 style="border-left-color: #ff3b30;">❌ 盘亏缺失货品详细名单</h2>
            <div class="table-container" style="max-height: 280px;"><table style="width:100%;"><tbody id="modalTableBody"></tbody></table></div>
            <button class="btn btn-blue" style="margin-top:15px;" onclick="closeModal()">关闭窗口</button>
        </div>
    </div>

    <script>
        // 保持您原本的 script 脚本逻辑即可（前端只根据后端返回的 key 渲染内容）...
        let html5QrcodeScanner = null; let tempParsedData = null; let currentMode = 'sale';
        let backendActiveData = []; let backendSoldData = []; let backendTodayData = [];
        let localStocktakeItems = [];
        
        let pagerConfig = { 
            inventory: { currentPage: 1, pageSize: 6 }, 
            sold: { currentPage: 1, pageSize: 6 }, 
            today: { currentPage: 1, pageSize: 50 } 
        };

        window.onload = loadAllData;

        function getTypeTagHtml(typeStr) {
            const val = String(typeStr || '').trim();
            let bg = '#eef0f3', color = '#495057';
            if (val.includes('戒指') || val.includes('耳')) { bg = '#fff0f6'; color = '#c41d7f'; }
            else if (val.includes('链')) { bg = '#e6f7ff'; color = '#096dd9'; }
            else if (val.includes('镯')) { bg = '#f6ffed'; color = '#389e0d'; }
            else if (val.includes('坠')) { bg = '#f9f0ff'; color = '#531dab'; }
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

        function toggleSection(id) { const el = document.getElementById(id); el.style.display = (el.style.display === 'none') ? 'block' : 'none'; }

        function setMode(mode) {
            currentMode = mode;
            const modeSale = document.getElementById('modeSale'); const modeReturn = document.getElementById('modeReturn');
            const priceInputArea = document.getElementById('priceInputArea'); const submitOpBtn = document.getElementById('submitOpBtn');
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
            let rawData = []; let tbody = null; let pagerDiv = null; let searchId = "";
            
            if (key === 'inventory') { rawData = backendActiveData; tbody = document.getElementById('inventoryBody'); pagerDiv = document.getElementById('pagerInventory'); searchId = "inventorySearchInput"; }
            else if (key === 'sold') { rawData = backendSoldData; tbody = document.getElementById('soldBody'); pagerDiv = document.getElementById('pagerSold'); searchId = "soldSearchInput"; }
            else if (key === 'today') { rawData = backendTodayData; tbody = document.getElementById('todaySalesBody'); pagerDiv = document.getElementById('pagerToday'); }

            tbody.innerHTML = '';
            let filteredData = rawData;
            if(searchId) {
                const query = document.getElementById(searchId).value.trim().toLowerCase();
                if(query) {
                    filteredData = rawData.filter(item => 
                        String(item.code).toLowerCase().includes(query) || String(item.name).toLowerCase().includes(query) || String(item.category).toLowerCase().includes(query)
                    );
                }
            }

            if(filteredData.length === 0) {
                const cols = key === 'sold' ? 7 : 6;
                tbody.innerHTML = `<tr><td colspan="${cols}" style="text-align:center; color:#999; padding:15px;">🔍 清单中未检索到相关匹配条目</td></tr>`;
                pagerDiv.innerHTML = ''; return;
            }

            let totalPages = Math.ceil(filteredData.length / config.pageSize);
            if (config.currentPage > totalPages) config.currentPage = totalPages;
            if (config.currentPage < 1) config.currentPage = 1;

            let startIndex = (config.currentPage - 1) * config.pageSize;
            let pageData = filteredData.slice(startIndex, startIndex + config.pageSize);

            pageData.forEach(item => {
                const tagHtml = getTypeTagHtml(item.category || '其他');
                if (key === 'inventory') {
                    tbody.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${tagHtml}</td><td>${item.weight}g</td><td>¥${item.price}</td><td>¥${item.fee}</td></tr>`;
                } else if (key === 'sold') {
                    tbody.innerHTML += `<tr><td><del>${item.code}</del></td><td>${item.name}</td><td>${tagHtml}</td><td>${item.weight}g</td><td>¥${item.price}</td><td style="color:#ff3b30; font-weight:bold;">¥ ${item.sold_price}</td><td><small>${item.sold_date}</small></td></tr>`;
                } else if (key === 'today') {
                    tbody.innerHTML += `<tr><td><b>${item.code}</b></td><td>${item.name}</td><td>${tagHtml}</td><td>${item.weight}g</td><td>¥${item.price}</td><td style="color:#ff3b30; font-weight:bold;">¥ ${item.sold_price}</td></tr>`;
                }
            });

            pagerDiv.innerHTML = `
                <div>共找到 ${filteredData.length} 条记录</div>
                <div>
                    <button class="page-btn" ${config.currentPage==1?'disabled':''} onclick="goToPage('${key}', ${config.currentPage - 1})">◀</button>
                    <span style="margin: 0 4px; font-weight:bold;">${config.currentPage}/${totalPages}</span>
                    <button class="page-btn" ${config.currentPage==totalPages?'disabled':''} onclick="goToPage('${key}', ${config.currentPage + 1})">▶</button>
                </div>
            `;
        }

        function goToPage(key, page) { pagerConfig[key].currentPage = page; renderPagedTable(key); }
        // 后面省略您剩余的前端业务逻辑（如摄像头控制、文件上传等，均未做改动，保持原有功能）...
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # 确保文件存在
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f: f.write('[]')
    app.run(host='0.0.0.0', port=5000, debug=True)
