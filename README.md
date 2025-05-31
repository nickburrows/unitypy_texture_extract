# Unity 紋理取代工具

這是一個用於提取和替換 Unity .assets 檔案中紋理的 Web 工具。它允許使用者上傳 Unity 資源檔案，查看其中的紋理，並進行替換操作。

## 功能特色

- 支援上傳 .assets 和 .resS 檔案
- 提取並顯示所有紋理資源
- 支援按 Path ID 搜尋紋理
- 支援紋理預覽和替換
- 支援深色/淺色主題切換
- 提供緊湊的表格視圖
- 支援檔案批次處理

## 系統需求

- Python 3.7 或更高版本
- 相關 Python 套件（見 requirements.txt）

## 安裝說明

1. 克隆此倉庫：

```bash
git clone [您的倉庫URL]
cd unitypy_texture_extract
```

2. 安裝所需套件：

```bash
pip install -r requirements.txt
```

3. 執行應用程式：

```bash
python app.py
```

4. 開啟瀏覽器訪問：

```
http://localhost:5000
```

## 使用說明

1. 在首頁點擊「選擇檔案」上傳 .assets 檔案（如果有對應的 .resS 檔案也可以一併上傳）
2. 等待系統提取紋理資源
3. 在列表頁面中可以：
   - 使用 Path ID 搜尋特定紋理
   - 點擊預覽圖放大查看
   - 點擊「取代紋理」上傳新的圖片
   - 完成所有替換後下載修改後的檔案

## 注意事項

- 支援的檔案類型：.assets 和 .resS
- 替換紋理時，建議使用相同尺寸的圖片以避免問題
- 請確保有足夠的磁碟空間用於處理大型資源檔案

## 專案結構

```
.
├── app.py              # Flask 應用程式主文件
├── texture_replacer.py # 紋理替換核心邏輯
├── requirements.txt    # Python 套件相依性
├── templates/         # HTML 模板
│   ├── index.html    # 首頁模板
│   └── results.html  # 結果頁面模板
├── uploads/          # 上傳檔案暫存目錄
├── extracted/        # 提取的紋理暫存目錄
└── modified/         # 修改後的檔案輸出目錄
```

## 授權說明

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 文件
