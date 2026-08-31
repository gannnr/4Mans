import http.server
import socketserver
import os
import webbrowser

PORT = 8000
FOLDER = os.path.dirname(os.path.abspath(__file__))
os.chdir(FOLDER)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    url = "http://127.0.0.1:%d/index.html" % PORT
    print("4MANS running at:")
    print(url)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("Leave Pythonista running while you test.")
    httpd.serve_forever()
