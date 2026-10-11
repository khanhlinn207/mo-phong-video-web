import os
import json
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Báo cáo mô phỏng biến động giá")

# Khai báo thư mục static chứa video
app.mount("/static", StaticFiles(directory="static"), name="static")

def load_market_data():
    csv_path = "abc-16.csv" if os.path.exists("abc-16.csv") else "data/abc-16.csv"
    df = pd.read_csv(csv_path, header=None)

    data = []
    for day in range(len(df)):
        op = float(df.iloc[day, 0])
        cl = float(df.iloc[day, 6])
        hi = float(df.iloc[day, 0:7].max())
        lo = float(df.iloc[day, 0:7].min())

        ref = 10000.00 if day == 0 else float(df.iloc[day - 1, 6])
        ceil = ref * 1.10
        floor = ref * 0.90

        cl_r = round(cl, 2)
        ceil_r = round(ceil, 2)
        floor_r = round(floor, 2)
        ref_r = round(ref, 2)

        if cl_r >= ceil_r:
            color = 'purple'
            status = 'Kịch trần (+10%)'
        elif cl_r <= floor_r:
            color = '#1E90FF'
            status = 'Chạm sàn (-10%)'
        elif cl_r > ref_r:
            color = '#16a34a'
            status = 'Tăng so với tham chiếu'
        elif cl_r < ref_r:
            color = '#dc2626'
            status = 'Giảm so với tham chiếu'
        else:
            color = '#ca8a04'
            status = 'Bằng giá tham chiếu'

        data.append({
            "day": day + 1,
            "open": f"{op:,.2f}",
            "close": f"{cl:,.2f}",
            "high": f"{hi:,.2f}",
            "low": f"{lo:,.2f}",
            "ref": f"{ref:,.2f}",
            "ceil": f"{ceil:,.2f}",
            "floor": f"{floor:,.2f}",
            "color": color,
            "status": status
        })
    return data

market_data_list = load_market_data()
market_data_json = json.dumps(market_data_list)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Báo cáo Mô phỏng Biến động Giá Chứng khoán</title>
    <style>
        :root {
            --bg-pastel: #FFD1DC;
            --dark-card: #1e1e1e;
            --white-card: #ffffff;
            --text-main: #222222;
        }
        body {
            margin: 0;
            padding: 24px 16px;
            background-color: var(--bg-pastel);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            box-sizing: border-box;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            color: var(--text-main);
            font-size: 24px;
            margin-bottom: 24px;
            text-align: center;
            font-weight: bold;
        }
        .main-container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            max-width: 1250px;
            width: 100%;
            align-items: start;
        }
        .video-box {
            background-color: var(--dark-card);
            padding: 14px;
            border-radius: 14px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        }
        video {
            width: 100%;
            height: auto;
            border-radius: 8px;
            display: block;
        }
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .card {
            background-color: var(--white-card);
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
        }
        .card h2 {
            margin-top: 0;
            margin-bottom: 14px;
            font-size: 17px;
            color: #333;
            border-bottom: 2px solid #fce7f3;
            padding-bottom: 8px;
        }
        .color-table {
            width: 100%;
            border-collapse: collapse;
        }
        .color-table td {
            padding: 8px 6px;
            font-size: 14px;
            border-bottom: 1px solid #f1f5f9;
        }
        .color-badge {
            display: inline-block;
            width: 16px;
            height: 16px;
            border-radius: 4px;
            vertical-align: middle;
            margin-right: 6px;
        }
        .metric-grid {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .metric-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
            padding: 6px 0;
            border-bottom: 1px dashed #e2e8f0;
        }
        .metric-item:last-child {
            border-bottom: none;
        }
        .metric-label {
            color: #555;
        }
        .metric-val {
            font-weight: 700;
            color: #111;
            transition: color 0.1s ease;
        }
        .note {
            font-size: 13px;
            color: #555;
            margin-top: 12px;
            line-height: 1.4;
            background: #fafafa;
            padding: 8px 10px;
            border-radius: 6px;
            border-left: 3px solid #f472b6;
        }
        @media (max-width: 950px) {
            .main-container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <h1>BÁO CÁO MÔ PHỎNG BIẾN ĐỘNG GIÁ CHỨNG KHOÁN</h1>
    
    <div class="main-container">
        <div class="video-box">
            <video id="stockVideo" controls autoplay loop muted playsinline>
                <source src="/static/stock_simulation.mp4" type="video/mp4">
                Trình duyệt không hỗ trợ xem video.
            </video>
        </div>

        <div class="sidebar">
            <div class="card">
                <h2>🎨 Quy ước màu sắc thị trường</h2>
                <table class="color-table">
                    <tr>
                        <td><span class="color-badge" style="background-color: purple;"></span><strong>Màu tím</strong></td>
                        <td>Giá trần (+10% so với tham chiếu)</td>
                    </tr>
                    <tr>
                        <td><span class="color-badge" style="background-color: #1E90FF;"></span><strong>Xanh dương</strong></td>
                        <td>Giá sàn (-10% so với tham chiếu)</td>
                    </tr>
                    <tr>
                        <td><span class="color-badge" style="background-color: #00FF00;"></span><strong>Xanh lá</strong></td>
                        <td>Giá tăng (> tham chiếu)</td>
                    </tr>
                    <tr>
                        <td><span class="color-badge" style="background-color: #FF0000;"></span><strong>Màu đỏ</strong></td>
                        <td>Giá giảm (< tham chiếu)</td>
                    </tr>
                    <tr>
                        <td><span class="color-badge" style="background-color: #facc15;"></span><strong>Màu vàng</strong></td>
                        <td>Giá tham chiếu (đứng giá)</td>
                    </tr>
                </table>
            </div>

            <div class="card">
                <h2 id="metricTitle">📊 Chỉ số chi tiết (Phiên Ngày 1/365)</h2>
                <div class="metric-grid">
                    <div class="metric-item">
                        <span class="metric-label">Giá tham chiếu (Ref):</span>
                        <span class="metric-val" id="valRef" style="color: #ca8a04;">10,000.00 VND</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Giá trần (Ceiling):</span>
                        <span class="metric-val" id="valCeil" style="color: purple;">11,000.00 VND</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Giá sàn (Floor):</span>
                        <span class="metric-val" id="valFloor" style="color: #0284c7;">9,000.00 VND</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Giá cao nhất (High):</span>
                        <span class="metric-val" id="valHigh">11,000.00 VND</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Giá thấp nhất (Low):</span>
                        <span class="metric-val" id="valLow">9,192.82 VND</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Giá đóng cửa (Close):</span>
                        <span class="metric-val" id="valClose" style="color: purple;">11,000.00 VND</span>
                    </div>
                </div>
                <div class="note" id="metricNote">
                    * Phiên Ngày 1: Đóng cửa <strong>Kịch trần (+10%)</strong>, nến hiển thị màu tím.
                </div>
            </div>
        </div>
    </div>

    <script>
        const video = document.getElementById('stockVideo');
        const marketData = __MARKET_DATA_JSON__;
        const totalDays = marketData.length;

        function updateMetrics() {
            if (!video.duration || isNaN(video.duration)) return;
            const progress = Math.min(Math.max(video.currentTime / video.duration, 0), 1);
            let dayIndex = Math.floor(progress * totalDays);
            if (dayIndex >= totalDays) dayIndex = totalDays - 1;

            const d = marketData[dayIndex];
            if (!d) return;

            document.getElementById('metricTitle').innerText = `📊 Chỉ số chi tiết (Phiên Ngày ${d.day}/365)`;
            document.getElementById('valRef').innerText = `${d.ref} VND`;
            document.getElementById('valCeil').innerText = `${d.ceil} VND`;
            document.getElementById('valFloor').innerText = `${d.floor} VND`;
            document.getElementById('valHigh').innerText = `${d.high} VND`;
            document.getElementById('valLow').innerText = `${d.low} VND`;
            
            const closeEl = document.getElementById('valClose');
            closeEl.innerText = `${d.close} VND`;
            closeEl.style.color = d.color;

            const noteEl = document.getElementById('metricNote');
            noteEl.innerHTML = `* Phiên Ngày ${d.day}: Đóng cửa <strong>${d.status}</strong>, cây nến mang màu tương ứng.`;
        }

        function renderLoop() {
            updateMetrics();
            if (!video.paused && !video.ended) {
                requestAnimationFrame(renderLoop);
            }
        }

        video.addEventListener('play', () => requestAnimationFrame(renderLoop));
        video.addEventListener('timeupdate', updateMetrics);
        video.addEventListener('seeked', updateMetrics);
        video.addEventListener('loadedmetadata', updateMetrics);
    </script>
</body>
</html>
""".replace("__MARKET_DATA_JSON__", market_data_json)

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_CONTENT