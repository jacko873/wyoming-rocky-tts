#!/usr/bin/env python3
"""Test the Wyoming TTS server exactly the way Home Assistant does:
connect -> describe -> expect info -> synthesize -> expect audio events.

Usage:
    venv/bin/python test_wyoming_connection.py [host] [port]
    (defaults: localhost 10202)
"""

import asyncio
import sys

from wyoming.client import AsyncTcpClient
from wyoming.info import Describe, Info
from wyoming.tts import Synthesize
from wyoming.audio import AudioStart, AudioChunk, AudioStop


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 10202

    print(f"Connecting to {host}:{port} ...")
    client = AsyncTcpClient(host, port)
    try:
        await asyncio.wait_for(client.connect(), timeout=5)
    except Exception as e:
        print(f"❌ TCP connect failed: {e}")
        print("   -> Server not listening / wrong host or port / still loading the model")
        sys.exit(1)
    print("✅ TCP connected")

    # 1. describe -> info (this is what HA does when you add the integration)
    await client.write_event(Describe().event())
    try:
        event = await asyncio.wait_for(client.read_event(), timeout=10)
    except asyncio.TimeoutError:
        print("❌ No response to 'describe' within 10s (old broken handler?)")
        sys.exit(1)
    if event is None:
        print("❌ Server closed the connection on 'describe' (old broken handler still running?)")
        sys.exit(1)
    if event.type != "info":
        print(f"❌ Expected 'info' event, got: {event.type}")
        sys.exit(1)
    info = Info.from_event(event)
    voices = [v.name for p in info.tts for v in p.voices]
    print(f"✅ describe -> info  (program: {info.tts[0].name}, voices: {voices})")

    # 2. synthesize -> audio-start, audio-chunk(s), audio-stop
    print("Requesting synthesis (this synthesizes for real, may take a while)...")
    await client.write_event(Synthesize(text="Connection test. Good good good.").event())
    try:
        event = await asyncio.wait_for(client.read_event(), timeout=120)
    except asyncio.TimeoutError:
        print("❌ No audio within 120s")
        sys.exit(1)
    if event is None or not AudioStart.is_type(event.type):
        print(f"❌ Expected 'audio-start', got: {event.type if event else 'connection closed'}")
        sys.exit(1)
    print(f"✅ audio-start: {event.data}")

    nbytes = 0
    while True:
        event = await asyncio.wait_for(client.read_event(), timeout=30)
        if event is None:
            print("❌ Connection closed mid-stream")
            sys.exit(1)
        if AudioStop.is_type(event.type):
            break
        if AudioChunk.is_type(event.type):
            nbytes += len(event.payload or b"")
    print(f"✅ audio-stop after {nbytes} bytes of PCM")

    await client.disconnect()
    print("\n🎉 ALL CHECKS PASSED — Home Assistant will be able to connect to this server.")


if __name__ == "__main__":
    asyncio.run(main())
