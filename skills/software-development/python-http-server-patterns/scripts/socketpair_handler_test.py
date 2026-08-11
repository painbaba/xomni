#!/usr/bin/env python3
"""Socketpair smoke test for a BaseHTTPRequestHandler subclass.

Catches the two classic handler bugs WITHOUT binding a port:
  1. header pre-read trap   -> request hangs / ValueError / no response
  2. rfile rewrap body loss -> POST 'read failed' or broken body

Usage:
    python socketpair_handler_test.py <handler_module.py> [HandlerClassName]

Asserts only that the handler PROCESSES the request (any HTTP response proves
the read path works) — 200/401/400 all pass. Exit 1 on timeout/exception.
"""
import importlib.util
import socket
import sys
import threading
import time

REQUEST = (
    b"POST /login HTTP/1.1\r\n"
    b"Host: x\r\n"
    b"Content-Length: 20\r\n"
    b"\r\n"
    b'{"username":"admin"}'
)


def main():
    path = sys.argv[1]
    cls_name = sys.argv[2] if len(sys.argv) > 2 else "Handler"

    spec = importlib.util.spec_from_file_location("mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # module-level code (env, constants) runs here
    handler_cls = getattr(mod, cls_name)

    s1, s2 = socket.socketpair()
    result = {"ok": False}

    def client():
        s2.settimeout(5)
        s2.sendall(REQUEST)
        time.sleep(0.3)
        try:
            data = s2.recv(4096)
            if b"HTTP/" in data:
                print("CLIENT GOT:", data[:120])
                result["ok"] = True
            else:
                print("CLIENT GOT non-HTTP bytes:", data[:120])
        except socket.timeout:
            print("CLIENT TIMEOUT: handler blocked in a read "
                  "(pre-read trap or rfile rewrap bug)")
        finally:
            s2.close()

    t = threading.Thread(target=client, daemon=True)
    t.start()
    h = handler_cls(s1, ("127.0.0.1", 0), None)
    t0 = time.time()
    h.handle_one_request()
    print("handler returned in", round(time.time() - t0, 3), "s")
    t.join(timeout=7)

    if not result["ok"]:
        print("FAIL: request was not processed")
        sys.exit(1)
    print("PASS: handler processed the request end-to-end")


if __name__ == "__main__":
    main()
