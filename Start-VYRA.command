#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
open_vyra() {
  if [[ -d '/Applications/Google Chrome.app' ]]; then
    open -a 'Google Chrome' 'http://127.0.0.1:8765/'
  else
    open 'http://127.0.0.1:8765/'
  fi
}
if ! command -v python3 >/dev/null 2>&1; then
  print '請先安裝 Python 3 / Python 3 is required.'
  read
  exit 1
fi
vyra_health=$(curl -fsS --max-time 3 http://127.0.0.1:8765/health 2>/dev/null)
if print -r -- "$vyra_health" | /usr/bin/grep -q 'vyra-market'; then
  if print -r -- "$vyra_health" | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("version", 0) >= 2 else 1)' 2>/dev/null; then
    open_vyra
    exit 0
  fi
  print '舊版行情服務仍在執行。請先關閉舊版服務的終端機視窗，再重新啟動。'
  print 'An older service is running. Stop its terminal window and run this launcher again.'
  read
  exit 1
fi
mkdir -p .runtime
nohup python3 server.py > .runtime/server.log 2>&1 < /dev/null &
vyra_server_pid=$!
print -r -- "$vyra_server_pid" > .runtime/server.pid
for attempt in {1..30}; do
  if curl -fsS --max-time 2 http://127.0.0.1:8765/health 2>/dev/null | /usr/bin/grep -q 'vyra-market'; then
    open_vyra
    print 'VYRA 已在背景啟動。可以關閉這個終端機視窗。'
    print 'VYRA is running in the background. You may close this terminal window.'
    exit 0
  fi
  sleep 0.5
done
print '啟動未完成，請查看以下錯誤 / Startup failed:'
tail -n 15 .runtime/server.log
read
exit 1
