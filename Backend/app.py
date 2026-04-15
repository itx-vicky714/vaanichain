from flask import Flask, jsonify, request, send_from_directory
import os
import logging
from flask_cors import CORS
import json
import requests as req
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Load env vars
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')
DEMO_TOKEN = os.environ.get('DEMO_TOKEN', 'vaanichain_demo')

# Headers for REST calls
SUPA_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def supa_call(method, path, payload=None):
    if not SUPABASE_URL or not SUPABASE_KEY: return None
    try:
        base_url = SUPABASE_URL.rstrip('/')
        url = f"{base_url}/rest/v1/{path}"
        r = req.request(method, url, headers=SUPA_HEADERS, json=payload, timeout=(3.05, 10))
        if not r.ok:
            logger.warning(f"Supabase error: {r.status_code} - {r.text[:200]}")
            return None
        if r.status_code == 204 or not r.text.strip():
            return None
        return r.json()
    except Exception as e:
        logger.exception(f"Supabase REST error: {e}")
        return None

app = Flask(__name__)
@app.route('/<path:filename>')
def serve_frontend(filename):
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'Frontend')
    return send_from_directory(frontend_path, filename)

@app.route('/')
def index():
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'Frontend')
    return send_from_directory(frontend_path, 'index.html')
CORS(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'shipments.json')

def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.exception(f"Error saving data: {e}")

@app.route('/health')
def health():
    return jsonify({"status": "ok", "supabase": SUPABASE_URL != ''})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    u = data.get('username')
    p = data.get('password')
    valid = {'demo':'vaanichain123', 'admin':'admin123', 'judge':'hackathon'}
    if u in valid and valid[u] == p:
        return jsonify({"success": True, "token": f"vc-{u}-token"})
    return jsonify({"success": False}), 401

@app.route('/shipments', methods=['GET'])
def get_shipments():
    res = supa_call('GET', 'shipments?select=*')
    if not isinstance(res, list):
        res = load_data()
    return jsonify(res)

def check_demo_token():
    token = request.headers.get('X-Demo-Token')
    if not token or token != DEMO_TOKEN:
        return False
    return True

@app.route('/shipments/add', methods=['POST'])
def add_shipment():
    if not check_demo_token():
        return jsonify({"success": False, "error": "Invalid or missing token"}), 403
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    supa_call('POST', 'shipments', payload=data)
    
    # Save to JSON as backup
    current = load_data()
    current.append(data)
    save_data(current)
    
    return jsonify({"success": True})

@app.route('/trigger', methods=['POST'])
def trigger():
    if not check_demo_token():
        return jsonify({"success": False, "error": "Invalid or missing token"}), 403
    data = request.get_json(silent=True) or {}
    mode = data.get('mode')
    route = data.get('route')
    if SUPABASE_URL:
        try:
            if mode:
                supa_call('PATCH', f'shipments?mode=eq.{mode}', payload={'status':'at_risk'})
            elif route:
                supa_call('PATCH', f'shipments?route_name=like.*{route}*', payload={'status':'at_risk'})
            else:
                supa_call('PATCH', 'shipments?id=not.is.null', payload={'status':'at_risk'})
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Supabase not connected'}), 503

@app.route('/reset', methods=['POST'])
def reset():
    if not check_demo_token():
        return jsonify({"success": False, "error": "Invalid or missing token"}), 403
    if SUPABASE_URL:
        try:
            supa_call('PATCH', 'shipments?id=not.is.null', payload={'status':'on_time'})
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Supabase not connected'}), 503

@app.route('/status', methods=['GET'])
def network_status():
    data = supa_call('GET', 'shipments?select=*')
    if not isinstance(data, list):
        data = load_data()
        
    total = len(data)
    on_time = 0
    at_risk = 0
    delayed = 0
    rev_risk = 0
    
    for s in data:
        status = s.get('status', 'on_time')
        if status == 'on_time': on_time += 1
        elif status == 'at_risk': 
            at_risk += 1
            rev_risk += s.get('value_inr', 0)
        elif status == 'delayed': 
            delayed += 1
            rev_risk += s.get('value_inr', 0)
            
    eff = round((on_time / total * 100) if total > 0 else 0)
    net_risk = "low" if eff > 80 else "medium" if eff > 60 else "high"
    
    return jsonify({
        "total": total, "on_time": on_time, "at_risk": at_risk, "delayed": delayed,
        "efficiency_pct": eff, "revenue_at_risk": rev_risk, "network_risk": net_risk,
        "alerts": [{"type":"warning", "msg":f"{at_risk} shipments at risk"}] if at_risk > 0 else []
    })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    message = data.get('message','')
    
    # Try Gemini first
    if GEMINI_KEY:
        try:
            ships = supa_call('GET', 'shipments?select=*')
            if not isinstance(ships, list): ships = load_data()
            at_risk = [s for s in ships if s.get('status') == 'at_risk']
            delayed = [s for s in ships if s.get('status') == 'delayed']
            
            prompt = f"""You are VaaniBot, AI logistics assistant for VaaniChain India.
Current network: {len(ships)} shipments total.
At risk: {len(at_risk)} shipments: {[s['id']+' ('+s['origin']+' to '+s['destination']+')' for s in at_risk[:3]]}
Delayed: {len(delayed)} shipments.

User message: {message}

Reply in 2-3 sentences max. Be helpful and specific about Indian logistics.
If message is in Hindi/Hinglish, reply in Hinglish."""
            
            response = req.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}',
                json={'contents':[{'parts':[{'text': prompt}]}]},
                timeout=10
            )
            reply = response.json()['candidates'][0]['content']['parts'][0]['text']
            return jsonify({'reply': reply})
        except:
            pass
    
    # Rule-based fallback
    msg = message.lower()
    if any(w in msg for w in ['status','kitna','total','how many']):
        ships = supa_call('GET', 'shipments?select=*')
        if not isinstance(ships, list): ships = load_data()
        on_time = len([s for s in ships if s.get('status')=='on_time'])
        at_risk = len([s for s in ships if s.get('status')=='at_risk'])
        return jsonify({'reply': f'Network mein {len(ships)} shipments hain. {on_time} on time, {at_risk} at risk.'})
    elif any(w in msg for w in ['rail','train','dfcil']):
        return jsonify({'reply': 'Rail freight DFC corridors pe 94% on-time chal raha hai. Eastern aur Western DFC dono clear hain.'})
    elif any(w in msg for w in ['air','flight','cargo']):
        return jsonify({'reply': 'Air cargo operations normal hain. Delhi IGI pe morning fog risk hai - 9am ke baad departure recommend karta hun.'})
    elif any(w in msg for w in ['sea','port','ship','jnpt']):
        return jsonify({'reply': 'JNPT Mumbai pe normal congestion hai. Bay of Bengal route mein monsoon risk elevated hai.'})
    elif any(w in msg for w in ['delay','late','problem']):
        return jsonify({'reply': 'Delayed shipments mostly road aur sea pe hain. NH-48 pe monsoon flooding ka risk hai. Rail ya air consider karo.'})
    else:
        return jsonify({'reply': 'VaaniChain network monitor kar raha hun. Koi specific route, mode ya shipment ke baare mein puchho!'})

@app.route('/weather/<city>', methods=['GET'])
def get_weather(city):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_r = req.get(geo_url, timeout=5)
        geo_r.raise_for_status()
        geo_data = geo_r.json()
        if not geo_data.get('results'):
            raise ValueError("City not found in geocoding")
        lat = geo_data['results'][0]['latitude']
        lon = geo_data['results'][0]['longitude']
        
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,wind_speed_10m,weather_code&timezone=auto"
        r = req.get(url, timeout=5)
        r.raise_for_status()
        d = r.json()['current']
        temp = d['temperature_2m']
        rain = d['precipitation']
        wind = d['wind_speed_10m']
        
        cond = "Clear"
        r_level = "low"
        if rain > 2: 
            cond = "Rain"
            r_level = "medium"
        if rain > 10:
            cond = "Heavy Rain"
            r_level = "high"
            
        return jsonify({
            "city": city, "temp_c": temp, "condition": cond, 
            "rain_mm": rain, "wind_kmh": wind, "risk_level": r_level
        })
    except Exception as e:
        logger.exception(f"Weather error for {city}: {e}")
        return jsonify({"city": city, "temp_c": 25, "condition": "Unknown", "rain_mm": 0, "wind_kmh": 10, "risk_level": "low"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
