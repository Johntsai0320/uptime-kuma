FROM ghcr.io/louislam/uptime-kuma:2-slim

LABEL org.opencontainers.image.source="https://github.com/Johntsai0320/uptime-kuma" \
      org.opencontainers.image.description="Synology DS718+ optimized Uptime Kuma v2-slim image"

# Synology DS718+（2GB RAM + Asia/Taipei）預設調校環境變數
ENV TZ=Asia/Taipei \
    NODE_OPTIONS="--max-old-space-size=192"

EXPOSE 3001

# 對齊純 HDD 機型初次建庫緩衝時間
HEALTHCHECK --interval=60s --timeout=30s --start-period=180s --retries=5 \
    CMD extra/healthcheck
