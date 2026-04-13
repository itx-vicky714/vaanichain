from flask import Flask, jsonify, request, send_from_directory
import os
from flask_cors import CORS
import os, json, requests as req
from dotenv import load_dotenv

load_dotenv()

# Load env vars
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY', '')

# Headers for REST calls
SUPA_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def supa_call(method, path, json=None):
    if not SUPABASE_URL: return None
    try:
        url = f"{SUPABASE_URL}/rest/v1/{path}"
        r = req.request(method, url, headers=SUPA_HEADERS, json=json, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Supabase REST error: {e}")
        return None

app = Flask(__name__)
@app.route('/<path:filename>')
def serve_frontend(filename):
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'Frontend')
    return send_from_directory(frontend_path, filename)

@app.route('/')
def index():
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'Frontend')
    return send_from_directory(frontend_path, 'dashboard.html')
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
        print(f"Error saving data: {e}")

@app.route('/')
def health():
    return jsonify({"status": "ok", "supabase": SUPABASE_URL != ''})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    u = data.get('username')
    p = data.get('password')
    valid = {'demo':'vaanichain123', 'admin':'admin123', 'judge':'hackathon'}
    if u in valid and valid[u] == p:
        return jsonify({"success": True, "token": f"vc-{u}-token"})
    return jsonify({"success": False}), 401

@app.route('/shipments', methods=['GET'])
def get_shipments():
    res = supa_call('GET', 'shipments?select=*')
    if res is not None:
        return jsonify(res)
    return jsonify(load_data())

@app.route('/shipments/add', methods=['POST'])
def add_shipment():
    data = request.json
    supa_call('POST', 'shipments', json=data)
    
    # Save to JSON as backup
    current = load_data()
    current.append(data)
    save_data(current)
    
    return jsonify({"success": True})

@app.route('/trigger', methods=['POST'])
def trigger():
    mode = request.json.get('mode')
    route = request.json.get('route')
    if SUPABASE_URL:
        try:
            if mode:
                supa_call('PATCH', f'shipments?mode=eq.{mode}', json={'status':'at_risk'})
            elif route:
                supa_call('PATCH', f'shipments?route_name=like.*{route}*', json={'status':'at_risk'})
            else:
                supa_call('PATCH', 'shipments?id=neq.', json={'status':'at_risk'})
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Supabase not connected'}), 503

@app.route('/reset', methods=['POST'])
def reset():
    if SUPABASE_URL:
        try:
            supa_call('PATCH', 'shipments?id=neq.', json={'status':'on_time'})
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Supabase not connected'}), 503

@app.route('/status', methods=['GET'])
def network_status():
    data = supa_call('GET', 'shipments?select=*')
    if data is None:
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
    message = request.json.get('message','')
    
    # Try Gemini first
    if GEMINI_KEY:
        try:
            ships = supa_call('GET', 'shipments?select=*') or []
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
        ships = supa_call('GET', 'shipments?select=*') or []
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
    coords = {
        'Mumbai':(19.07,72.87), 'Delhi':(28.67,77.22), 'Chennai':(13.08,80.27),
        'Kolkata':(22.57,88.36), 'Bangalore':(12.97,77.59), 'Hyderabad':(17.38,78.47)
    }
    if city not in coords:
        return jsonify({"error":"City not found"}), 404
        
    lat, lon = coords[city]
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,windspeed_10m,weathercode"
        r = req.get(url, timeout=5)
        d = r.json()['current']
        temp = d['temperature_2m']
        rain = d['precipitation']
        wind = d['windspeed_10m']
        
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
    except:
        return jsonify({"city": city, "temp_c": 25, "condition": "Unknown", "rain_mm": 0, "wind_kmh": 10, "risk_level": "low"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
