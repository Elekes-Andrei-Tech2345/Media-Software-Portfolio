import http.server
import socketserver

# Set port to 8000
PORT = 8000

class LocalTestingHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Prevent browser caching issues during testing
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        # Inject standard cors rules if necessary
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

# Correctly configure JavaScript file extension parsing for browsers
LocalTestingHTTPHandler.extensions_map.update({
    '.js': 'application/javascript',
    '.mjs': 'application/javascript',
    '.module.js': 'application/javascript'
})

print(f"🚀 Local Server launched successfully!")
print(f"👉 Open your web browser and go to: http://localhost:{PORT}/")
print("Press CTRL+C in this command window to stop the server.")

with socketserver.TCPServer(("", PORT), LocalTestingHTTPHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local testing server. Goodbye!")
