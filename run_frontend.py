#!/usr/bin/env python3
"""Serve the frontend on port 3000. Run from project root: python run_frontend.py"""
import http.server
import os
import webbrowser

LOCAL_API = "http://127.0.0.1:8000"

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/index.html"
            with open(os.path.join(os.getcwd(), "index.html"), "rb") as f:
                body = f.read().decode("utf-8").replace("__BACKEND_URL__", LOCAL_API).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root, "frontend")
    os.chdir(frontend_dir)
    port = 3000
    server = http.server.HTTPServer(("0.0.0.0", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Frontend: {url}")
    print("(Start the backend with: python run_api.py → http://127.0.0.1:8000)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
