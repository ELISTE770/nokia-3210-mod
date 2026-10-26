"""
urequests.py - Lightweight HTTP/HTTPS client for MicroPython on Nokia UMS9117
Compatible with standard requests API.
"""

import json

class Response:
    def __init__(self, status_code, content, headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self._text = None

    @property
    def text(self):
        if self._text is None:
            if isinstance(self.content, bytes):
                self._text = self.content.decode("utf-8", "replace")
            else:
                self._text = str(self.content)
        return self._text

    def json(self):
        return json.loads(self.text)

    def close(self):
        pass

def request(method, url, data=None, json=None, headers=None):
    headers = headers or {}
    if json is not None:
        import json as _json
        data = _json.dumps(json).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif isinstance(data, str):
        data = data.encode("utf-8")

    # 1. Standard Python environment (Desktop / PC / Simulator)
    try:
        import urllib.request
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            resp_headers = dict(resp.getheaders())
            return Response(resp.status, content, resp_headers)
    except ImportError:
        pass
    except Exception as ex:
        import json as _json
        err_body = _json.dumps({"error": str(ex)}).encode("utf-8")
        return Response(502, err_body, {"Content-Type": "application/json"})

    # 2. Embedded MicroPython socket implementation with TLS
    try:
        import usocket as socket
        proto, dummy, host, path = url.split("/", 3)
        port = 443 if proto == "https:" else 80
        if ":" in host:
            host, port_str = host.split(":", 1)
            port = int(port_str)
        addr = socket.getaddrinfo(host, port)[0][-1]
        s = socket.socket()
        s.connect(addr)
        if proto == "https:":
            import ussl as ssl
            s = ssl.wrap_socket(s, server_hostname=host)
        s.write(f"{method} /{path} HTTP/1.0\r\nHost: {host}\r\n".encode())
        for k, v in headers.items():
            s.write(f"{k}: {v}\r\n".encode())
        if data:
            s.write(f"Content-Length: {len(data)}\r\n\r\n".encode())
            s.write(data)
        else:
            s.write(b"\r\n")
        resp_data = s.read()
        s.close()
        header_end = resp_data.find(b"\r\n\r\n")
        body = resp_data[header_end + 4:] if header_end != -1 else resp_data
        return Response(200, body, {})
    except Exception as ex:
        import json as _json
        err_body = _json.dumps({"error": str(ex)}).encode("utf-8")
        return Response(500, err_body, {})

def get(url, **kwargs):
    return request("GET", url, **kwargs)

def post(url, **kwargs):
    return request("POST", url, **kwargs)
