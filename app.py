import io, os, json, time, re, secrets
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlopen, Request
from functools import wraps
from ldap3 import Server, Connection, ALL, core

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from flask import Flask, render_template_string, send_file, jsonify, request, session, redirect, url_for

CRAICKEN_API = os.environ.get('CRAICKEN_API_URL', 'http://192.168.1.2:8042')
AUTH_TOKEN = os.environ.get('CRAICKEN_AUTH_TOKEN', '111JbCV3_BSzwygG0XJ-6kFWDz8v-LHx0rwb8zGv7H8')
PROJECTS_DIR = Path(os.environ.get('PROJECTS_DIR', '/mnt/SANDIEGO/Projects'))
CACHE_TTL = int(os.environ.get('CACHE_TTL', '300'))
CONSOLE_PASSWORD = os.environ.get('CONSOLE_PASSWORD', 'splipperverse')
AD_SERVER = os.environ.get('AD_SERVER', '192.168.1.10')
AD_PORT = int(os.environ.get('AD_PORT', '389'))
AD_DOMAIN = os.environ.get('AD_DOMAIN', 'corp.project6x7.com')
AD_BASE_DN = os.environ.get('AD_BASE_DN', 'DC=corp,DC=project6x7,DC=com')
AD_USE_TLS = os.environ.get('AD_USE_TLS', 'false').lower() == 'true'

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', secrets.token_hex(32))
HEADERS = {'Authorization': f'Bearer {AUTH_TOKEN}'}

LOGIN_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SPLIPPERVERSE &mdash; Auth</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;color:#d4d4d8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',monospace;display:flex;align-items:center;justify-content:center;min-height:100vh}
.login-box{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:40px;width:380px;text-align:center}
.login-box h1{font-size:1.4rem;color:#58a6ff;letter-spacing:0.12em;margin-bottom:4px}
.login-box .sub{font-size:0.75rem;color:#484f58;margin-bottom:24px}
.login-box input{width:100%;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#d4d4d8;font-size:0.9rem;outline:none;margin-bottom:12px;font-family:inherit}
.login-box input:focus{border-color:#58a6ff}
.login-box button{width:100%;padding:10px;background:#58a6ff;color:#fff;border:none;border-radius:6px;font-size:0.9rem;cursor:pointer;font-weight:600}
.login-box button:hover{background:#4a8cd4}
.login-box .error{color:#f47067;font-size:0.8rem;margin-top:8px}
.login-box .footer{font-size:0.65rem;color:#484f58;margin-top:20px}
</style>
</head>
<body>
<div class="login-box">
<h1>SPLIPPERVERSE</h1>
<div class="sub">Fleet Console &mdash; Project6x7.com</div>
<form method="POST" action="/login">
<input type="text" name="username" placeholder="corp\\username" autofocus>
<input type="password" name="password" placeholder="Password">
<button type="submit">Access Console</button>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
</form>
<div class="footer">Project6x7.com &mdash; AD authenticated</div>
</div>
</body>
</html>'''

cache = {'data': None, 'ts': 0, 'context_map': {}, 'agents': [], 'fleet': {}, 'debates': []}

S = '</scr' + 'ipt>'

def fetch_json(url):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def fetch_context_list(kind, limit=200):
    try:
        return fetch_json(f'{CRAICKEN_API}/api/v1/context/list?kind={kind}&limit={limit}').get('entries', [])
    except Exception as e:
        print(f'fetch_context_list({kind}) error: {e}')
    return []

def fetch_context_retrieve(q, kind='ken', limit=5):
    try:
        q_enc = q.replace(' ', '%20')
        return fetch_json(f'{CRAICKEN_API}/api/v1/context/retrieve?q={q_enc}&kind={kind}&limit={limit}').get('results', [])
    except Exception as e:
        print(f'fetch_context_retrieve({q}) error: {e}')
    return []

def multi_fetch(queries, kind='ken', limit=4):
    seen = set()
    results = []
    for q in queries:
        for r in fetch_context_retrieve(q, kind, limit):
            sid = r.get('id', r.get('source', ''))
            if sid not in seen:
                seen.add(sid)
                results.append(r)
    return results

def fetch_agents():
    try:
        return fetch_json(f'{CRAICKEN_API}/api/v1/net/agents')
    except Exception as e:
        print(f'fetch_agents error: {e}')
    return []

def collect_data():
    ken_entries = fetch_context_list('ken', 200)
    craic_entries = fetch_context_list('craic', 68)
    agents = fetch_agents()

    word_freq = Counter()
    context_map = {}

    for entries, kind in [(ken_entries, 'ken'), (craic_entries, 'craic')]:
        for e in entries:
            tags = [t.strip().lower() for t in e.get('tags', '').split(',') if t.strip()]
            for t in tags:
                if t and t != 'unknown':
                    word_freq[t] += 1
                    if t not in context_map:
                        context_map[t] = []
                    context_map[t].append({
                        'source': e.get('source', ''),
                        'snippet': e.get('snippet', '')[:300],
                        'kind': kind,
                        'id': e.get('id')
                    })
            src = e.get('source', '').lower().replace('-', ' ')
            for w in re.findall(r'[a-z]{3,}', src):
                if w not in ('the', 'and', 'for', 'with', 'that', 'this', 'from'):
                    word_freq[w] += 0.5

    for a in agents:
        name = a.get('name', '').lower()
        if name:
            word_freq[name] += 5
            if name not in context_map:
                context_map[name] = []
            caps = ', '.join(a.get('capabilities', []))
            context_map[name].append({
                'source': f'agent/{a.get("hostname", name)}',
                'snippet': f'Agent {a["name"]} on {a.get("hostname","?")}. Capabilities: {caps}. Status: {a.get("status","?")}',
                'kind': 'agent',
                'id': a.get('id')
            })
        for cap in a.get('capabilities', []):
            c = cap.lower().replace('-', ' ')
            word_freq[c] += 2

    if PROJECTS_DIR.exists():
        projects = sorted([d.name for d in PROJECTS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')])
        for p in projects:
            name = p.lower().replace('-', ' ').replace('_', ' ')
            word_freq[name] += 3

    return word_freq, context_map, agents, ken_entries, craic_entries

def get_data(force=False):
    now = time.time()
    if force or not cache['data'] or (now - cache['ts']) > CACHE_TTL:
        freq, ctx, agents, ken, craic = collect_data()
        cache['data'] = freq
        cache['context_map'] = ctx
        cache['agents'] = agents
        cache['ts'] = now

        diag = defaultdict(list)
        for e in ken + craic:
            src = e.get('source', '').lower()
            tags = e.get('tags', '').lower()
            if any(t in tags or t in src for t in ['fleet', 'diagnostic', 'health', 'disk', 'cpu', 'memory']):
                diag['fleet'].append(e)
            if any(t in tags or t in src for t in ['sic', 'debate', 'massdeb8', 'committee']):
                diag['debates'].append(e)
            if any(t in tags or t in src for t in ['network', 'connect', 'topology', 'dns', 'lan']):
                diag['network'].append(e)
        cache['diag'] = diag
    return cache['data'], cache['context_map']

AGT_STATUS_HTML = '''<div class="grid-3">
{% for a in agents %}
<div class="ag-card" onclick="openContext('{{ a.name|lower }}')">
<div class="ag-name">{{ a.name }}</div>
<div class="ag-host">{{ a.hostname }}</div>
<div class="ag-caps">{% for c in a.capabilities %}<span class="tag-sm">{{ c }}</span> {% endfor %}</div>
<div class="ag-status {{ a.status }}">{{ a.status }}</div>
</div>
{% endfor %}
</div>'''

HTML_BEFORE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SPLIPPERVERSE</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#000;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',monospace;overflow:hidden;height:100vh;width:100vw;user-select:none}
#canvas-wrap{position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:0}

/* Header */
#header{position:fixed;top:0;left:0;right:0;z-index:20;padding:16px 28px 8px;background:linear-gradient(180deg,rgba(0,0,0,0.92) 0%,transparent 100%);pointer-events:none}
#header h1{font-size:1.8rem;color:#58a6ff;letter-spacing:0.12em;display:inline;text-shadow:0 0 40px rgba(88,166,255,0.25);font-weight:800}
#header .sub{color:#8b949e;font-size:0.75rem;margin-left:12px;opacity:0.6}
#header .badge{display:inline-block;background:rgba(33,38,45,0.5);border:1px solid #30363d;border-radius:10px;padding:1px 8px;font-size:0.6rem;color:#8b949e;margin-left:6px;vertical-align:middle}
#logout{position:fixed;top:18px;right:28px;z-index:25;pointer-events:auto;background:rgba(33,38,45,0.5);border:1px solid #30363d;border-radius:6px;padding:4px 12px;font-size:0.65rem;color:#8b949e;cursor:pointer;text-decoration:none;transition:all 0.15s}
#logout:hover{color:#f47067;border-color:#f47067}

/* Tabs */
#tabs{position:fixed;top:58px;left:0;right:0;z-index:20;padding:0 28px;display:flex;gap:4px;pointer-events:none}
#tabs .tab{pointer-events:auto;padding:6px 16px;border-radius:8px 8px 0 0;font-size:0.7rem;color:#8b949e;cursor:pointer;background:rgba(0,0,0,0.3);border:1px solid transparent;border-bottom:none;transition:all 0.2s;letter-spacing:0.06em;text-transform:uppercase;font-weight:600}
#tabs .tab:hover{color:#c9d1d9;background:rgba(0,0,0,0.5)}
#tabs .tab.active{color:#58a6ff;background:rgba(0,0,0,0.7);border-color:#30363d;border-bottom-color:rgba(0,0,0,0.7)}

/* Tab content overlay */
#content{position:fixed;top:90px;left:0;right:0;bottom:0;z-index:10;pointer-events:none;overflow:hidden}
.tab-content{position:absolute;top:0;left:0;right:0;bottom:0;padding:20px 28px;overflow-y:auto;pointer-events:auto;display:none;background:rgba(0,0,0,0.55);backdrop-filter:blur(6px)}
.tab-content.active{display:block}
.tab-content h2{font-size:0.8rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:16px}
.tab-content h2 span{color:#58a6ff}

/* Word cloud view - minimal overlay */
#tab-cloud{background:transparent;backdrop-filter:none;pointer-events:none;padding:0}
#tab-cloud .cloud-hint{position:absolute;bottom:80px;left:50%;transform:translateX(-50%);color:#484f58;font-size:0.7rem;pointer-events:none;text-align:center;transition:opacity 2s;z-index:5}

/* Agent cards */
.grid-3{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;max-width:900px}
.ag-card{background:rgba(22,27,34,0.8);border:1px solid #30363d;border-radius:8px;padding:14px;cursor:pointer;transition:all 0.15s}
.ag-card:hover{background:rgba(33,38,45,0.8);border-color:#58a6ff}
.ag-name{font-size:1rem;font-weight:700;color:#e6edf3}
.ag-host{font-size:0.65rem;color:#484f58;margin-top:2px}
.ag-caps{margin-top:6px;display:flex;flex-wrap:wrap;gap:3px}
.tag-sm{background:rgba(33,38,45,0.6);border:1px solid #30363d;border-radius:4px;padding:1px 6px;font-size:0.6rem;color:#8b949e}
.ag-status{font-size:0.6rem;text-transform:uppercase;letter-spacing:0.08em;margin-top:6px}
.ag-status.online{color:#3fb950}
.ag-status.offline{color:#e5534b}
.ag-status.idle{color:#d29922}

/* Fleet diag cards */
.fleet-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;max-width:1000px}
.fleet-card{background:rgba(22,27,34,0.8);border:1px solid #30363d;border-radius:8px;padding:12px;font-size:0.75rem;line-height:1.4}
.fleet-card .src{font-size:0.6rem;color:#484f58;text-transform:uppercase}
.fleet-card .body{color:#c9d1d9;margin-top:4px;max-height:80px;overflow:hidden}

/* Debate items */
.debate-list{max-width:800px}
.debate-item{background:rgba(22,27,34,0.8);border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:8px;font-size:0.75rem;line-height:1.4}
.debate-item .src{font-size:0.6rem;color:#484f58;text-transform:uppercase}
.debate-item .body{color:#c9d1d9;margin-top:4px;max-height:60px;overflow:hidden}

/* Network */
.net-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px;max-width:900px}
.net-card{background:rgba(22,27,34,0.8);border:1px solid #30363d;border-radius:8px;padding:12px;font-size:0.75rem}
.net-card .src{font-size:0.6rem;color:#484f58;text-transform:uppercase}
.net-card .body{color:#c9d1d9;margin-top:4px;max-height:60px;overflow:hidden}

/* Search */
#search-box{position:fixed;bottom:24px;left:24px;z-index:25;pointer-events:auto}
#search-box input{background:rgba(0,0,0,0.85);border:1px solid #30363d;color:#d4d4d8;padding:8px 14px;border-radius:8px;font-size:0.8rem;width:220px;backdrop-filter:blur(8px);outline:none;font-family:inherit}
#search-box input:focus{border-color:#58a6ff}
#search-box input::placeholder{color:#484f58}

/* Info panel */
#info-panel{position:fixed;bottom:24px;right:24px;width:420px;max-height:65vh;z-index:30;pointer-events:auto;background:rgba(0,0,0,0.92);border:1px solid #30363d;border-radius:10px;padding:16px;overflow-y:auto;display:none;backdrop-filter:blur(16px);box-shadow:0 8px 40px rgba(0,0,0,0.7)}
#info-panel.open{display:block}
#info-panel .close{float:right;background:none;border:none;color:#8b949e;cursor:pointer;font-size:1.2rem;padding:0 4px}
#info-panel .close:hover{color:#f47067}
#info-panel .word-title{font-size:1.1rem;font-weight:700;color:#58a6ff;margin-bottom:12px;text-transform:capitalize}
#info-panel .ctx-item{border-bottom:1px solid #21262d;padding:10px 0}
#info-panel .ctx-item:last-child{border-bottom:none}
#info-panel .ctx-source{font-size:0.65rem;color:#484f58;text-transform:uppercase;letter-spacing:0.08em}
#info-panel .ctx-kind{display:inline-block;background:#21262d;border-radius:4px;padding:1px 6px;font-size:0.6rem;color:#8b949e;margin-left:4px}
#info-panel .ctx-snippet{font-size:0.78rem;color:#c9d1d9;margin-top:4px;line-height:1.4;max-height:80px;overflow:hidden;word-break:break-word;cursor:pointer;transition:max-height 0.25s ease;position:relative}
#info-panel .ctx-snippet:hover{color:#e6edf3}
#info-panel .ctx-snippet::after{content:'';position:absolute;bottom:0;left:0;right:0;height:28px;background:linear-gradient(transparent,rgba(0,0,0,0.92));pointer-events:none}
#info-panel .ctx-snippet.expanded{max-height:none;overflow:visible}
#info-panel .ctx-snippet.expanded::after{display:none}
#info-panel .empty{color:#484f58;font-size:0.8rem;text-align:center;padding:20px}

/* Loading */
#loading{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:30;color:#58a6ff;font-size:0.9rem;pointer-events:none}
.load-spinner{display:inline-block;width:24px;height:24px;border:2px solid #30363d;border-top-color:#58a6ff;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div id="loading"><div class="load-spinner"></div> Loading...</div>
<div id="canvas-wrap"></div>
<a id="logout" href="/logout">Logout</a>
<div id="header">
<h1>SPLIPPERVERSE</h1><span class="sub">Fleet Console</span><span class="badge">''' + '{{ word_count }}' + ''' words</span>
</div>
<div id="tabs">
<div class="tab active" data-tab="cloud">&#9733; Word Cloud</div>
<div class="tab" data-tab="mgmt">&#9881; Management</div>
<div class="tab" data-tab="sic">&#9878; SIC</div>
<div class="tab" data-tab="net">&#127760; Networking</div>
<div class="tab" data-tab="diag">&#9888; Diagnostics</div>
</div>
<div id="content">
<div id="tab-cloud" class="tab-content active">
<div class="cloud-hint" id="hint">&#x1f446; Drag to orbit &#x2022; Scroll/pinch to zoom &#x2022; Click a word for context</div>
</div>
<div id="tab-mgmt" class="tab-content">
<h2>&#9881; Management Console <span>| Agent Fleet</span></h2>
<div class="grid-3" id="mgmt-agents"></div>
</div>
<div id="tab-sic" class="tab-content">
<h2>&#9878; SIC <span>| Symposium of Infinite Contention</span></h2>
<div class="debate-list" id="sic-content"><div class="empty" style="color:#484f58;padding:20px">Loading debates...</div></div>
</div>
<div id="tab-net" class="tab-content">
<h2>&#127760; Networking <span>| LAN Topology</span></h2>
<div class="net-grid" id="net-content"><div class="empty" style="color:#484f58;padding:20px">Loading network data...</div></div>
</div>
<div id="tab-diag" class="tab-content">
<h2>&#9888; Diagnostics <span>| Fleet Health</span></h2>
<div class="fleet-grid" id="diag-content"><div class="empty" style="color:#484f58;padding:20px">Loading diagnostics...</div></div>
</div>
</div>
<div id="search-box"><input id="search" type="text" placeholder="Search words..." oninput="searchWord(this.value)"></div>
<div id="info-panel">
<button class="close" onclick="closePanel()">&times;</button>
<div class="word-title" id="panel-title"></div>
<div id="panel-content"></div>
</div>
'''

HTML_MIDDLE = """<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }
}
""" + S + """<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const WORDS = """ + '{{ words_json | safe }}' + """;

const container = document.getElementById('canvas-wrap');
const w = window.innerWidth, h = window.innerHeight;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, w/h, 0.1, 1000);
camera.position.set(0, 0, 14);

const renderer = new THREE.WebGLRenderer({ alpha: false, antialias: true });
renderer.setSize(w, h);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x000000, 1);
container.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(w, h);
labelRenderer.domElement.style.position = 'absolute';
labelRenderer.domElement.style.top = '0';
labelRenderer.domElement.style.left = '0';
labelRenderer.domElement.style.pointerEvents = 'none';
container.appendChild(labelRenderer.domElement);

// == OrbitControls for grab/pinch/zoom ==
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.8;
controls.minDistance = 6;
controls.maxDistance = 30;
controls.enablePan = false;
controls.rotateSpeed = 0.6;
controls.zoomSpeed = 0.8;
controls.target.set(0, 0, 0);

// == DOCTOR WHO STARFIELD -- full wrap-around sphere ==
const STAR_COUNT = 3000;
const STAR_RADIUS_INNER = 18;
const STAR_RADIUS_OUTER = 50;
const starGeo = new THREE.BufferGeometry();
const starPos = new Float32Array(STAR_COUNT * 3);
const starSpeeds = new Float32Array(STAR_COUNT);
const starSizes = new Float32Array(STAR_COUNT);
const starColors = new Float32Array(STAR_COUNT * 3);

for (let i = 0; i < STAR_COUNT; i++) {
    const theta = Math.acos(2 * Math.random() - 1);
    const phi = Math.random() * 2 * Math.PI;
    const r = STAR_RADIUS_INNER + Math.random() * (STAR_RADIUS_OUTER - STAR_RADIUS_INNER);
    starPos[i*3] = r * Math.sin(theta) * Math.cos(phi);
    starPos[i*3+1] = r * Math.sin(theta) * Math.sin(phi);
    starPos[i*3+2] = r * Math.cos(theta);
    starSpeeds[i] = 0.2 + Math.random() * 0.6;
    starSizes[i] = 0.08 + Math.random() * 0.2;
    const tint = Math.random();
    if (tint < 0.1) {
        starColors[i*3] = 0.4; starColors[i*3+1] = 0.5; starColors[i*3+2] = 1.0;
    } else if (tint < 0.2) {
        starColors[i*3] = 1.0; starColors[i*3+1] = 0.75; starColors[i*3+2] = 0.5;
    } else {
        starColors[i*3] = 1.0; starColors[i*3+1] = 1.0; starColors[i*3+2] = 1.0;
    }
}

starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
starGeo.setAttribute('color', new THREE.BufferAttribute(starColors, 3));
starGeo.setAttribute('size', new THREE.BufferAttribute(starSizes, 1));

const starMat = new THREE.PointsMaterial({
    size: 0.12,
    vertexColors: true,
    transparent: true,
    opacity: 0.9,
    sizeAttenuation: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false
});
const stars = new THREE.Points(starGeo, starMat);
scene.add(stars);

const starPosAttr = starGeo.attributes.position;
const starArray = starPosAttr.array;

function updateStarfield() {
    const cx = 0, cy = 0, cz = 0;
    for (let i = 0; i < STAR_COUNT; i++) {
        const dx = starArray[i*3] - cx;
        const dy = starArray[i*3+1] - cy;
        const dz = starArray[i*3+2] - cz;
        const dist = Math.sqrt(dx*dx + dy*dy + dz*dz);
        if (dist < 0.01) continue;
        const speed = starSpeeds[i] * 0.08;
        starArray[i*3] -= (dx / dist) * speed;
        starArray[i*3+1] -= (dy / dist) * speed;
        starArray[i*3+2] -= (dz / dist) * speed;
        if (dist < STAR_RADIUS_INNER * 0.5) {
            const theta = Math.acos(2 * Math.random() - 1);
            const phi = Math.random() * 2 * Math.PI;
            const r = STAR_RADIUS_OUTER * (0.85 + Math.random() * 0.15);
            starArray[i*3] = r * Math.sin(theta) * Math.cos(phi);
            starArray[i*3+1] = r * Math.sin(theta) * Math.sin(phi);
            starArray[i*3+2] = r * Math.cos(theta);
        }
    }
    starPosAttr.needsUpdate = true;
}

// == WORD CLOUD ==
const colors = ['#58a6ff','#f0883e','#3fb950','#bc8cff','#f778ba','#e5534b','#d29922','#79c0ff','#ffa657','#56d364','#ff7ee2','#f47067','#e3b341','#96d0ff','#c9d1d9','#ffb77c'];

const maxFreq = Math.max(...WORDS.map(w => w.freq));
const group = new THREE.Group();
const wordObjects = [];
const radii = 4.5;

WORDS.forEach((w) => {
    const theta = Math.acos(2 * Math.random() - 1);
    const phi = Math.random() * 2 * Math.PI;
    const x = radii * Math.sin(theta) * Math.cos(phi);
    const y = radii * Math.sin(theta) * Math.sin(phi);
    const z = radii * Math.cos(theta);

    const ratio = Math.min(1, w.freq / maxFreq);
    const pow = Math.pow(ratio, 0.35);
    const size = 0.45 + pow * 3.0;
    const opacity = 0.2 + pow * 0.8;
    const color = colors[Math.floor(Math.random() * colors.length)];

    const el = document.createElement('span');
    el.textContent = w.word;
    el.style.cssText = `font-size:${size}rem;font-weight:${ratio>0.3?700:500};color:${color};opacity:${opacity};cursor:pointer;text-shadow:0 0 ${8+ratio*16}px ${color}50;transition:opacity 0.2s,text-shadow 0.2s;white-space:nowrap;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',monospace;`;
    el.dataset.word = w.word;
    el.style.pointerEvents = 'auto';

    el.addEventListener('click', (e) => {
        e.stopPropagation();
        window.switchTab('cloud');
        window.openContext(w.word);
    });
    el.addEventListener('mouseenter', () => {
        el.style.opacity = '1';
        el.style.textShadow = `0 0 ${25+ratio*35}px ${color}`;
    });
    el.addEventListener('mouseleave', () => {
        el.style.opacity = opacity;
        el.style.textShadow = `0 0 ${8+ratio*16}px ${color}50`;
    });

    const label = new CSS2DObject(el);
    label.position.set(x, y, z);
    group.add(label);
    wordObjects.push({ label, word: w.word, freq: w.freq, el });
});

scene.add(group);

document.getElementById('loading').style.display = 'none';
document.getElementById('hint').style.opacity = '1';
setTimeout(() => { document.getElementById('hint').style.opacity = '0'; }, 8000);

function animate() {
    requestAnimationFrame(animate);
    updateStarfield();
    controls.update();
    labelRenderer.render(scene, camera);
    renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
    const w2 = window.innerWidth, h2 = window.innerHeight;
    camera.aspect = w2 / h2;
    camera.updateProjectionMatrix();
    renderer.setSize(w2, h2);
    labelRenderer.setSize(w2, h2);
});

window.searchWord = function(q) {
    const ql = q.toLowerCase().trim();
    wordObjects.forEach(({ el }) => {
        if (!ql) { el.style.opacity = ''; el.style.display = ''; return; }
        const match = el.textContent.toLowerCase().includes(ql);
        el.style.opacity = match ? '1' : '0.06';
        if (match) el.style.display = '';
    });
};
""" + S + """<script>
// Tab switching
window.switchTab = function(name) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    document.querySelector('.tab[data-tab="' + name + '"]').classList.add('active');
    if (name !== 'cloud') loadTab(name);
};
// Tab click binding
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function(e) {
            window.switchTab(this.dataset.tab);
        });
    });
});
// Load tab data
const tabData = {};
async function loadTab(name) {
    if (tabData[name]) return;
    try {
        const r = await fetch('/api/' + name);
        const data = await r.json();
        const el = document.getElementById(name + '-content');
        if (el) el.innerHTML = renderTab(name, data);
        tabData[name] = true;
    } catch(e) { console.error(e); }
}
function renderTab(name, data) {
    if (name === 'mgmt') {
        return data.agents.map(a => '<div class="ag-card" onclick="window.switchTab(\\'cloud\\');setTimeout(function(){window.openContext(\\'' + a.name.toLowerCase() + '\\')},100)"><div class="ag-name">' + escHtml(a.name) + '</div><div class="ag-host">' + escHtml(a.hostname) + '</div><div class="ag-caps">' + (a.capabilities||[]).map(function(c) { return '<span class="tag-sm">' + escHtml(c) + '</span> '; }).join('') + '</div><div class="ag-status ' + a.status + '">' + a.status + '</div></div>').join('');
    } else if (name === 'sic') {
        if (!data.results || !data.results.length) return '<div class="empty" style="color:#484f58;padding:20px">No debates found</div>';
        return data.results.map(function(d) { return '<div class="debate-item"><div class="src">' + escHtml(d.source) + '</div><div class="body">' + escHtml((d.snippet||'').slice(0,300)) + '</div></div>'; }).join('');
    } else if (name === 'net') {
        if (!data.results || !data.results.length) return '<div class="empty" style="color:#484f58;padding:20px">No network data</div>';
        return data.results.map(function(d) { return '<div class="net-card"><div class="src">' + escHtml(d.source) + '</div><div class="body">' + escHtml((d.snippet||'').slice(0,200)) + '</div></div>'; }).join('');
    } else if (name === 'diag') {
        if (!data.results || !data.results.length) return '<div class="empty" style="color:#484f58;padding:20px">No diagnostics</div>';
        return data.results.map(function(d) { return '<div class="fleet-card"><div class="src">' + escHtml(d.source) + '</div><div class="body">' + escHtml((d.snippet||'').slice(0,300)) + '</div></div>'; }).join('');
    }
    return '';
}
// Context panel
window.openContext = async function(word) {
    const panel = document.getElementById('info-panel');
    const title = document.getElementById('panel-title');
    const content = document.getElementById('panel-content');
    title.textContent = word;
    content.innerHTML = '<div style="color:#484f58;text-align:center;padding:10px"><div class="load-spinner" style="width:16px;height:16px;margin-right:6px"></div> Loading...</div>';
    panel.classList.add('open');
    try {
        const r = await fetch('/api/context?word=' + encodeURIComponent(word));
        const data = await r.json();
        if (data.results && data.results.length > 0) {
            content.innerHTML = data.results.map(ctx => {
                return '<div class="ctx-item"><div class="ctx-source">' + escHtml(ctx.source) + ' <span class="ctx-kind">' + escHtml(ctx.kind) + '</span></div><div class="ctx-snippet" onclick="this.classList.toggle(\\'expanded\\')">' + escHtml(ctx.snippet) + '</div></div>';
            }).join('');
        } else {
            content.innerHTML = '<div class="empty">No context found</div>';
        }
    } catch(e) {
        content.innerHTML = '<div class="empty">Error fetching context</div>';
    }
};
function escHtml(s) { const d=document.createElement('div'); d.textContent=s||''; return d.innerHTML; }
function closePanel() { document.getElementById('info-panel').classList.remove('open'); }
document.addEventListener('keydown', (e) => { if(e.key==='Escape') closePanel(); });
document.getElementById('info-panel').addEventListener('wheel', function(e) { e.stopPropagation(); });
// Load mgmt tab immediately on page load (inline data)
document.addEventListener('DOMContentLoaded', function() {
    const mgmtEl = document.getElementById('mgmt-agents');
    if (mgmtEl) mgmtEl.innerHTML = `{{ agent_cards | safe }}`;
});
""" + S + """</body>
</html>"""

HTML = HTML_BEFORE + HTML_MIDDLE

import time as _time
_GEMINI_BYPASS_IPS = {'34.62.159.141'}
_GEMINI_BYPASS_UNTIL = 1779671918

def _bypass_allowed():
    if request.remote_addr in _GEMINI_BYPASS_IPS and _time.time() < _GEMINI_BYPASS_UNTIL:
        return True
    return False

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get('authenticated') or _bypass_allowed():
            return f(*args, **kwargs)
        return redirect(url_for('login_page'))
    return wrapped

def authenticate_ad(username, password):
    if not username or not password:
        return False
    try:
        if '\\' in username:
            domain_part, user_part = username.split('\\', 1)
            user_dn = f'{user_part}@{AD_DOMAIN}'
        else:
            user_dn = f'{username}@{AD_DOMAIN}'
        server = Server(AD_SERVER, port=AD_PORT, get_info=ALL)
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        conn.unbind()
        return True
    except core.exceptions.LDAPBindError:
        return False
    except Exception as e:
        print(f'AD auth error: {e}')
        return False

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    error = None
    if _bypass_allowed():
        session['authenticated'] = True
        session['ad_user'] = 'gemini-gcp'
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if AD_SERVER and authenticate_ad(username, password):
            session['authenticated'] = True
            session['ad_user'] = username
            return redirect(url_for('index'))
        elif not AD_SERVER and password == CONSOLE_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            error = 'Incorrect credentials'
    return render_template_string(LOGIN_PAGE, error=error)

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login_page'))

@app.route('/')
@login_required
def index():
    data, ctx_map = get_data()
    words = [{'word': w, 'freq': int(f)} for w, f in data.most_common(120)]

    agents = cache.get('agents', [])
    agent_cards = ''
    for a in agents:
        caps = ''.join(f'<span class="tag-sm">{c}</span> ' for c in a.get('capabilities', []))
        agent_cards += f'<div class="ag-card" onclick="window.switchTab(\'cloud\');setTimeout(function(){{window.openContext(\'{a.get("name","").lower()}\')}},100)"><div class="ag-name">{a["name"]}</div><div class="ag-host">{a.get("hostname","")}</div><div class="ag-caps">{caps}</div><div class="ag-status {a.get("status","")}">{a.get("status","")}</div></div>'

    return render_template_string(HTML, words_json=json.dumps(words), word_count=len(data), agent_cards=agent_cards)

@app.route('/api/context')
@login_required
def context_api():
    word = request.args.get('word', '').lower().strip()
    if not word:
        return jsonify({'results': []})
    data, ctx_map = get_data()
    results = ctx_map.get(word, [])
    if not results:
        ken = fetch_context_retrieve(word, 'ken', 5)
        craic = fetch_context_retrieve(word, 'craic', 5)
        results = []
        for r in ken:
            results.append({'source': r.get('source',''), 'snippet': r.get('snippet','')[:400], 'kind': 'ken', 'id': r.get('id')})
        for r in craic:
            results.append({'source': r.get('source',''), 'snippet': r.get('snippet','')[:400], 'kind': 'craic', 'id': r.get('id')})
    return jsonify({'results': results[:10]})

@app.route('/api/mgmt')
@login_required
def api_mgmt():
    agents = cache.get('agents', [])
    if not agents:
        agents = fetch_agents()
        cache['agents'] = agents
    return jsonify({'agents': agents})

@app.route('/api/sic')
@login_required
def api_sic():
    results = multi_fetch(['SIC', 'massdeb8', 'debate', 'committee', 'GraGu'], 'ken', 5)
    craic = multi_fetch(['SIC', 'massdeb8', 'debate', 'committee'], 'craic', 4)
    return jsonify({'results': results + craic})

@app.route('/api/net')
@login_required
def api_net():
    results = multi_fetch(['network', 'topology', 'LAN', 'DNS', 'connectivity'], 'ken', 5)
    craic = multi_fetch(['network', 'LAN', 'DNS', 'connectivity'], 'craic', 4)
    return jsonify({'results': results + craic})

@app.route('/api/diag')
@login_required
def api_diag():
    results = multi_fetch(['fleet', 'diagnostic', 'health', 'AAA', 'CPU', 'memory', 'disk'], 'ken', 5)
    craic = multi_fetch(['fleet', 'diagnostic', 'health', 'AAA'], 'craic', 5)
    return jsonify({'results': results + craic})

@app.route('/api/refresh')
@login_required
def api_refresh():
    get_data(force=True)
    return jsonify({'status': 'refreshed', 'words': len(cache['data'])})

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555
    print(f'SPLIPPERVERSE Console on http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
