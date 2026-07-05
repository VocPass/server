<div align="center">

# VocPass Server

**高職通用校務查詢系統 — 後端 API 伺服器**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PocketBase](https://img.shields.io/badge/DB-PocketBase-b8dbe4?logo=pocketbase&logoColor=black)](https://pocketbase.io/)
[![License](https://img.shields.io/badge/license-GPL--3.0-green)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-/docs-orange)](https://vocpass.zeabur.app/docs)

</div>

---

## 這是什麼

VocPass Server 是 [VocPass iOS](https://github.com/VocPass/ios)、[VocPass Android](https://github.com/VocPass/android) 及 [Discord Bot](https://github.com/VocPass/bot) 共用的後端服務，負責登入各校校務系統、解析課表 / 成績 / 缺曠 / 獎懲等資料，並提供論壇、揪團（When2Meet）、吃啥推薦、桌布產生器等附加功能的 API。

## 功能總覽

| 模組 | 說明 |
|------|------|
| 🔐 **`/auth`** | 登入各校校務系統並代管 Session |
| 📡 **`/api/v1` ~ `/api/v9`** | 依各校系統版本解析課表、成績、缺曠、獎懲資料 |
| 🧪 **`/api/demo`** | 免帳密的展示端點，回傳假資料供前端開發測試 |
| 👤 **`/api/user`** | VocPass 使用者資料 |
| 💬 **`/api/forum`** | 校園匿名論壇（發文、標籤、檢舉、審核） |
| 🍜 **`/restaurant`** | 「吃啥？」餐廳推薦與投稿 |
| 📅 **When2Meet** | 團體時間揪團與可用時段統計 |
| 🖼️ **`/api/wallpaper`** | 依課表產生手機桌布 |
| 📊 **`/metrics`** | Prometheus 指標，`status/` 內含對應 Grafana dashboard |
| 🗺️ **`/sitemap.xml`** | 自動產生的網站 sitemap |

完整 API 規格請見線上文件：**[vocpass.zeabur.app/docs](https://vocpass.zeabur.app/docs)**

## 技術棧

- **FastAPI** + **Uvicorn** — API 框架與 ASGI server
- **PocketBase** — 資料庫與使用者驗證
- **slowapi** — 依 IP 做請求限流
- **prometheus-client** / **python-logging-loki** — 監控與日誌
- **BeautifulSoup4 / curl-cffi / httpx** — 校務系統網頁解析與爬取

## 新增學校支援

各校校務系統的登入方式、路由與解析規則集中定義於 [`school.json`](school.json)，新增一所學校通常只需要：

1. 在 `school.json` 新增一筆學校設定（登入表單欄位、驗證碼、各功能路由）
2. 視系統版本差異，對應到既有的 `/api/v1` ~ `/api/v9` 解析邏輯，或在 `routers/` 新增一版
3. 送出 PR，並附上該校系統的樣本頁面或欄位說明以利驗證

## 本機開發

```bash
git clone https://github.com/VocPass/server.git
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.exp .env   # 依需求填入 PB_URL / PB_EMAIL / PB_PASSWORD 等變數
./start.sh         # 預設以 development 模式啟動，port 8000
```

啟動後開啟 `http://localhost:8000/docs` 即可看到互動式 API 文件。

> 正式環境部署（Docker、VPS、環境變數、Prometheus 監控）請見 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 相關專案

| Repo | 說明 |
|------|------|
| [VocPass/ios](https://github.com/VocPass/ios) | iOS / iPadOS / macOS 原生 App |
| [VocPass/android](https://github.com/VocPass/android) | Android App（Flutter） |
| [VocPass/bot](https://github.com/VocPass/bot) | Discord 狀態機器人 |

## 授權

本專案採用 [GPL-3.0 License](LICENSE) 授權。
