# Uptime Kuma Discord Bot

使用 Discord 斜線命令管理 Uptime Kuma 監控系統的機器人。

## 功能

- 🔍 查看所有監控器狀態
- ➕ 新增網站監控
- 🗑️ 刪除監控器
- ⏸️ 暫停/恢復監控器
- 📊 查看監控器詳細資訊
- 📋 列出所有監控器

## 安裝

1. 安裝依賴：
```bash
pip install -r requirements.txt
```

2. 設定環境變數：
   - 複製 `.env.example` 為 `.env`
   - 填入你的 Discord Bot Token 和 Uptime Kuma 資訊

3. 執行機器人：
```bash
python main.py
```

## Discord Bot 設定

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. 創建新應用程式
3. 在 Bot 頁面啟用 bot
4. 在 OAuth2 > URL Generator 選擇：
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`
5. 使用生成的 URL 邀請 bot 到你的伺服器

## 可用命令

| 命令 | 說明 |
|------|------|
| `/status` | 查看所有監控器狀態 |
| `/list_monitors` | 列出所有監控器 |
| `/monitor_info <id>` | 查看特定監控器詳情 |
| `/add_monitor <名稱> <URL>` | 新增網站監控 |
| `/delete_monitor <id>` | 刪除監控器 |
| `/toggle_monitor <id> <動作>` | 暫停或恢復監控器 |
| `/help` | 顯示幫助訊息 |

## 注意事項

- 確保 Uptime Kuma 服務正在運行
- Bot 需要管理員權限才能同步斜線命令
- 首次啟動後，斜線命令可能需要幾分鐘才會顯示在 Discord 中
"# uptime-kuma-api-bot" 
