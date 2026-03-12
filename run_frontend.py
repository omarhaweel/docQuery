#!/usr/bin/env python3
"""Serve the frontend on port 3000. Run from project root: python run_frontend.py"""
import http.server
import os
import webbrowser

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root, "frontend")
    os.chdir(frontend_dir)
    port = 3000
    server = http.server.HTTPServer(("0.0.0.0", port), http.server.SimpleHTTPRequestHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Frontend: {url}")
    print("(Start the backend with: python run_api.py → http://127.0.0.1:8000)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
