# NAS 服務監控中心 — Uptime Kuma v2-slim (Synology DS718+ 2GB 最佳化版)

專為 **Synology DS718+（原廠 2GB RAM、純 HDD 無 SSD、搭配 Tailscale）** 設計的服務在線監控與備份 Webhook 告警中心，可無縫串接 [`Johntsai0320/vaultwarden-backup-`](https://github.com/Johntsai0320/vaultwarden-backup-) 的每日備份通知與全部 NAS 容器健康檢查。

部署架構與慣例一致對齊 [`Johntsai0320/vaultwarden-backup-`](https://github.com/Johntsai0320/vaultwarden-backup-) 與 [`Johntsai0320/nginx`](https://github.com/Johntsai0320/nginx)。

---

## 目錄結構

```text
/volume1/docker/uptime-kuma/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
└── data/                  # 首次啟動自動產生 SQLite 資料庫（已忽略，不進 Git）
```

---

## ✨ 針對 DS718+ 2GB RAM + 純 HDD 的調校重點

1. **採用 `ghcr.io/louislam/uptime-kuma:2-slim` 映像檔**：
   - 使用 GHCR 多架構映像檔避開 Docker Hub 拉取限流。
   - `2-slim` 版本移除數百 MB 的 Chromium 無頭瀏覽器元件，大幅節省空間並防止在 2GB RAM 機型上誤開 Real Browser 監控造成記憶體耗盡。
2. **記憶體與日誌防護**：
   - 限制容器上限 `mem_limit: 256m`、`memswap_limit: 384m`、`cpu_shares: 512`，並設定 `NODE_OPTIONS=--max-old-space-size=192`，避免與其他服務爭搶記憶體引發 HDD Swap。
   - 啟用 `json-file` 日誌輪替（單檔上限 `5m`、最多保留 `2` 份）。
   - 健康檢查套用官方建議緩衝時間（`start_period: 180s`、`retries: 5`），確保在純 HDD 首次初始化資料庫時不會誤判為異常。
3. **本機儲存提醒（重要）**：
   - 官方明確**不支援**將 `./data` 掛載於 NFS，請務必維持在 NAS 本機儲存池（`/volume1/docker/uptime-kuma/data`）。
4. **低 I/O 建議設定**（部署完成後請於網頁後台調整）：
   - 監控間隔建議設為 **`60`～`120` 秒**（不要使用預設高頻 20 秒，可顯著減少 SQLite 寫入 HDD 的次數）。
   - 前往 **設定 → 歷史紀錄** 將保留天數設為 **`30`～`60` 天**，防止資料庫長期膨脹。

---

## 🚀 部署步驟（目標路徑：`/volume1/docker/uptime-kuma`）

### 步驟 1：下載專案至 NAS 資料夾

透過 SSH 連線到 Synology NAS，將專案 Clone 至 `/volume1/docker/uptime-kuma`：

```bash
cd /volume1/docker
git clone https://github.com/Johntsai0320/uptime-kuma.git uptime-kuma
cd /volume1/docker/uptime-kuma
```

### 步驟 2：建立 `.env`

```bash
cp .env.example .env
```

預設監聽埠號為 **`3001`**（已避開 `novel:3000`、`homepage:3010`、`LibreTV:8080`、`nginx:8088/8443`、`vaultwarden:8200`），一般情況無須修改即可啟動。

### 步驟 3：在 Synology Container Manager 匯入「專案」

1. 開啟 DSM **Container Manager → 專案 (Project) → 新增 (Create)**。
2. 專案名稱填入：`uptime-kuma`。
3. **路徑 (Path)** 選擇 `/docker/uptime-kuma`（即 `/volume1/docker/uptime-kuma`）。
4. Container Manager 會自動偵測 `docker-compose.yml` → 選擇 **使用現有的 docker-compose.yml** 並啟動。
5. 連上 Tailscale 後開啟 `http://<您的Tailscale_IP>:3001`，建立管理員帳號（內建 SQLite 資料庫，無需額外裝 MariaDB）。

---

## 🔗 建議監控項目清單（透過 `host.docker.internal` 本機檢查）

本專案已設定 `extra_hosts: host.docker.internal:host-gateway`，在 Uptime Kuma 新增監控項目時建議透過內網迴路直連：

| 服務名稱 | 監控類型 | URL / 目標 | 備註 |
| :--- | :--- | :--- | :--- |
| **Vaultwarden** | HTTP(s) | `http://host.docker.internal:8200/alive` | 官方專用健康檢查端點（見下方備註） |
| **LibreTV** | HTTP(s) | `http://host.docker.internal:8080/api/status` | 無須登入即可取得 JSON `200` 狀態 |
| **雲端書閣 Novel** | HTTP(s) | `http://host.docker.internal:3000/api/health` | 無須 PIN 即可回傳 `{ ok: true }` |
| **Homepage** | HTTP(s) | `http://host.docker.internal:3010/api/healthcheck` | 官方健康檢查端點 |
| **Nginx 反向代理** | HTTP(s) | `http://host.docker.internal:8088/healthz` | 對應 `nginx` 專案內建健康檢查端點 |

> [!NOTE]
> - **DSM 防火牆放行**：若在 Synology 控制台有啟用 **DSM 防火牆**，請確認已放行 Docker 網段（如 `172.17.0.0/16`）存取上述埠號；或於 `docker-compose.yml` 啟用共用自訂 Docker 網路（如 `proxy-net`）後直接填入容器名稱。
> - **Vaultwarden 若設定 `VAULTWARDEN_BIND_IP=127.0.0.1`**：因只綁定本機迴路 `127.0.0.1`，Bridge 模式的 `host.docker.internal` 無法直接連線。此時請改為監控 Synology 反向代理後的 HTTPS 網址（如 `https://vw.yourname.synology.me/alive`），或將兩者加入同一個自訂 Docker 網路並改填 `http://vaultwarden:80/alive`。

---

## 🔔 串接 `vaultwarden-backup-` 每日備份通知（Push Monitor）

[`Johntsai0320/vaultwarden-backup-`](https://github.com/Johntsai0320/vaultwarden-backup-) 的 `.env.example` 已預留 `PING_URL_WHEN_SUCCESS` 與 `PING_URL_WHEN_FAILURE` 欄位，設定步驟如下：

1. 在 Uptime Kuma 點擊 **新增監控項目**：
   - **監控類型**：選擇 **`Push`**
   - **顯示名稱**：`Vaultwarden 每日熱備份`
   - **心跳間隔**：設為 **`90000`** 秒（25 小時，容許每日凌晨 03:00 排程與上傳 Google Drive 的緩衝時間）
2. 儲存後複製畫面上產生的 **Push URL**（格式類似 `http://localhost:3001/api/push/xxxxxx?status=up&msg=OK&ping=`）。
3. 填入 `/volume1/docker/vaultwarden/.env`（注意 `vaultwarden-backup` 預設未設定 `host.docker.internal`，請使用 **NAS 區網 / Tailscale IP** 或 **Docker 閘道器 `172.17.0.1`**；若兩者已加入共用網路或於 `vaultwarden-backup` 補上 `extra_hosts` 則可用容器名稱或 `host.docker.internal`）：
   ```env
   PING_URL_WHEN_SUCCESS=http://172.17.0.1:3001/api/push/xxxxxx?status=up&msg=Backup_OK
   PING_URL_WHEN_FAILURE=http://172.17.0.1:3001/api/push/xxxxxx?status=down&msg=Backup_Failed
   ```
4. 在 Container Manager 重新套用 `vaultwarden` 專案，之後只要半夜備份失敗或超過 25 小時未回報，Uptime Kuma 就會立即發送告警通知。

---

## 🧩 整合至 Homepage 狀態小工具（選用）

1. 在 Uptime Kuma 建立一個 **狀態頁 (Status Page)**，設定 URL slug（例如 `nas`）並加入要展示的監控項目。
2. 於 `homepage` 專案的 `config/services.yaml` 取消註解對應的 `uptimekuma` `widget:` 區塊並填入 `slug: nas` 即可在導覽首頁顯示各服務即時狀態。
