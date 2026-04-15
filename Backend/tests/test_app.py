import pytest
from unittest.mock import patch, MagicMock
from app import app, supa_call, load_data

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_returns_ok(client):
    rv = client.get('/health')
    assert rv.status_code == 200
    assert rv.json['status'] == 'ok'

def test_login_valid_credentials(client):
    rv = client.post('/login', json={'username': 'demo', 'password': 'vaanichain123'})
    assert rv.status_code == 200
    assert rv.json['success'] is True

def test_login_missing_body(client):
    rv = client.post('/login')
    assert rv.status_code == 400
    assert rv.json['error'] == 'JSON body required'

def test_login_invalid_credentials(client):
    rv = client.post('/login', json={'username': 'demo', 'password': 'wrong'})
    assert rv.status_code == 401
    assert rv.json['success'] is False

@patch('app.supa_call')
def test_shipments_fallback_when_supabase_down(mock_supa, client):
    mock_supa.return_value = None
    rv = client.get('/shipments')
    assert rv.status_code == 200
    assert isinstance(rv.json, list)

@patch('app.supa_call')
def test_status_handles_non_list_supabase(mock_supa, client):
    mock_supa.return_value = {"error": "down"}
    rv = client.get('/status')
    assert rv.status_code == 200
    assert 'total' in rv.json

@patch('app.supa_call')
@patch('app.check_demo_token', return_value=True)
def test_trigger_no_crash_supabase_down(mock_check, mock_supa, client):
    mock_supa.return_value = None
    rv = client.post('/trigger', json={'mode': 'road'})
    assert rv.status_code in [200, 503]
    assert rv.json is not None

@patch('app.supa_call')
@patch('app.check_demo_token', return_value=True)
def test_reset_no_crash_supabase_down(mock_check, mock_supa, client):
    mock_supa.return_value = None
    rv = client.post('/reset', json={})
    assert rv.status_code in [200, 503]
    assert rv.json is not None

@patch('app.req.get')
def test_weather_parses_correct_fields(mock_get, client):
    mock_geo_resp = MagicMock()
    mock_geo_resp.json.return_value = {"results": [{"latitude": 19.0, "longitude": 72.0}]}
    
    mock_weather_resp = MagicMock()
    mock_weather_resp.json.return_value = {
        "current": {"temperature_2m": 30, "precipitation": 0, "wind_speed_10m": 12, "weather_code": 0}
    }
    
    mock_get.side_effect = [mock_geo_resp, mock_weather_resp]
    
    rv = client.get('/weather/Mumbai')
    assert rv.status_code == 200
    assert rv.json['wind_kmh'] == 12

@patch('app.req.get')
def test_weather_fallback_on_error(mock_get, client):
    mock_get.side_effect = Exception("API down")
    rv = client.get('/weather/Mumbai')
    assert rv.status_code == 200
    assert rv.json['city'] == 'Mumbai'
    assert 'temp_c' in rv.json
