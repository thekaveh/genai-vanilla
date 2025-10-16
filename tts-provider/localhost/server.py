#!/usr/bin/env python3
"""
XTTS v2 TTS Server for Localhost Deployment

Runs openedai-speech server on host machine for text-to-speech generation.
Works on any platform (Mac/Linux/Windows) with Python 3.10+.

Usage:
    uv run server.py

Environment Variables:
    TTS_PROVIDER_PORT - Port to bind to (default: 10400)
    PRELOAD_MODEL - Model to preload (default: tts-1-hd)
    TTS_HOME - Directory for voice files (default: ./voices)
    HF_HOME - Directory for HuggingFace cache (default: ~/.cache/huggingface)
"""

import subprocess
import sys
import os
from pathlib import Path

def check_openedai_installation():
    """Check if openedai-speech is installed, provide instructions if not"""
    openedai_dir = Path(__file__).parent / "openedai-speech"

    if not openedai_dir.exists():
        print("\n" + "=" * 70)
        print("❌ ERROR: openedai-speech not found")
        print("=" * 70)
        print("\nopenedai-speech must be cloned from GitHub before running.")
        print("\nTo install, run these commands:")
        print()
        print("  cd tts-provider/localhost")
        print("  git clone https://github.com/matatonic/openedai-speech.git")
        print("  uv sync  # Install dependencies")
        print()
        print("Then run this script again:")
        print("  uv run server.py")
        print("=" * 70)
        sys.exit(1)

    return openedai_dir

def main():
    """Start openedai-speech server"""
    port = os.getenv('TTS_PROVIDER_PORT', '10400')
    preload_model = os.getenv('PRELOAD_MODEL', 'tts-1-hd')

    # Accept Coqui TOS automatically (required for model downloads)
    os.environ['COQUI_TOS_AGREED'] = '1'

    # Check installation
    openedai_dir = check_openedai_installation()

    # Set up directories
    tts_home = Path(os.getenv('TTS_HOME', './voices'))
    tts_home.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🎤 XTTS v2 TTS Server - Localhost Mode")
    print("=" * 70)
    print(f"📡 Server URL: http://0.0.0.0:{port}")
    print(f"📝 OpenAI-compatible API: POST /v1/audio/speech")
    print(f"🔊 Voices: alloy, echo, fable, onyx, nova, shimmer")
    print(f"🎯 Models:")
    print(f"   • tts-1: Piper TTS (fast, CPU-friendly)")
    print(f"   • tts-1-hd: XTTS v2 (high quality, GPU-accelerated)")
    print(f"💾 Preloading model: {preload_model}")
    print(f"📁 Voice directory: {tts_home.absolute()}")
    print(f"📂 openedai-speech: {openedai_dir.absolute()}")
    print("=" * 70)
    print()
    print("ℹ️  First run will download models (~1-2GB). Please be patient.")
    print("ℹ️  Subsequent runs will be instant.")
    print()
    print("🔗 Test with:")
    print(f'   curl -X POST http://localhost:{port}/v1/audio/speech \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"model": "tts-1-hd", "input": "Hello world!", "voice": "alloy"}\' \\')
    print('     --output speech.mp3')
    print()
    print("=" * 70)
    print()

    try:
        # Run openedai-speech directly from its directory
        speech_py = openedai_dir / "speech.py"

        # Build command - note: preload expects model names like 'xtts' not 'tts-1-hd'
        # The model selection happens at API request time, not server startup
        # So we skip preload and let it load on first use
        cmd = [sys.executable, str(speech_py), "--host", "0.0.0.0", "--port", port]

        subprocess.run(cmd, cwd=openedai_dir, check=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        sys.exit(0)
    except FileNotFoundError:
        print("\n\n❌ Error: openedai_speech module not found")
        print("\nTroubleshooting:")
        print("1. Ensure openedai-speech is cloned: git clone https://github.com/matatonic/openedai-speech.git")
        print("2. Install dependencies: uv sync")
        print(f"3. Check openedai-speech directory exists: {openedai_dir}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Server error: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure dependencies are installed: uv sync")
        print(f"2. Check port availability: lsof -i :{port}")
        print("3. Verify Python version: python --version (requires 3.10+)")
        print(f"4. Check openedai-speech installation in: {openedai_dir}")
        sys.exit(1)

if __name__ == "__main__":
    main()
