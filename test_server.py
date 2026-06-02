#!/usr/bin/env python3
"""
Standalone test server for Wyoming Rocky TTS
Test text transformations and hear audio output
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.rocky_styler import RockyStyler
from src.text_normalizer import TextNormalizer

# Simple HTML interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Rocky TTS Test Interface</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        h1 {
            color: #333;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        
        .input-section {
            background: #f7f7f7;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            resize: vertical;
            min-height: 100px;
            box-sizing: border-box;
        }
        
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        button {
            flex: 1;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
        }
        
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .secondary {
            background: #6c757d;
        }
        
        .results {
            margin-top: 30px;
        }
        
        .result-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            display: none;
        }
        
        .result-box.show {
            display: block;
        }
        
        .result-label {
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .result-text {
            font-size: 18px;
            color: #333;
            line-height: 1.5;
        }
        
        #audio-player {
            width: 100%;
            margin-top: 20px;
            display: none;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        
        .loading.show {
            display: block;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .examples {
            margin-top: 30px;
            padding: 20px;
            background: #f0f0f0;
            border-radius: 10px;
        }
        
        .examples h3 {
            margin-top: 0;
            color: #333;
        }
        
        .example {
            background: white;
            padding: 10px 15px;
            margin: 8px 0;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .example:hover {
            background: #e9ecef;
        }
        
        .emoji {
            font-size: 1.5em;
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1><span class="emoji">🗿</span> Rocky TTS Test Interface</h1>
        <p class="subtitle">Test Rocky-style text transformations and hear the results</p>
        
        <div class="input-section">
            <textarea id="input-text" placeholder="Enter any text to transform into Rocky's speaking style...">The temperature is 72°F and the lights are turned on. Would you like me to adjust anything?</textarea>
            <div class="button-group">
                <button onclick="processText()">🎯 Transform Text</button>
                <button onclick="generateAudio()" class="secondary">🔊 Generate Audio</button>
                <button onclick="clearAll()" class="secondary">🗑️ Clear</button>
            </div>
        </div>
        
        <div class="loading">
            <div class="spinner"></div>
            <p>Processing...</p>
        </div>
        
        <div class="results">
            <div id="original-box" class="result-box">
                <div class="result-label">📝 Original Text</div>
                <div class="result-text" id="original-text"></div>
            </div>
            
            <div id="rocky-box" class="result-box">
                <div class="result-label">🗿 Rocky Style</div>
                <div class="result-text" id="rocky-text"></div>
            </div>
            
            <div id="normalized-box" class="result-box">
                <div class="result-label">🔧 Normalized for TTS</div>
                <div class="result-text" id="normalized-text"></div>
            </div>
            
            <audio id="audio-player" controls></audio>
        </div>
        
        <div class="examples">
            <h3>📚 Example Phrases (click to try)</h3>
            <div class="example" onclick="setExample('I don\\'t understand what you mean')">
                "I don't understand what you mean"
            </div>
            <div class="example" onclick="setExample('The living room lights have been turned on successfully')">
                "The living room lights have been turned on successfully"
            </div>
            <div class="example" onclick="setExample('That\\'s absolutely amazing!')">
                "That's absolutely amazing!"
            </div>
            <div class="example" onclick="setExample('The temperature is 68°F with 45% humidity')">
                "The temperature is 68°F with 45% humidity"
            </div>
            <div class="example" onclick="setExample('Would you like me to turn off all the lights?')">
                "Would you like me to turn off all the lights?"
            </div>
            <div class="example" onclick="setExample('Unable to connect to the smart device')">
                "Unable to connect to the smart device"
            </div>
            <div class="example" onclick="setExample('It\\'s 3:45 PM and the weather is nice')">
                "It's 3:45 PM and the weather is nice"
            </div>
        </div>
    </div>

    <script>
        function setExample(text) {
            document.getElementById('input-text').value = text;
            processText();
        }
        
        function clearAll() {
            document.getElementById('input-text').value = '';
            document.querySelectorAll('.result-box').forEach(box => box.classList.remove('show'));
            document.getElementById('audio-player').style.display = 'none';
        }
        
        async function processText() {
            const text = document.getElementById('input-text').value;
            if (!text.trim()) {
                alert('Please enter some text');
                return;
            }
            
            document.querySelector('.loading').classList.add('show');
            
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                
                const data = await response.json();
                
                document.getElementById('original-text').textContent = data.original;
                document.getElementById('rocky-text').textContent = data.rocky_style;
                document.getElementById('normalized-text').textContent = data.normalized;
                
                document.querySelectorAll('.result-box').forEach(box => box.classList.add('show'));
                
            } catch (error) {
                alert('Error processing text: ' + error);
            } finally {
                document.querySelector('.loading').classList.remove('show');
            }
        }
        
        async function generateAudio() {
            const text = document.getElementById('rocky-text').textContent;
            if (!text) {
                alert('Please transform text first');
                return;
            }
            
            document.querySelector('.loading').classList.add('show');
            
            try {
                const response = await fetch('/generate_audio', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const player = document.getElementById('audio-player');
                    player.src = url;
                    player.style.display = 'block';
                    player.play();
                } else {
                    alert('Audio generation failed. Make sure espeak-ng is installed.');
                }
            } catch (error) {
                alert('Error generating audio: ' + error);
            } finally {
                document.querySelector('.loading').classList.remove('show');
            }
        }
        
        // Process default text on load
        window.onload = () => processText();
    </script>
</body>
</html>
"""

def create_test_server():
    """Create a simple test server using Python's built-in HTTP server"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    
    # Initialize components
    normalizer = TextNormalizer()
    styler = RockyStyler(mode="rules")
    
    class TestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(HTML_TEMPLATE.encode())
            else:
                self.send_error(404)
        
        def do_POST(self):
            if self.path == '/process':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                
                text = data.get('text', '')
                
                # Process through pipeline
                rocky_style = styler.apply_style(text)
                normalized = normalizer.normalize(rocky_style)
                
                response = {
                    'original': text,
                    'rocky_style': rocky_style,
                    'normalized': normalized
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            
            elif self.path == '/generate_audio':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                
                text = data.get('text', '')
                
                # Generate audio using espeak-ng (simple TTS for testing)
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    tmp_path = tmp.name
                
                # Try espeak-ng first, fallback to espeak
                try:
                    # Use espeak-ng with a slower speed for Rocky effect
                    result = subprocess.run(
                        ['espeak-ng', '-w', tmp_path, '-s', '140', '-p', '30', text],
                        capture_output=True,
                        timeout=10
                    )
                    
                    if result.returncode != 0:
                        # Try regular espeak
                        result = subprocess.run(
                            ['espeak', '-w', tmp_path, '-s', '140', '-p', '30', text],
                            capture_output=True,
                            timeout=10
                        )
                except FileNotFoundError:
                    # espeak not installed
                    self.send_error(500, "TTS engine not installed. Install espeak-ng: apt-get install espeak-ng")
                    return
                except Exception as e:
                    self.send_error(500, f"Audio generation failed: {e}")
                    return
                
                # Read and send the WAV file
                try:
                    with open(tmp_path, 'rb') as f:
                        audio_data = f.read()
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'audio/wav')
                    self.end_headers()
                    self.wfile.write(audio_data)
                    
                    # Clean up
                    os.unlink(tmp_path)
                except Exception as e:
                    self.send_error(500, f"Failed to read audio: {e}")
            
            else:
                self.send_error(404)
        
        def log_message(self, format, *args):
            # Suppress default logging
            pass
    
    return HTTPServer, TestHandler

def main():
    print("=" * 60)
    print("🗿 Rocky TTS Test Server")
    print("=" * 60)
    print()
    
    # Check if espeak is installed
    try:
        subprocess.run(['espeak-ng', '--version'], capture_output=True)
        print("✓ espeak-ng is installed (audio will work)")
    except FileNotFoundError:
        try:
            subprocess.run(['espeak', '--version'], capture_output=True)
            print("✓ espeak is installed (audio will work)")
        except FileNotFoundError:
            print("⚠️  espeak-ng not installed. Audio generation won't work.")
            print("   Install with: sudo apt-get install espeak-ng")
    
    print()
    
    # Start server
    HTTPServer, TestHandler = create_test_server()
    
    port = 8888
    server = HTTPServer(('localhost', port), TestHandler)
    
    print(f"🌐 Server starting on: http://localhost:{port}")
    print()
    print("📝 Instructions:")
    print("1. Open your browser to the URL above")
    print("2. Enter any text to see Rocky transformation")
    print("3. Click 'Generate Audio' to hear the result")
    print("4. Try the example phrases")
    print()
    print("Press Ctrl+C to stop the server")
    print("-" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")

if __name__ == '__main__':
    main()