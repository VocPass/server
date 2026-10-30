# VocPass Server

[API Docs](https://vocpass.com/docs)

## 部署

部署流程、環境變數、Docker、VPS設定請見 [DEPLOYMENT.md](DEPLOYMENT.md)。


## 專案結構

```text
.
├── app.py                      # FastAPI 入口、路由載入、例外處理與 metrics
├── start.sh                    # 載入 .env，依環境切換啟動模式
├── requirements.txt            # Python 依賴
├── Dockerfile                  # Python 3.11 容器映像
├── .env.exp                    # 環境變數範例
├── school.json                 # 學校、系統版本、登入與資料路徑設定
├── pocketbase.json             # PocketBase collection 匯出檔
├── wallpaper_template.json     # 課表桌布模板資料
├── routers/
│   ├── v1api.py … v10api.py    # 各校務系統解析端點
│   ├── demoapi.py              # 展示用端點
│   ├── auth.py / user.py       # 登入頁面與使用者 API
│   ├── vocpass.py              # 共用 API、課表分享、公告與檢舉
│   ├── forum.py                # 論壇
│   ├── restaurant.py           # 餐廳、評價與菜單
│   ├── w2m.py                  # When2Meet
│   ├── wallpaper.py            # 桌布模板、字體與統計
│   ├── mapfetch.py             # Google Maps HTML 抓取中繼站
│   └── index.py                # 網站頁面、登入檢查與部署版本
├── utils/
│   ├── v1.py … v10.py          # 各版本資料解析器
│   ├── http_client.py          # 校務資料 HTTP 請求
│   ├── esa_client.py           # v10 ESA → HSA 登入與 session 管理
│   ├── pb.py                   # PocketBase 使用者驗證與資料操作
│   ├── notice.py              # 學校公告解析
│   ├── send_notification.py    # APNs 推播發送
│   ├── debug.py                # 正式環境錯誤紀錄
│   ├── logger.py / metrics.py  # 日誌與監控指標
│   └── page_templates.py       # 網頁模板與 SEO 設定
├── templates/                  # Jinja2 頁面與共用片段
├── demo/                       # 展示用 JSON
├── tools/                      # 各版本輔助腳本
├── status/                     # Prometheus 設定與 Grafana dashboard
├── auto.py                     # 校務系統版本辨識輔助函式
├── sort_by_vision.py            # 依版本排序並覆寫 school.json
└── .github/workflows/deploy.yml # 透過面板 API 重新啟動服務
```