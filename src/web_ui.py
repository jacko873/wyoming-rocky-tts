#!/usr/bin/env python3

import os
import sys
import json
import logging
import traceback
from pathlib import Path
from typing import Optional
import io
import tempfile
import subprocess

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import yaml
import requests

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
    allow_credentials=True,
)

# Add middleware for proxy compatibility
@app.middleware("http")
async def proxy_middleware(request: Request, call_next):
    # Trust proxy headers
    if "x-forwarded-host" in request.headers:
        request.scope["server"] = (request.headers["x-forwarded-host"], None)
    if "x-forwarded-proto" in request.headers:
        request.scope["scheme"] = request.headers["x-forwarded-proto"]
    
    # Add headers for proxy compatibility
    response = await call_next(request)
    
    # Disable CSRF protection for proxy environments
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Add cache control to prevent stale CSRF tokens
    if request.url.path.startswith("api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    
    return response

# Global variables to be initialized
config: Optional[Config] = None
normalizer: Optional[TextNormalizer] = None
cache_manager: Optional[CacheManager] = None
rocky_tts: Optional[object] = None

@app.on_event("startup")
async def startup():
    global config, normalizer, cache_manager, rocky_tts
    
    # Load environment variables from .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        logger.info("Loading environment variables from .env file")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
                    logger.info(f"Loaded env var: {key.strip()}")
    
    config_path = Path.home() / '.rocky_tts' / 'config.yaml'
    config = Config.load(config_path)
    
    normalizer = TextNormalizer(Path(config.data_dir) / "overrides.yaml")
    cache_manager = CacheManager(Path(config.cache_dir))
    
    # Initialize Rocky TTS instance once during startup
    try:
        from src.wyoming_server import RockyTTS
        logger.info("Loading Rocky TTS model...")
        rocky_tts = RockyTTS(config)
        logger.info("Rocky TTS model loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load Rocky TTS: {e}")
        rocky_tts = None
    
    logger.info("Web UI started")

@app.get("/", response_class=HTMLResponse)
async def home():
    """
    Web UI home page - uses relative URLs for proxy compatibility.
    All API calls use 'api/*' paths (not absolute URLs) so this works
    behind reverse proxies, subpaths, and different domains.
    """
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Rocky TTS Control Panel</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="referrer" content="same-origin">
    <link rel="icon" type="image/jpeg" href="favicon.ico">
    <!-- 
    IMPORTANT: All URLs in this page use relative paths (e.g., 'api/status') 
    for proxy compatibility. Do not use absolute URLs like 'http://localhost:8088/api/...'
    -->
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
    <h1><img src="rocky-image.jpg" style="height: 40px; width: 40px; object-fit: cover; border-radius: 50%; margin-right: 10px; vertical-align: middle;"> Rocky TTS Control Panel</h1>
    
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
    
    <div class="card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px;">
        <h2 style="border-bottom-color: white; color: white;">🎤 Test Rocky TTS - See & Hear the Transformation</h2>
        <form id="test-form">
            <textarea name="text" placeholder="Enter any text to transform into Rocky's speaking style..." rows="4" style="font-size: 16px; width: 100%; padding: 12px;">The temperature is 72°F and the lights are turned on. Would you like me to adjust anything?</textarea>
            
            <div style="margin: 15px 0; display: flex; gap: 20px; align-items: center; flex-wrap: wrap;">
                <label style="display: flex; align-items: center; gap: 5px;">
                    Rocky Style:
                    <select name="style_mode" style="padding: 5px; border-radius: 4px; margin-left: 8px;">
                        <option value="off">Off</option>
                        <option value="rules" selected>Rules-based</option>
                        <option value="openai">🤖 OpenAI Mode</option>
                    </select>
                </label>
                <label style="display: flex; align-items: center; gap: 5px;">
                    Voice Speed:
                    <select name="voice_speed" style="padding: 5px; border-radius: 4px;">
                        <option value="120">Slow</option>
                        <option value="150" selected>Normal</option>
                        <option value="180">Fast</option>
                    </select>
                </label>
            </div>
            
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                <button type="submit" style="background: white; color: #667eea; font-weight: bold;">🎯 Transform Text</button>
                <button type="button" onclick="synthesizeTest()" style="background: white; color: #667eea; font-weight: bold;">🔊 Generate & Play Audio</button>
                <button type="button" onclick="clearTest()" class="secondary">🗑️ Clear All</button>
            </div>
        </form>
        
        <div id="pipeline-result" style="margin-top: 20px;"></div>
        
        <div id="audio-section" style="display: none; margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px;">
            <h4 style="margin-top: 0; color: white;">🔊 Audio Output:</h4>
            <audio id="audio-player" controls style="width: 100%; margin: 10px 0;"></audio>
            <div id="audio-status" style="margin-top: 10px; font-size: 14px;"></div>
        </div>
        
        <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.3);">
            <h4 style="color: white;">📚 Quick Examples (click to try):</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                <button onclick="setExample('I don\\'t understand what you mean')" class="example-btn" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid white; padding: 10px; border-radius: 4px; cursor: pointer;">
                    "I don't understand"
                </button>
                <button onclick="setExample('The lights have been turned on successfully')" class="example-btn" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid white; padding: 10px; border-radius: 4px; cursor: pointer;">
                    "Lights turned on"
                </button>
                <button onclick="setExample('That\\'s absolutely amazing!')" class="example-btn" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid white; padding: 10px; border-radius: 4px; cursor: pointer;">
                    "That's amazing!"
                </button>
                <button onclick="setExample('What do you want me to do?')" class="example-btn" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid white; padding: 10px; border-radius: 4px; cursor: pointer;">
                    "What do you want?"
                </button>
                <button onclick="setExample('Unable to connect to the device')" class="example-btn" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid white; padding: 10px; border-radius: 4px; cursor: pointer;">
                    "Can't connect"
                </button>
                <button onclick="setExample('Task completed successfully')" class="example-btn" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid white; padding: 10px; border-radius: 4px; cursor: pointer;">
                    "Task done"
                </button>
            </div>
        </div>
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
                const resp = await fetch('api/status');
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
                const resp = await fetch('api/cache/stats');
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
                await fetch('api/cache/clear', { method: 'POST' });
                alert('Cache cleared successfully');
                loadCacheStats();
            } catch(e) {
                alert('Error clearing cache');
            }
        }
        
        async function deleteCache(key) {
            try {
                await fetch(`api/cache/${key}`, { method: 'DELETE' });
                loadCacheStats();
            } catch(e) {
                alert('Error deleting cache entry');
            }
        }
        
        async function loadOverrides() {
            try {
                const resp = await fetch('api/overrides');
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
                await fetch(`api/overrides/${encodeURIComponent(key)}`, { method: 'DELETE' });
                loadOverrides();
            } catch(e) {
                alert('Error deleting override');
            }
        }
        
        async function loadConfig() {
            try {
                const resp = await fetch('api/config');
                const data = await resp.json();
                document.getElementById('config-display').textContent = JSON.stringify(data, null, 2);
            } catch(e) {
                document.getElementById('config-display').textContent = 'Error loading config';
            }
        }
        
        function downloadConfig() {
            window.open('api/config/download', '_blank');
        }
        
        function setExample(text) {
            document.querySelector('[name="text"]').value = text;
            document.getElementById('test-form').dispatchEvent(new Event('submit'));
        }
        
        function clearTest() {
            document.querySelector('[name="text"]').value = '';
            document.getElementById('pipeline-result').innerHTML = '';
            document.getElementById('audio-section').style.display = 'none';
            document.getElementById('audio-player').pause();
        }
        
        document.getElementById('test-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            if (isProcessing) return;
            
            isProcessing = true;
            const button = e.target.querySelector('button[type="submit"]');
            button.disabled = true;
            button.innerHTML = '🎯 Transforming... <div class="spinner" style="display: inline-block;"></div>';
            
            try {
                const formData = new FormData(e.target);
                const resp = await fetch('api/test', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const result = await resp.json();
                
                // Check if there's an error in the response
                if (result.error) {
                    let html = '<div style="background: #fee; color: #333; padding: 20px; border-radius: 8px; margin-top: 10px; border: 1px solid #fcc;">';
                    html += '<h3 style="margin-top: 0; color: #d00;">⚠️ Error in Text Transformation:</h3>';
                    html += '<div style="margin: 10px 0; color: #800;">' + result.error + '</div>';
                    if (result.error_detail) {
                        html += '<div style="margin: 10px 0; color: #666; font-size: 14px;">' + result.error_detail + '</div>';
                    }
                    html += '<div style="margin: 15px 0; padding: 10px; background: #fff; border-left: 3px solid #f44;">';
                    html += '<strong>Original Text:</strong><br>' + result.original;
                    html += '</div>';
                    if (result.actual_mode) {
                        html += '<div style="margin-top: 10px; padding: 10px; background: #ffc; border-radius: 4px;">';
                        html += '<small>Note: Mode fell back to <strong>' + result.actual_mode + '</strong> due to the error.</small>';
                        html += '</div>';
                    }
                    html += '</div>';
                    document.getElementById('pipeline-result').innerHTML = html;
                    return;
                }
                
                let html = '<div style="background: white; color: #333; padding: 20px; border-radius: 8px; margin-top: 10px;">';
                html += '<h3 style="margin-top: 0; color: #667eea;">📝 Text Transformation Results:</h3>';
                
                // Show actual mode if different from requested
                if (result.actual_mode && result.actual_mode !== result.mode) {
                    html += '<div style="margin: 10px 0; padding: 10px; background: #ffc; border-radius: 4px;">';
                    html += '<small>ℹ️ Using <strong>' + result.actual_mode + '</strong> mode (requested ' + result.mode + ' but fell back)</small>';
                    html += '</div>';
                }
                
                html += '<div class="pipeline-stage" style="margin: 15px 0; padding: 15px; background: #f0f0f0; border-left: 3px solid #667eea;">';
                html += '<strong style="color: #667eea; display: block; margin-bottom: 5px;">Original Text:</strong>';
                html += '<div style="font-size: 16px; line-height: 1.5;">' + result.original + '</div>';
                html += '</div>';
                html += '<div class="pipeline-stage" style="margin: 15px 0; padding: 15px; background: #f0f0f0; border-left: 3px solid #764ba2;">';
                html += '<strong style="color: #764ba2; display: block; margin-bottom: 5px;">🗿 Rocky Style:</strong>';
                html += '<div style="font-size: 18px; line-height: 1.5; font-weight: bold;">' + result.styled + '</div>';
                html += '</div>';
                html += '<div class="pipeline-stage" style="margin: 15px 0; padding: 15px; background: #f0f0f0; border-left: 3px solid #667eea;">';
                html += '<strong style="color: #667eea; display: block; margin-bottom: 5px;">🔧 Normalized for Speech:</strong>';
                html += '<div style="font-size: 16px; line-height: 1.5;">' + result.normalized + '</div>';
                html += '</div>';
                html += '<div style="margin-top: 15px; padding: 10px; background: #e8f4fd; border-radius: 4px;">';
                html += '<small>Cache Key: <code>' + (result.cache_key ? result.cache_key.substring(0, 16) + '...' : 'N/A') + '</code></small>';
                html += '</div>';
                html += '</div>';
                
                document.getElementById('pipeline-result').innerHTML = html;
                
                // Auto-generate audio if Rocky style is enabled
                if (document.querySelector('[name="style_mode"]').value !== 'off') {
                    setTimeout(() => synthesizeTest(), 500);
                }
            } catch(error) {
                console.error('Error during text transformation:', error);
                let html = '<div style="background: #fee; color: #333; padding: 20px; border-radius: 8px; margin-top: 10px; border: 1px solid #fcc;">';
                html += '<h3 style="margin-top: 0; color: #d00;">⚠️ Network or Server Error:</h3>';
                html += '<div style="margin: 10px 0; color: #800;">' + error.message + '</div>';
                html += '<div style="margin: 10px 0; color: #666; font-size: 14px;">Please check the server logs or try again.</div>';
                html += '</div>';
                document.getElementById('pipeline-result').innerHTML = html;
            } finally {
                isProcessing = false;
                button.disabled = false;
                button.innerHTML = '🎯 Transform Text';
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
                await fetch('api/overrides', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                loadOverrides();
                e.target.reset();
            } catch(e) {
                alert('Error adding override');
            }
        });
        
        async function synthesizeTest() {
            if (isProcessing) return;
            
            // Get the styled text if available, otherwise use the input text
            const styledTextElement = document.querySelector('.pipeline-stage:nth-child(2) div:last-child');
            const text = styledTextElement ? styledTextElement.textContent : document.querySelector('[name="text"]').value;
            const styleMode = document.querySelector('[name="style_mode"]').value;
            const voiceSpeed = document.querySelector('[name="voice_speed"]').value;
            
            if (!text) {
                alert('Please enter and transform some text first');
                return;
            }
            
            isProcessing = true;
            const button = document.querySelector('button[onclick="synthesizeTest()"]');
            button.disabled = true;
            button.innerHTML = '🔊 Generating Audio... <div class="spinner" style="display: inline-block;"></div>';
            
            // Show audio section
            const audioSection = document.getElementById('audio-section');
            audioSection.style.display = 'block';
            document.getElementById('audio-status').innerHTML = '⏳ Generating audio with Rocky voice...';
            
            try {
                const resp = await fetch('api/synthesize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        text: text, 
                        style_mode: styleMode,
                        voice_speed: voiceSpeed
                    })
                });
                
                if (resp.ok) {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const player = document.getElementById('audio-player');
                    player.src = url;
                    player.style.display = 'block';
                    
                    // Check if using actual YourTTS
                    const ttsEngine = resp.headers.get('X-TTS-Engine');
                    if (ttsEngine && ttsEngine.includes('YourTTS')) {
                        document.getElementById('audio-status').innerHTML = '✅ Audio generated with YourTTS Rocky voice! Click play to hear.';
                    } else {
                        document.getElementById('audio-status').innerHTML = '✅ Audio ready! Click play to hear Rocky speak.';
                    }
                    
                    // Auto-play
                    player.play().catch(e => {
                        document.getElementById('audio-status').innerHTML += ' (Click the play button if auto-play was blocked)';
                    });
                } else {
                    const errorText = await resp.text();
                    let errorMsg = '❌ ';
                    if (resp.status === 503) {
                        errorMsg += 'YourTTS model not loaded. Please ensure Wyoming Rocky TTS service is running.';
                    } else if (resp.status === 500) {
                        errorMsg += 'TTS generation failed. Check the service logs for details.';
                    } else {
                        errorMsg += 'Error generating audio: ' + errorText;
                    }
                    document.getElementById('audio-status').innerHTML = errorMsg;
                }
            } catch(e) {
                document.getElementById('audio-status').innerHTML = '❌ Failed to generate audio: ' + e;
            } finally {
                isProcessing = false;
                button.disabled = false;
                button.innerHTML = '🔊 Generate & Play Audio';
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

@app.get("/favicon.ico")
async def get_favicon():
    """Serve Rocky plush favicon"""
    # Look for the icon in the data directory
    rocky_icon_path = Path("data/rocky_icon.jpg")
    
    # If not found locally, try to download it
    if not rocky_icon_path.exists():
        try:
            response = requests.get("https://media.gamestop.com/i/gamestop/20034410/Project-Hail-Mary-Rocky-8-in-Collector-Plush?w=32&h=32&fmt=auto", timeout=5)
            if response.status_code == 200:
                with open(rocky_icon_path, "wb") as f:
                    f.write(response.content)
        except:
            pass  # Fallback to empty icon if download fails
    
    # Serve the icon if it exists
    if rocky_icon_path.exists():
        with open(rocky_icon_path, "rb") as f:
            return Response(content=f.read(), media_type="image/jpeg")
    
    # Fallback empty icon
    return Response(content=b"", media_type="image/x-icon")

@app.get("/rocky-image.jpg")
async def get_rocky_image():
    """Serve Rocky plush image for the page"""
    # Look for a larger version of the image
    rocky_image_path = Path("data/rocky_image.jpg")
    
    # If not found locally, try to download a larger version
    if not rocky_image_path.exists():
        try:
            response = requests.get("https://media.gamestop.com/i/gamestop/20034410/Project-Hail-Mary-Rocky-8-in-Collector-Plush?w=128&h=128&fmt=auto", timeout=5)
            if response.status_code == 200:
                with open(rocky_image_path, "wb") as f:
                    f.write(response.content)
        except:
            # Fallback to the smaller icon if download fails
            rocky_image_path = Path("data/rocky_icon.jpg")
    
    # Serve the image if it exists
    if rocky_image_path.exists():
        with open(rocky_image_path, "rb") as f:
            return Response(content=f.read(), media_type="image/jpeg")
    
    # Fallback empty response
    return Response(content=b"", media_type="image/jpeg")

@app.get("/api/status")
async def get_status():
    global config
    
    import socket
    import asyncio
    
    # Check if Wyoming server is actually responding on its port
    wyoming_running = False
    try:
        # Try to connect to Wyoming server port
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection('localhost', config.wyoming_port),
            timeout=2.0
        )
        wyoming_running = True
        writer.close()
        await writer.wait_closed()
    except:
        wyoming_running = False
    
    return {
        "running": wyoming_running,
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
async def test_text(text: str = Form(...), style_mode: str = Form("rules")):
    global config, normalizer
    
    try:
        # Validate style mode
        if style_mode not in ["off", "rules", "openai"]:
            style_mode = "rules"
        
        # Log the request
        logger.info(f"Test text requested - mode: {style_mode}, text: {text[:50]}...")
        
        styler = RockyStyler(style_mode, config)
        styled = styler.apply_style(text)
        normalized = normalizer.normalize(styled)
        
        import hashlib
        cache_key = hashlib.sha256(f"{text}:{style_mode}:test".encode()).hexdigest()
        
        return {
            "original": text,
            "styled": styled,
            "normalized": normalized,
            "cache_key": cache_key,
            "mode": style_mode,
            "actual_mode": styler.mode  # Return the actual mode used (may fallback)
        }
    except Exception as e:
        logger.error(f"Error in test_text endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return partial results with error info
        return {
            "original": text,
            "styled": text,  # Return original text on error
            "normalized": text,
            "cache_key": "",
            "mode": style_mode,
            "error": str(e),
            "error_detail": "Check server logs for more details"
        }

@app.post("/api/synthesize")
async def synthesize(request: Request):
    data = await request.json()
    text = data.get("text", "")
    style_mode = data.get("style_mode", data.get("use_style", True))  # Support old and new format
    voice_speed = data.get("voice_speed", "150")
    
    # Convert legacy boolean to style mode
    if isinstance(style_mode, bool):
        style_mode = "rules" if style_mode else "off"
    elif style_mode not in ["off", "rules", "openai"]:
        style_mode = "rules"
    
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    
    # Use the global Rocky TTS instance for faster synthesis
    global rocky_tts
    
    if rocky_tts is None:
        raise HTTPException(status_code=503, detail="Rocky TTS not available")
    
    try:
        # Temporarily adjust configuration for this request
        original_style_mode = rocky_tts.config.style_mode
        original_audio_rate = rocky_tts.config.audio_rate

        try:
            # Override style mode based on request
            rocky_tts.config.style_mode = style_mode

            # Adjust audio rate based on voice speed
            speed_map = {
                "120": 20000,  # Slow
                "150": 22050,  # Normal
                "180": 24000   # Fast
            }
            rocky_tts.config.audio_rate = speed_map.get(voice_speed, 22050)

            # Update the styler's mode (initializes the OpenAI client if needed)
            rocky_tts.styler.set_mode(style_mode)

            # Generate audio using the cached TTS instance
            audio_data = rocky_tts.synthesize(text, use_cache=True)
        finally:
            # Restore original configuration
            rocky_tts.config.style_mode = original_style_mode
            rocky_tts.config.audio_rate = original_audio_rate
            rocky_tts.styler.set_mode(original_style_mode)
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=rocky_yourtts.wav",
                "X-TTS-Engine": "YourTTS with Rocky voice"
            }
        )
        
    except ImportError as e:
        # TTS modules not fully installed, try the test command
        logger.warning(f"TTS modules not available: {e}")
        
        # Try using the test-rocky-tts command if installed
        if Path('/usr/local/bin/test-rocky-tts').exists():
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
                
                try:
                    style_arg = "--style rules" if style_mode != "off" else "--style off"
                    result = subprocess.run(
                        f'/usr/local/bin/test-rocky-tts "{text}" {style_arg} --output {tmp_path}',
                        shell=True,
                        capture_output=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0 and Path(tmp_path).exists():
                        with open(tmp_path, 'rb') as f:
                            audio_data = f.read()
                        
                        return StreamingResponse(
                            io.BytesIO(audio_data),
                            media_type="audio/wav",
                            headers={"Content-Disposition": "attachment; filename=rocky.wav"}
                        )
                except Exception:
                    pass
                finally:
                    try:
                        Path(tmp_path).unlink()
                    except:
                        pass
        
        raise HTTPException(
            status_code=503, 
            detail="YourTTS model not available. Please ensure the full Wyoming Rocky TTS is installed."
        )
        
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"TTS synthesis failed: {str(e)}. Make sure YourTTS model is installed and configured."
        )

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8088)
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()