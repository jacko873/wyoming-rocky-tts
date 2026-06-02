#!/usr/bin/env python3

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional
import io
import tempfile
import subprocess

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import yaml

from .text_normalizer import TextNormalizer
from .rocky_styler import RockyStyler
from .cache_manager import CacheManager
from .config import Config

logger = logging.getLogger(__name__)

app = FastAPI(title="Rocky TTS Web UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to be initialized
config: Optional[Config] = None
normalizer: Optional[TextNormalizer] = None
cache_manager: Optional[CacheManager] = None

@app.on_event("startup")
async def startup():
    global config, normalizer, cache_manager
    
    config_path = Path.home() / '.rocky_tts' / 'config.yaml'
    config = Config.load(config_path)
    
    normalizer = TextNormalizer(Path(config.data_dir) / "overrides.yaml")
    cache_manager = CacheManager(Path(config.cache_dir))
    
    logger.info("Web UI started")

@app.get("/", response_class=HTMLResponse)
async def home():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Rocky TTS Control Panel</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --primary: #4CAF50;
            --danger: #f44336;
            --bg: #f5f5f5;
            --card-bg: white;
            --text: #333;
        }
        
        * { box-sizing: border-box; }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: var(--bg);
            color: var(--text);
        }
        
        h1 { 
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .emoji { font-size: 1.5em; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            margin-top: 0;
            border-bottom: 2px solid var(--primary);
            padding-bottom: 10px;
        }
        
        input[type="text"], textarea, select {
            width: 100%;
            padding: 10px;
            margin: 5px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        button {
            background: var(--primary);
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px 5px 5px 0;
            font-size: 14px;
            transition: background 0.3s;
        }
        
        button:hover { background: #45a049; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        
        .danger { background: var(--danger); }
        .danger:hover { background: #da190b; }
        
        .secondary { background: #666; }
        .secondary:hover { background: #555; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }
        
        th {
            background: var(--primary);
            color: white;
            font-weight: normal;
        }
        
        tr:nth-child(even) { background: #f9f9f9; }
        
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: 500;
        }
        
        .status.running { background: #4CAF50; color: white; }
        .status.stopped { background: #f44336; color: white; }
        
        .pipeline-stage {
            background: #f0f0f0;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid var(--primary);
            border-radius: 4px;
        }
        
        .pipeline-stage strong {
            color: var(--primary);
            display: block;
            margin-bottom: 5px;
        }
        
        pre {
            background: #f0f0f0;
            padding: 15px;
            overflow-x: auto;
            border-radius: 4px;
            font-size: 13px;
        }
        
        code {
            background: #f0f0f0;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 13px;
        }
        
        #audio-player {
            width: 100%;
            margin-top: 10px;
        }
        
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }
        
        .stat-box {
            background: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: var(--primary);
        }
        
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }
        
        .form-row {
            display: flex;
            gap: 10px;
            margin: 10px 0;
        }
        
        .form-row input { flex: 1; }
        
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <h1><span class="emoji">🗿</span> Rocky TTS Control Panel</h1>
    
    <div class="grid">
        <div class="card">
            <h2>⚡ Service Status</h2>
            <div id="status">
                <div class="spinner"></div> Loading...
            </div>
        </div>
        
        <div class="card">
            <h2>📊 Cache Statistics</h2>
            <div id="cache-stats">
                <div class="spinner"></div> Loading...
            </div>
            <button onclick="loadCacheStats()">🔄 Refresh</button>
            <button onclick="clearCache()" class="danger">🗑️ Clear All Cache</button>
        </div>
    </div>
    
    <div class="card">
        <h2>🎤 Test Text Processing</h2>
        <form id="test-form">
            <textarea name="text" placeholder="Enter text to test..." rows="3">The temperature is 72°F with 30% humidity at 3:45 PM.</textarea>
            <div style="margin: 10px 0;">
                <label style="display: flex; align-items: center; gap: 5px;">
                    <input type="checkbox" name="use_style" checked>
                    Apply Rocky Style
                </label>
            </div>
            <button type="submit">🔍 Process Text</button>
            <button type="button" onclick="synthesizeTest()">🔊 Generate Audio</button>
            <button type="button" onclick="document.querySelector('[name=text]').value=''" class="secondary">Clear</button>
        </form>
        <div id="pipeline-result"></div>
        <audio id="audio-player" controls style="display:none;"></audio>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>💾 Recent Cache Entries</h2>
            <div id="cache-entries">Loading...</div>
        </div>
        
        <div class="card">
            <h2>📝 Pronunciation Overrides</h2>
            <form id="override-form" class="form-row">
                <input type="text" name="original" placeholder="Original text">
                <input type="text" name="replacement" placeholder="Spoken as...">
                <button type="submit">Add</button>
            </form>
            <div id="overrides-list">Loading...</div>
        </div>
    </div>
    
    <div class="card">
        <h2>⚙️ Configuration</h2>
        <button onclick="loadConfig()">🔄 Reload</button>
        <button onclick="downloadConfig()" class="secondary">💾 Download</button>
        <pre id="config-display">Loading...</pre>
    </div>

    <script>
        let isProcessing = false;
        
        async function loadStatus() {
            try {
                const resp = await fetch('/api/status');
                const data = await resp.json();
                document.getElementById('status').innerHTML = `
                    <div style="margin: 20px 0;">
                        <span class="status ${data.running ? 'running' : 'stopped'}">
                            ${data.running ? '✓ Running' : '✗ Stopped'}
                        </span>
                    </div>
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-value">${data.wyoming_port || 10202}</div>
                            <div class="stat-label">Wyoming Port</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${data.web_port || 8088}</div>
                            <div class="stat-label">Web UI Port</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${data.style_mode || 'rules'}</div>
                            <div class="stat-label">Style Mode</div>
                        </div>
                    </div>
                `;
            } catch(e) {
                document.getElementById('status').innerHTML = '<span class="status stopped">Error loading status</span>';
            }
        }
        
        async function loadCacheStats() {
            try {
                const resp = await fetch('/api/cache/stats');
                const data = await resp.json();
                document.getElementById('cache-stats').innerHTML = `
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-value">${data.total_entries}</div>
                            <div class="stat-label">Total Entries</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${data.total_hits}</div>
                            <div class="stat-label">Total Hits</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${(data.cache_size_mb || 0).toFixed(1)}</div>
                            <div class="stat-label">Size (MB)</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${(data.avg_synthesis_ms || 0).toFixed(0)}</div>
                            <div class="stat-label">Avg Time (ms)</div>
                        </div>
                    </div>
                `;
                
                if (data.top_entries && data.top_entries.length > 0) {
                    let html = '<table><tr><th>Text</th><th>Hits</th><th>Action</th></tr>';
                    for (const entry of data.top_entries.slice(0, 5)) {
                        const text = entry.raw_text.substring(0, 40);
                        html += `<tr>
                            <td>${text}${entry.raw_text.length > 40 ? '...' : ''}</td>
                            <td style="text-align: center;">${entry.hit_count}</td>
                            <td><button onclick="deleteCache('${entry.cache_key}')" class="danger" style="padding: 5px 10px; font-size: 12px;">Delete</button></td>
                        </tr>`;
                    }
                    html += '</table>';
                    document.getElementById('cache-entries').innerHTML = html;
                } else {
                    document.getElementById('cache-entries').innerHTML = '<p style="color: #666;">No cache entries yet</p>';
                }
            } catch(e) {
                document.getElementById('cache-stats').innerHTML = 'Error loading cache stats';
            }
        }
        
        async function clearCache() {
            if (!confirm('Are you sure you want to clear all cache entries?')) return;
            try {
                await fetch('/api/cache/clear', { method: 'POST' });
                alert('Cache cleared successfully');
                loadCacheStats();
            } catch(e) {
                alert('Error clearing cache');
            }
        }
        
        async function deleteCache(key) {
            try {
                await fetch(`/api/cache/${key}`, { method: 'DELETE' });
                loadCacheStats();
            } catch(e) {
                alert('Error deleting cache entry');
            }
        }
        
        async function loadOverrides() {
            try {
                const resp = await fetch('/api/overrides');
                const data = await resp.json();
                
                if (Object.keys(data).length === 0) {
                    document.getElementById('overrides-list').innerHTML = '<p style="color: #666;">No overrides configured</p>';
                    return;
                }
                
                let html = '<table><tr><th>Original</th><th>Replacement</th><th>Action</th></tr>';
                for (const [original, replacement] of Object.entries(data)) {
                    html += `<tr>
                        <td>${original}</td>
                        <td>${replacement}</td>
                        <td><button onclick="deleteOverride('${original}')" class="danger" style="padding: 5px 10px; font-size: 12px;">Delete</button></td>
                    </tr>`;
                }
                html += '</table>';
                document.getElementById('overrides-list').innerHTML = html;
            } catch(e) {
                document.getElementById('overrides-list').innerHTML = 'Error loading overrides';
            }
        }
        
        async function deleteOverride(key) {
            try {
                await fetch(`/api/overrides/${encodeURIComponent(key)}`, { method: 'DELETE' });
                loadOverrides();
            } catch(e) {
                alert('Error deleting override');
            }
        }
        
        async function loadConfig() {
            try {
                const resp = await fetch('/api/config');
                const data = await resp.json();
                document.getElementById('config-display').textContent = JSON.stringify(data, null, 2);
            } catch(e) {
                document.getElementById('config-display').textContent = 'Error loading config';
            }
        }
        
        function downloadConfig() {
            window.open('/api/config/download', '_blank');
        }
        
        document.getElementById('test-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            if (isProcessing) return;
            
            isProcessing = true;
            const button = e.target.querySelector('button[type="submit"]');
            button.disabled = true;
            button.innerHTML = '🔍 Processing... <div class="spinner" style="display: inline-block;"></div>';
            
            try {
                const formData = new FormData(e.target);
                const resp = await fetch('/api/test', {
                    method: 'POST',
                    body: formData
                });
                const result = await resp.json();
                
                let html = '<h3>Text Processing Pipeline</h3>';
                html += '<div class="pipeline-stage"><strong>Original Text:</strong>' + result.original + '</div>';
                html += '<div class="pipeline-stage"><strong>After Rocky Style:</strong>' + result.styled + '</div>';
                html += '<div class="pipeline-stage"><strong>After Normalization:</strong>' + result.normalized + '</div>';
                html += '<div class="pipeline-stage"><strong>Cache Key:</strong><code>' + result.cache_key.substring(0, 16) + '...</code></div>';
                
                document.getElementById('pipeline-result').innerHTML = html;
            } finally {
                isProcessing = false;
                button.disabled = false;
                button.innerHTML = '🔍 Process Text';
            }
        });
        
        document.getElementById('override-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            if (!formData.get('original') || !formData.get('replacement')) {
                alert('Please fill in both fields');
                return;
            }
            
            try {
                await fetch('/api/overrides', {
                    method: 'POST',
                    body: formData
                });
                loadOverrides();
                e.target.reset();
            } catch(e) {
                alert('Error adding override');
            }
        });
        
        async function synthesizeTest() {
            if (isProcessing) return;
            
            const text = document.querySelector('[name="text"]').value;
            const useStyle = document.querySelector('[name="use_style"]').checked;
            
            if (!text) {
                alert('Please enter some text to synthesize');
                return;
            }
            
            isProcessing = true;
            const button = document.querySelector('button[onclick="synthesizeTest()"]');
            button.disabled = true;
            button.innerHTML = '🔊 Generating... <div class="spinner" style="display: inline-block;"></div>';
            
            try {
                const resp = await fetch('/api/synthesize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, use_style: useStyle })
                });
                
                if (resp.ok) {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const player = document.getElementById('audio-player');
                    player.src = url;
                    player.style.display = 'block';
                    player.play();
                } else {
                    alert('Error generating audio. Check if the TTS service is running.');
                }
            } finally {
                isProcessing = false;
                button.disabled = false;
                button.innerHTML = '🔊 Generate Audio';
            }
        }
        
        // Initial load
        loadStatus();
        loadCacheStats();
        loadOverrides();
        loadConfig();
        
        // Auto-refresh status
        setInterval(loadStatus, 30000);
    </script>
</body>
</html>
'''

@app.get("/api/status")
async def get_status():
    global config
    
    import subprocess
    try:
        result = subprocess.run(['systemctl', 'is-active', 'wyoming-rocky'], 
                              capture_output=True, text=True)
        running = result.stdout.strip() == 'active'
    except:
        running = False
    
    return {
        "running": running,
        "wyoming_port": config.wyoming_port,
        "web_port": config.web_port,
        "style_mode": config.style_mode
    }

@app.get("/api/cache/stats")
async def get_cache_stats():
    global cache_manager
    
    stats = cache_manager.get_stats()
    top_entries = cache_manager.get_top_entries(10)
    
    return {
        **stats,
        "top_entries": top_entries
    }

@app.post("/api/cache/clear")
async def clear_cache():
    global cache_manager
    cache_manager.clear()
    return {"status": "cleared"}

@app.delete("/api/cache/{cache_key}")
async def delete_cache_entry(cache_key: str):
    global cache_manager
    
    if cache_manager.delete(cache_key):
        return {"status": "deleted"}
    else:
        raise HTTPException(status_code=404, detail="Cache entry not found")

@app.get("/api/overrides")
async def get_overrides():
    global config
    
    overrides_file = Path(config.data_dir) / "overrides.yaml"
    if overrides_file.exists():
        with open(overrides_file) as f:
            return yaml.safe_load(f) or {}
    return {}

@app.post("/api/overrides")
async def add_override(original: str = Form(...), replacement: str = Form(...)):
    global config, normalizer
    
    overrides_file = Path(config.data_dir) / "overrides.yaml"
    
    overrides = {}
    if overrides_file.exists():
        with open(overrides_file) as f:
            overrides = yaml.safe_load(f) or {}
    
    overrides[original] = replacement
    
    with open(overrides_file, 'w') as f:
        yaml.dump(overrides, f, allow_unicode=True)
    
    normalizer.load_overrides(overrides_file)
    
    return {"status": "added"}

@app.delete("/api/overrides/{key}")
async def delete_override(key: str):
    global config, normalizer
    
    overrides_file = Path(config.data_dir) / "overrides.yaml"
    
    overrides = {}
    if overrides_file.exists():
        with open(overrides_file) as f:
            overrides = yaml.safe_load(f) or {}
    
    if key in overrides:
        del overrides[key]
        with open(overrides_file, 'w') as f:
            yaml.dump(overrides, f, allow_unicode=True)
        
        normalizer.load_overrides(overrides_file)
    
    return {"status": "deleted"}

@app.get("/api/config")
async def get_config():
    global config
    return config.__dict__

@app.get("/api/config/download")
async def download_config():
    global config
    
    config_yaml = yaml.dump(config.__dict__, default_flow_style=False)
    
    return StreamingResponse(
        io.BytesIO(config_yaml.encode()),
        media_type="application/x-yaml",
        headers={"Content-Disposition": "attachment; filename=config.yaml"}
    )

@app.post("/api/test")
async def test_text(text: str = Form(...), use_style: bool = Form(False)):
    global config, normalizer
    
    styler = RockyStyler("rules" if use_style else "off", config)
    styled = styler.apply_style(text)
    normalized = normalizer.normalize(styled)
    
    import hashlib
    cache_key = hashlib.sha256(f"{text}:{'rules' if use_style else 'off'}:test".encode()).hexdigest()
    
    return {
        "original": text,
        "styled": styled,
        "normalized": normalized,
        "cache_key": cache_key
    }

@app.post("/api/synthesize")
async def synthesize(request: Request):
    data = await request.json()
    text = data.get("text", "")
    use_style = data.get("use_style", True)
    
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    
    # Use the test command if available
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        try:
            style_arg = "--style rules" if use_style else "--style off"
            result = subprocess.run(
                f'/usr/local/bin/test-rocky-tts "{text}" {style_arg}',
                shell=True,
                capture_output=True,
                timeout=30
            )
            
            # Find the generated WAV file
            wav_files = list(Path("/tmp").glob("rocky_test_*.wav"))
            if wav_files:
                wav_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                with open(wav_files[0], 'rb') as f:
                    audio_data = f.read()
                
                # Clean up
                for wav in wav_files:
                    try:
                        wav.unlink()
                    except:
                        pass
                
                return StreamingResponse(
                    io.BytesIO(audio_data),
                    media_type="audio/wav",
                    headers={"Content-Disposition": "attachment; filename=test.wav"}
                )
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
    
    raise HTTPException(status_code=500, detail="Synthesis failed")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8088)
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()