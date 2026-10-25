#!/usr/bin/env bash
# 在 GitHub 连通窗口一出现时立刻推送（网络时好时坏，靠重试兜住）
set -u
cd "$(dirname "$0")/.." || exit 1

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export GIT_TERMINAL_PROMPT=0
export GIT_TOKEN="${GIT_TOKEN:?需要 GIT_TOKEN 环境变量}"

CRED='!f() { echo username=x-access-token; echo "password=$GIT_TOKEN"; }; f'

for i in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://github.com 2>/dev/null)
  echo "[$i] github.com -> ${code:-timeout}"
  if [ "$code" = "200" ]; then
    echo "[$i] 窗口出现，开始推送…"
    if git -c credential.helper= -c "credential.helper=$CRED" \
           -c http.postBuffer=524288000 \
           push -u origin main 2>&1; then
      echo "PUSH_OK"
      exit 0
    fi
    echo "[$i] 推送中断，继续等下一个窗口"
  fi
  sleep 6
done

echo "PUSH_GIVEUP"
exit 1
