FROM python:3.11-slim

# tc コマンド用パッケージをインストール
RUN apt-get update && apt-get install -y \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 共通プロトコルとアクチュエーターコードをコピー
COPY common/ /app/common/
COPY hils/act/actuator.py /app/

# ログディレクトリを作成
RUN mkdir -p /app/logs

# 起動時にユーザー権限を調整するスクリプトを作成
RUN echo '#!/bin/bash\n\
if [ -n "$USER_ID" ] && [ -n "$GROUP_ID" ]; then\n\
    # ユーザーとグループを作成（既に存在する場合はスキップ）\n\
    groupadd -g "$GROUP_ID" -o appgroup 2>/dev/null || true\n\
    useradd -u "$USER_ID" -g "$GROUP_ID" -o -m appuser 2>/dev/null || true\n\
    # ログディレクトリの権限を設定\n\
    chown -R "$USER_ID:$GROUP_ID" /app/logs\n\
    # appuserとして実行\n\
    exec gosu appuser python actuator.py\n\
else\n\
    # デフォルトはrootで実行\n\
    exec python actuator.py\n\
fi' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# gosuをインストール
RUN apt-get update && apt-get install -y gosu && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/app/entrypoint.sh"]