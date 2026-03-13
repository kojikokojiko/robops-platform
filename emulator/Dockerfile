FROM python:3.12-slim

# uv のインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# 依存ファイルをコピーして install (コードより先にキャッシュ効率を上げる)
COPY pyproject.toml .
RUN uv sync --no-dev

# アプリコードをコピー
COPY robot/ ./robot/

# uv の venv を PATH に追加
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "robot.main"]
