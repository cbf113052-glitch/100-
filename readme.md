# 資料結構：堆積與優先佇列測驗系統

這是一個基於 Django 開發的資料結構線上測驗平台。

## 🎯 系統核心功能
1. **帳號功能**：支援使用者登入與註冊機制
2. **歷史紀錄**：完整追蹤每一次的測驗分數與時間
3. **即時回饋**：提供答案、詳細解題即時回饋機制
4. **倒數計時**：模擬真實考試的測驗計時功能
5. **難易度分級**：提供不同層級的資料結構題庫
6. **錯題複習模式**：自動統整答錯題目以供二次練習
7. **排行榜系統**：激發學習動力的全站使用者排名
8. **活動熱圖**：動態展示每日學習進度的活動熱圖（Heatmap）
9. **學習成效分析**：圖表化呈現個人歷史學習曲線
10. **使用者題庫預覽**：直觀的線上題庫瀏覽與預覽介面

---

## 🛠️ 開發者的實際安裝與環境建置紀錄

本專案在部署與推送到 GitHub 的過程中，實際執行了以下完整的環境建置與問題排查步驟，以此向教學團隊與老師說明實際安裝與 Debug 流程：

### 1. 本地環境建置與依賴安裝
在本地端（Windows PowerShell）建立 Django 專案環境，並透過以下指令安裝必要套件、執行資料庫遷移：
```bash
複製專案並進入資料夾
git clone [https://github.com/cbf113052-glitch/100-.git](https://github.com/cbf113052-glitch/100-.git)
cd mysite

安裝環境必要套件（提供給教學團隊還原環境測試）
pip install -r requirements.txt

初始化與遷移資料庫（Migration）
python manage.py migrate

啟動本機測試伺服器
python manage.py runserver

按下快門，正式建立本地第一個存檔紀錄
git commit -m "Initial commit - Django quiz system"

確保預設分支更名為 main
git branch -M main

正式「發射、上傳」到 GitHub 雲端網站上
git push origin main