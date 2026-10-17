#!/usr/bin/env python3
"""VYRA localhost server. Public Bitunix market endpoints only; no keys or orders."""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import ssl
import threading
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CACHE = {}
LOCK = threading.Lock()
KEY_LOCKS = {}
UPSTREAM_SLOTS = threading.BoundedSemaphore(4)
LAST_REQUEST = 0.0
COOLDOWN = 0.0
ACTIONS = {'tickers': ('tickers', 8), 'pairs': ('trading_pairs', 3600), 'kline': ('kline', 30), 'funding': ('funding_rate', 60)}
INTERVALS = {'15m', '1h', '4h', '1d'}
TLS = ssl.create_default_context(cafile='/etc/ssl/cert.pem' if Path('/etc/ssl/cert.pem').exists() else None)


class MarketFailure(RuntimeError):
    def __init__(self, code, status):
        self.code = code
        self.status = status
        super().__init__(code)


def request_market(query):
    global LAST_REQUEST, COOLDOWN
    if any(len(v) != 1 for v in query.values()):
        raise ValueError('Duplicate query parameters')
    action = query.get('action', [''])[0]
    if action not in ACTIONS:
        raise ValueError('Unsupported market action')
    allowed = {'action', 'symbol', 'interval'} if action == 'kline' else {'action', 'symbol'} if action == 'funding' else {'action'}
    if set(query) - allowed:
        raise ValueError('Unsupported query parameters')
    params = {}
    if action in {'kline', 'funding'}:
        symbol = query.get('symbol', [''])[0]
        if not re.fullmatch(r'[A-Z0-9]{1,32}USDT', symbol):
            raise ValueError('Invalid USDT symbol')
        params['symbol'] = symbol
    if action == 'kline':
        interval = query.get('interval', [''])[0]
        if interval not in INTERVALS:
            raise ValueError('Invalid interval')
        params.update(interval=interval, limit=100, type='LAST_PRICE')
    endpoint, ttl = ACTIONS[action]
    key = (action, tuple(sorted(params.items())))
    with LOCK:
        key_lock = KEY_LOCKS.setdefault(key, threading.Lock())
    # Coalesce identical requests, without blocking tickers behind unrelated candles.
    with key_lock:
        now_wall = time.time()
        with LOCK:
            cached = CACHE.get(key)
        # Cache freshness follows wall time, including time spent asleep.
        if cached and 0 <= now_wall - cached[0] < ttl:
            return cached[1]
        if not UPSTREAM_SLOTS.acquire(timeout=2):
            raise MarketFailure('SERVICE_BUSY', 503)
        try:
            with LOCK:
                now = time.monotonic()
                if now < COOLDOWN:
                    raise MarketFailure('RATE_LIMITED', 429)
                scheduled = max(now, LAST_REQUEST + .26)
                LAST_REQUEST = scheduled
            time.sleep(max(0, scheduled - time.monotonic()))
            url = 'https://fapi.bitunix.com/api/v1/futures/market/' + endpoint
            if params:
                url += '?' + urlencode(params)
            try:
                with urlopen(Request(url, headers={'User-Agent': 'VYRA-Market/2.0', 'Accept': 'application/json'}), timeout=12, context=TLS) as response:
                    payload = json.load(response)
            except HTTPError as exc:
                if exc.code == 429:
                    with LOCK:
                        COOLDOWN = time.monotonic() + 30
                    raise MarketFailure('RATE_LIMITED', 429) from None
                raise MarketFailure('UPSTREAM_UNAVAILABLE', 502) from None
            except Exception:
                raise MarketFailure('UPSTREAM_UNAVAILABLE', 502) from None
            if action == 'funding' and isinstance(payload.get('data'), dict):
                payload['data'] = [payload['data']]
            if payload.get('code') != 0 or not isinstance(payload.get('data'), list):
                raise MarketFailure('INVALID_UPSTREAM_DATA', 502)
            result = {'code': 0, 'data': payload['data'], 'fetchedAt': datetime.now(timezone.utc).isoformat(), 'source': 'Bitunix'}
            with LOCK:
                CACHE[key] = (time.time(), result)
            return result
        finally:
            UPSTREAM_SLOTS.release()



class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def permitted(self):
        return self.headers.get('Host', '').split(':')[0] in {'127.0.0.1', 'localhost'}

    def send_data(self, code, data, content_type='application/json; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        origin = self.headers.get('Origin', '')
        if origin == 'null' or re.fullmatch(r'http://(127\.0\.0\.1|localhost)(:\d+)?', origin):
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        self.send_data(204, b'')

    def do_GET(self):
        if not self.permitted():
            return self.send_data(403, b'{"error":"Localhost only"}')
        route = urlsplit(self.path)
        if route.path == '/health':
            return self.send_data(200, json.dumps({"service":"vyra-market","version":2,"serverTime":datetime.now(timezone.utc).isoformat()}).encode())
        if route.path == '/api/market':
            try:
                payload = request_market(parse_qs(route.query, keep_blank_values=True))
                return self.send_data(200, json.dumps(payload).encode())
            except MarketFailure as exc:
                return self.send_data(exc.status, json.dumps({'error': 'Market request failed', 'errorCode': exc.code}).encode())
            except ValueError as exc:
                return self.send_data(400, json.dumps({'error': str(exc)}).encode())
            except Exception:
                return self.send_data(502, b'{"error":"Bitunix market data unavailable; retry shortly"}')
        if route.path in {'/', '/index.html'}:
            return self.send_data(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        self.send_data(404, b'{"error":"Not found"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError:
        raise SystemExit('Port in use. Open http://127.0.0.1:%s or choose --port.' % args.port)
    print('VYRA ready: http://127.0.0.1:%s — keep this window open. Ctrl+C to stop.' % args.port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
