"""Private ML service: route/time filtering, explainable ranking and demand forecast."""
import hmac
import json
import math
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
import joblib
import numpy as np
from flask import Flask, request, jsonify
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics.pairwise import cosine_similarity
from waitress import serve

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024
MODEL_PATH = Path(os.environ.get('MODEL_PATH', str(Path(__file__).parent / 'models' / 'matching.joblib')))
LOCK = threading.RLock()
MODEL = None
VERSION = 'similarity-v1 (cold start)'
SAMPLES = 0
if MODEL_PATH.exists():
    saved = joblib.load(MODEL_PATH)  # Only this service writes this local file.
    MODEL, VERSION, SAMPLES = saved['model'], saved['version'], saved['samples']

@app.before_request
def authenticate():
    key = os.environ.get('ML_SERVICE_KEY', '')
    if not key or not hmac.compare_digest(request.headers.get('X-Service-Key', ''), key):
        return jsonify(error='Service authentication required'), 401

@app.errorhandler(ValueError)
@app.errorhandler(KeyError)
@app.errorhandler(TypeError)
def invalid(error):
    return jsonify(error='Invalid analytics input'), 400

def haversine(a, b, c, d):
    lat1, lat2 = math.radians(float(a)), math.radians(float(c))
    dl, dn = lat2-lat1, math.radians(float(d)-float(b))
    x = math.sin(dl/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dn/2)**2
    return 6371 * 2 * math.asin(math.sqrt(min(1, max(0, x))))

def features_for(q, r, max_route):
    pickup = haversine(q['origin_lat'], q['origin_lng'], r['origin_lat'], r['origin_lng'])
    drop = haversine(q['dest_lat'], q['dest_lng'], r['dest_lat'], r['dest_lng'])
    minutes = abs((datetime.fromisoformat(q['departure'])-datetime.fromisoformat(r['departure'])).total_seconds())/60
    if pickup > max_route or drop > max_route or minutes > int(q['tolerance']):
        return None
    compatible = q['preference'] == 'any' or r['preference'] == 'any' or q['preference'] == r['preference']
    values = [max(0, 1-pickup/max_route), max(0, 1-drop/max_route), max(0, 1-minutes/int(q['tolerance'])), float(compatible), float(r.get('rating', 0))/5]
    return values, pickup, drop, minutes

@app.post('/recommend')
def recommend():
    data = request.get_json(); q = data['request']; max_route = float(data['settings']['max_route_km'])
    if max_route <= 0 or int(q['tolerance']) <= 0:
        raise ValueError('Invalid settings')
    matches = []; seen = set()
    with LOCK:
        model, version = MODEL, VERSION
    for ride in data['rides']:
        if ride['id'] in seen or int(ride['available_seats']) < 1 or ride['status'] != 'OPEN':
            continue
        seen.add(ride['id'])
        if int(ride['driver_id']) == int(q['user_id']):
            continue
        if datetime.fromisoformat(ride['departure']) <= datetime.now():
            continue
        result = features_for(q, ride, max_route)
        if result is None:
            continue
        f, pickup, drop, minutes = result
        # Similarity is blended with magnitude so a uniformly bad vector cannot score perfectly.
        weights = np.array([.30, .30, .25, .10, .05])
        similarity = float(cosine_similarity([np.array(f)*weights], [weights])[0, 0])
        baseline = .8*float(np.dot(f, weights)) + .2*similarity
        score = baseline if model is None else .6*baseline + .4*float(model.predict([f])[0])
        matches.append({**ride, 'score': round(100*max(0, min(1, score)), 1), 'features': f,
                        'pickup_km': round(pickup, 2), 'drop_km': round(drop, 2), 'time_difference': round(minutes),
                        'reason': f'{pickup:.1f} km pickup gap · {minutes:.0f} min timing difference · '+('preferences compatible' if f[3] else 'different conversation preferences')})
    matches.sort(key=lambda r: (-r['score'], r['price'], r['id']))
    return jsonify(matches=matches, model_version=version)

@app.post('/train')
def train():
    global MODEL, VERSION, SAMPLES
    samples = request.get_json()['samples']; x, y = [], []
    for row in samples:
        try:
            f = json.loads(row['features']) if isinstance(row['features'], str) else row['features']
            rating = int(row['rating'])
            if len(f) == 5 and all(math.isfinite(float(v)) and 0 <= float(v) <= 1 for v in f) and 1 <= rating <= 5:
                x.append(f); y.append((rating-1)/4)
        except (ValueError, TypeError, KeyError):
            continue
    if len(x) < 10:
        return jsonify(status='cold_start', samples=len(x), minimum_samples=10, model_version=VERSION)
    with LOCK:
        # Serialize fitting and publishing so an older concurrent request cannot overwrite a newer model.
        if len(x) < SAMPLES:
            return jsonify(status='unchanged', samples=SAMPLES, model_version=VERSION)
        candidate = RandomForestRegressor(n_estimators=80, max_depth=5, min_samples_leaf=2, random_state=42, n_jobs=1).fit(x, y)
        version = 'feedback-rf-' + datetime.now().strftime('%Y%m%d%H%M%S')
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp = MODEL_PATH.with_suffix('.tmp')
        joblib.dump({'model': candidate, 'version': version, 'samples': len(x)}, temp)
        os.replace(temp, MODEL_PATH)
        MODEL, VERSION, SAMPLES = candidate, version, len(x)
    return jsonify(status='trained', samples=SAMPLES, model_version=VERSION,
                   note='Feedback-trained ranking; no claim of validated predictive accuracy.')

@app.post('/forecast')
def forecast():
    history = request.get_json()['history']
    if not history:
        return jsonify(status='insufficient_history', predictions=[], observed_days=0)
    counts = {(datetime.fromisoformat(str(r['day'])).date(), int(r['hour'])): int(r['demand']) for r in history}
    start = min(d for d, h in counts); today = datetime.now().date()
    days = (today-start).days
    if days < 14:
        return jsonify(status='insufficient_history', predictions=[], observed_days=days, minimum_days=14)
    x, y = [], []
    # Include zero-demand hours; training only observed hours would inflate predictions.
    for offset in range(min(days, 90)):
        day = today-timedelta(days=offset+1)
        for hour in range(24):
            x.append([day.weekday(), hour]); y.append(counts.get((day, hour), 0))
    model = RandomForestRegressor(n_estimators=80, min_samples_leaf=2, random_state=42, n_jobs=1).fit(x, y)
    predictions = []
    for offset in range(1, 8):
        day = today+timedelta(days=offset)
        hourly = model.predict([[day.weekday(), hour] for hour in range(24)])
        predictions.append({'day': day.isoformat(), 'demand': round(float(sum(hourly)), 1), 'peak_hour': int(np.argmax(hourly))})
    return jsonify(status='estimated', predictions=predictions, observed_days=min(days, 90),
                   model='RandomForestRegressor', note='Exploratory forecast from recorded requests; not a validated service guarantee.')

@app.post('/health')
def health():
    return jsonify(status='online', model_version=VERSION, training_samples=SAMPLES)

if __name__ == '__main__':
    if not os.environ.get('ML_SERVICE_KEY'):
        raise SystemExit('Set ML_SERVICE_KEY before starting the service')
    serve(app, host='127.0.0.1', port=int(os.environ.get('ML_PORT', '5001')), threads=4)
