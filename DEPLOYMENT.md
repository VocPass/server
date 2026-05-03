# VocPass Server 部署說明

本文說明如何在本機、VPS、Docker 容器部署 VocPass Server。

## 服務概覽

- Runtime：Python 3.11
- Framework：FastAPI
- 預設 Port：`8000`
- 啟動入口：`start.sh`
- API 文件：`/docs`
- Metrics：`/metrics`

## 前置需求

部署環境需準備：

- Python 3.11 或 Docker
- 可連線的 PocketBase 服務
- Git
- 若使用 GitHub Actions 自動部署，遠端主機需可透過 SSH 登入

## 環境變數

先複製範例檔：

```bash
cp .env.exp .env
```

依部署環境填入：

```env
APP_ENV=production
APP_PORT=8000
INSTANCE_ID=node-1

PB_URL=https://your-pocketbase.example.com/
PB_EMAIL=admin@example.com
PB_PASSWORD=your-password

PROMETHEUS_METRICS_TOKEN=your-metrics-token

LOKI_URL=
LOKI_TOKEN=
```

### 必填

- `APP_ENV`：部署到正式環境時設為 `production`。
- `APP_PORT`：服務監聽 Port，預設為 `8000`。
- `PB_URL`：PocketBase URL。
- `PB_EMAIL`：PocketBase admin 帳號。
- `PB_PASSWORD`：PocketBase admin 密碼。

### 選填

- `INSTANCE_ID`：節點識別，用於 metrics 與 log 標記。
- `PROMETHEUS_METRICS_TOKEN`：若有設定，存取 `/metrics` 時需帶 `Authorization: Bearer <token>`。
- `LOKI_URL`：Loki endpoint。留空時 log 會輸出到 stdout。
- `LOKI_TOKEN`：Loki token。

若有使用推播功能，另需依實際環境提供：

- `team_id`
- `key_id`
- `key_path`
- `bundle_id`

## 本機正式模式啟動

安裝依賴：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

啟動服務：

```bash
APP_ENV=production APP_PORT=8000 ./start.sh
```

Windows PowerShell 可改用：

```powershell
$env:APP_ENV="production"
$env:APP_PORT="8000"
fastapi run --port $env:APP_PORT
```

啟動後檢查：

```bash
curl http://localhost:8000/docs
```

## Docker 部署

建置 image：

```bash
docker build -t vocpass-server .
```

啟動容器：

```bash
docker run -d \
  --name vocpass-server \
  --env-file .env \
  -p 8000:8000 \
  vocpass-server
```

查看 log：

```bash
docker logs -f vocpass-server
```

重新部署：

```bash
docker stop vocpass-server
docker rm vocpass-server
docker build -t vocpass-server .
docker run -d --name vocpass-server --env-file .env -p 8000:8000 vocpass-server
```

## VPS 部署

在遠端主機 clone 專案：

```bash
git clone <repo-url> vocpass-server
cd vocpass-server
cp .env.exp .env
```

填好 `.env` 後，安裝依賴並啟動：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x start.sh
APP_ENV=production ./start.sh
```

建議使用 systemd、Pterodactyl、Docker 或其他 process manager 管理服務重啟。

## 監控

服務提供 `/metrics` 給 Prometheus 抓取。若設定了 `PROMETHEUS_METRICS_TOKEN`，Prometheus 需帶 bearer token。

範例：

```yaml
scrape_configs:
  - job_name: "vocpass_api"
    static_configs:
      - targets: ["api.example.com"]
    metrics_path: /metrics
    authorization:
      credentials: "your-metrics-token"
```

Grafana dashboard 範例位於：

```text
status/grafana-dashboard.json
```

## 部署後驗證

部署完成後建議檢查：

```bash
curl -I http://localhost:8000/docs
curl http://localhost:8000/metrics -H "Authorization: Bearer <token>"
```

也可以從瀏覽器開啟：

```text
https://your-domain.example.com/docs
```

## 常見問題

### 啟動時 PocketBase 驗證失敗

確認 `PB_URL`、`PB_EMAIL`、`PB_PASSWORD` 是否正確，且部署環境可以連線到 PocketBase。

### `/metrics` 回傳 401

代表已設定 `PROMETHEUS_METRICS_TOKEN`。請在 request header 加上：

```text
Authorization: Bearer <token>
```
