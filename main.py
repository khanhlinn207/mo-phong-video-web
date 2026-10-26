import os
import io
import json
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Báo cáo mô phỏng biến động giá")

# Gắn thư mục static chứa video
app.mount("/static", StaticFiles(directory="static"), name="static")

# ========================================================
# 1. GIỮ NGUYÊN HOÀN TOÀN HÀM XỬ LÝ DỮ LIỆU CŨ CỦA BẠN
# ========================================================
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

# ========================================================
# 2. HÀM TỰ ĐỘNG VẼ 5 BIỂU ĐỒ (DÙNG ĐÚNG CODE CỦA BẠN)
# ========================================================
def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=105, facecolor='white', edgecolor='none')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{img_b64}"

def generate_charts():
    csv_path = "abc-16.csv" if os.path.exists("abc-16.csv") else "data/abc-16.csv"
    df = pd.read_csv(csv_path, header=None)

    cal_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day_month = []
    for m, d in enumerate(cal_days, 1):
        day_month.extend([m] * d)

    df_melt = df.copy()
    df_melt['thang'] = day_month
    df_melt['quy'] = [(m - 1) // 3 + 1 for m in day_month]
    gia = df_melt.melt(id_vars=['thang', 'quy'], value_name='gia')

    charts = {}

    # Câu 1: Cột giá trung bình mỗi tháng (#FFD1DC)
    t = gia.groupby('thang')['gia'].agg(['mean'])
    fig1, ax1 = plt.subplots(figsize=(7, 3.6), facecolor='white')
    ax1.set_facecolor('white')
    ax1.bar(t.index, t['mean'], color='#FFD1DC')
    ax1.set_xticks(range(1, 13))
    ax1.set_xlabel('Tháng', fontsize=9.5)
    ax1.set_ylabel('Giá trung bình (VND)', fontsize=9.5)
    charts['chart1'] = fig_to_base64(fig1)

    # Câu 2: Boxplot theo tháng
    fig2, ax2 = plt.subplots(figsize=(7.5, 3.8), facecolor='white')
    ax2.set_facecolor('white')
    data_by_thang = [gia[gia['thang'] == m]['gia'].values for m in range(1, 13)]
    ax2.boxplot(data_by_thang, labels=range(1, 13), patch_artist=True,
                boxprops=dict(facecolor='#FFD1DC', edgecolor='#a3224b'),
                medianprops=dict(color='#a3224b'),
                flierprops=dict(markeredgecolor='#a3224b', markersize=4))
    ax2.set_xlabel('Tháng', fontsize=9.5)
    ax2.set_ylabel('Giá (VND)', fontsize=9.5)
    ax2.grid(axis='y', linestyle='--', alpha=0.4)
    charts['chart2'] = fig_to_base64(fig2)

    # Câu 3: Thống kê số lượng phiên bất thường
    ngay = range(1, 366)
    close = df.iloc[:, 6].values
    ref = np.zeros(len(df))
    ref[0] = 10000.0
    ref[1:] = close[:-1]

    bt = pd.DataFrame({'ngày': ngay, 'tham_chieu': ref, 'dong_cua': close})
    bt['loại'] = ''
    bt.loc[np.isclose(close, ref * 1.1), 'loại'] = 'Giá trần'
    bt.loc[np.isclose(close, ref * 0.9), 'loại'] = 'Giá sàn'
    bt.loc[np.isclose(close, ref), 'loại'] = 'Giá tham chiếu'
    bt = bt[bt['loại'] != '']
    counts = bt['loại'].value_counts()

    fig3, ax3 = plt.subplots(figsize=(7, 3.6), facecolor='white')
    ax3.set_facecolor('white')
    bars = ax3.bar(counts.index, counts.values, color='#FFD1DC', edgecolor='#a3224b', width=0.45)
    for bar in bars:
        y = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width() / 2, y + 2, f'{int(y)} phiên', 
                 ha='center', va='bottom', color='#a3224b', fontweight='bold', fontsize=10)
    ax3.set_ylabel('Số phiên', fontsize=9.5)
    ax3.set_ylim(0, max(counts.values) + 20)
    ax3.grid(axis='y', linestyle='--', alpha=0.4)
    charts['chart3'] = fig_to_base64(fig3)

    # Câu 4: Histogram 2 nửa năm (Code gốc: #e8789a và #6c8ebf)
    dau = gia[gia['quy'] <= 2]['gia']
    cuoi = gia[gia['quy'] >= 3]['gia']
    fig4, (a, b) = plt.subplots(1, 2, figsize=(8, 3.6), sharey=True, facecolor='white')
    a.set_facecolor('white'); b.set_facecolor('white')
    a.hist(dau, bins=30, color='#e8789a')
    a.set_title('2 quý đầu năm', fontsize=10)
    b.hist(cuoi, bins=30, color='#6c8ebf')
    b.set_title('2 quý cuối năm', fontsize=10)
    a.set_xlabel('Giá (VND)', fontsize=9); a.set_ylabel('Số lần', fontsize=9)
    b.set_xlabel('Giá (VND)', fontsize=9)
    charts['chart4'] = fig_to_base64(fig4)

    # Câu 5: Xu hướng giá trong năm
    cao_moi_ngay = df.max(axis=1)
    thap_moi_ngay = df.min(axis=1)
    gia_cao = cao_moi_ngay.max()
    ngay_cao = cao_moi_ngay.idxmax() + 1
    gia_thap = thap_moi_ngay.min()
    ngay_thap = thap_moi_ngay.idxmin() + 1

    fig5, ax5 = plt.subplots(figsize=(7.5, 3.6), facecolor='white')
    ax5.set_facecolor('white')
    ax5.plot(range(1, 366), close, color='#a3224b', label='Giá đóng cửa')
    ax5.scatter([ngay_cao, ngay_thap], [gia_cao, gia_thap], color='black', s=45, zorder=5, label='Cao/thấp nhất')
    ax5.set_xlabel('Ngày giao dịch', fontsize=9.5)
    ax5.set_ylabel('Giá (VND)', fontsize=9.5)
    ax5.set_title('Xu hướng giá trong năm', fontsize=10.5)
    ax5.legend(fontsize=8.5, loc='upper right')
    charts['chart5'] = fig_to_base64(fig5)

    return charts

market_data_list = load_market_data()
market_data_json = json.dumps(market_data_list)
auto_charts = generate_charts()

# ========================================================
# 3. GIAO DIỆN HTML (GIỮ NGUYÊN TOÀN BỘ PHẦN TRÊN, CHỈ THÊM MỤC PHÂN TÍCH Ở DƯỚI)
# ========================================================
HTML_CONTENT = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Báo cáo Mô phỏng Biến động Giá Chứng khoán</title>
    <style>
        :root {{
            --bg-pastel: #FFD1DC;
            --dark-card: #1e1e1e;
            --white-card: #ffffff;
            --text-main: #222222;
            --accent-pink: #a3224b;
        }}
        body {{
            margin: 0;
            padding: 24px 16px;
            background-color: var(--bg-pastel);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            box-sizing: border-box;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        h1 {{
            color: var(--text-main);
            font-size: 24px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
        }}
        .main-container {{
            display: flex;
            flex-direction: column;
            gap: 20px;
            max-width: 1100px;
            width: 100%;
        }}
        /* Khung video kéo rộng toàn bộ chiều ngang (CŨ) */
        .video-box {{
            background-color: var(--dark-card);
            padding: 12px;
            border-radius: 14px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            width: 100%;
            box-sizing: border-box;
        }}
        video {{
            width: 100%;
            height: auto;
            border-radius: 8px;
            display: block;
        }}
        /* Hàng chứa 2 khung bên dưới (CŨ) */
        .bottom-cards {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            width: 100%;
        }}
        .card {{
            background-color: var(--white-card);
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
            box-sizing: border-box;
        }}
        .card h2 {{
            margin-top: 0;
            margin-bottom: 12px;
            font-size: 16px;
            color: #333;
            border-bottom: 2px solid #fce7f3;
            padding-bottom: 8px;
        }}
        .color-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .color-table td {{
            padding: 7px 4px;
            font-size: 13.5px;
            border-bottom: 1px solid #f1f5f9;
        }}
        .color-badge {{
            display: inline-block;
            width: 15px;
            height: 15px;
            border-radius: 4px;
            vertical-align: middle;
            margin-right: 6px;
        }}
        .metric-grid {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .metric-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13.5px;
            padding: 4px 0;
            border-bottom: 1px dashed #e2e8f0;
        }}
        .metric-item:last-child {{
            border-bottom: none;
        }}
        .metric-label {{
            color: #555;
        }}
        .metric-val {{
            font-weight: 700;
            color: #111;
        }}
        .note {{
            font-size: 12px;
            color: #555;
            margin-top: 10px;
            line-height: 1.4;
            background: #fafafa;
            padding: 6px 10px;
            border-radius: 6px;
            border-left: 3px solid #f472b6;
        }}

        /* PHẦN MỚI THÊM: DANH SÁCH 5 MỤC PHÂN TÍCH Ở DƯỚI */
        .section-header {{
            text-align: center;
            margin: 15px 0 5px 0;
        }}
        .section-header h2 {{
            font-size: 19px;
            color: var(--accent-pink);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0;
        }}
        .analysis-list {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .item-card {{
            background-color: var(--white-card);
            border-radius: 14px;
            padding: 22px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
        }}
        .item-card h3 {{
            margin-top: 0;
            color: var(--accent-pink);
            font-size: 16.5px;
            border-bottom: 1px solid #fce7f3;
            padding-bottom: 8px;
        }}
        .item-body {{
            display: grid;
            grid-template-columns: 1.15fr 1fr;
            gap: 20px;
            align-items: center;
            margin-top: 12px;
        }}
        .img-container {{
            background: #ffffff;
            border: 1px solid #fce7f3;
            border-radius: 10px;
            padding: 6px;
            text-align: center;
        }}
        .img-container img {{
            width: 100%;
            height: auto;
            border-radius: 6px;
            display: block;
        }}
        .desc-text {{
            font-size: 14px;
            line-height: 1.6;
            color: #374151;
        }}
        .desc-text p {{
            margin: 0;
        }}
        .desc-text strong {{
            color: #111827;
        }}

        @media (max-width: 850px) {{
            .bottom-cards {{
                grid-template-columns: 1fr;
            }}
            .item-body {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <h1>BÁO CÁO MÔ PHỎNG BIẾN ĐỘNG GIÁ CHỨNG KHOÁN</h1>
    
    <div class="main-container">
        <!-- Khung phát Video lớn ở trên (GIỮ NGUYÊN) -->
        <div class="video-box">
            <video id="stockVideo" controls autoplay loop muted playsinline>
                <source src="/static/mo_phong.mp4" type="video/mp4">
                Trình duyệt không hỗ trợ xem video.
            </video>
        </div>

        <!-- 2 Khung thông tin xếp ngang ở dưới (GIỮ NGUYÊN) -->
        <div class="bottom-cards">
            <!-- Khung 1: Quy ước màu sắc -->
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

            <!-- Khung 2: Chỉ số chi tiết nhảy theo video -->
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

        <!-- KHU VỰC BỔ SUNG: 5 MỤC PHÂN TÍCH (CHỈ GỒM HÌNH ẢNH & NHẬN XÉT) -->
        <div class="section-header">
            <h2>Phân Tích Dữ Liệu Biến Động Giá</h2>
        </div>

        <div class="analysis-list">
            <!-- Mục 1 -->
            <div class="item-card">
                <h3>1. Giá trung bình mỗi tháng</h3>
                <div class="item-body">
                    <div class="img-container">
                        <img src="{auto_charts['chart1']}" alt="Giá trung bình mỗi tháng">
                    </div>
                    <div class="desc-text">
                        <p><strong>Nhận xét:</strong> Giá cổ phiếu đạt thị giá trung bình cao nhất ở giai đoạn Tháng 2 và Tháng 3 (quanh ngưỡng 12,000 VND). Từ sau Tháng 4, mặt bằng giá bắt đầu trượt dốc liên tục và chạm đáy vào Tháng 11 và Tháng 12 khi giá trung bình chỉ còn quanh 2,000 VND.</p>
                    </div>
                </div>
            </div>

            <!-- Mục 2 -->
            <div class="item-card">
                <h3>2. Phân bố giá theo tháng (Boxplot)</h3>
                <div class="item-body">
                    <div class="img-container">
                        <img src="{auto_charts['chart2']}" alt="Boxplot theo tháng">
                    </div>
                    <div class="desc-text">
                        <p><strong>Nhận xét:</strong> 
                            <br>• <strong>Tháng 1 đến Tháng 4:</strong> Thân hộp kéo dài và râu nến rộng, thể hiện biên độ dao động nội tháng rất lớn và sự bất ổn định cao.
                            <br>• <strong>Tháng 9 đến Tháng 12:</strong> Thân hộp co cụm lại sát đáy, phản ánh thanh khoản và biên độ dao động suy giảm khi giá đóng băng ở vùng đáy.
                        </p>
                    </div>
                </div>
            </div>

            <!-- Mục 3 -->
            <div class="item-card">
                <h3>3. Thống kê số lượng phiên giao dịch bất thường</h3>
                <div class="item-body">
                    <div class="img-container">
                        <img src="{auto_charts['chart3']}" alt="Các phiên bất thường">
                    </div>
                    <div class="desc-text">
                        <p><strong>Nhận xét:</strong> Toàn bộ 365 phiên ghi nhận <strong>118 phiên chạm sàn</strong> và <strong>114 phiên kịch trần</strong>[cite: 27]. Các phiên trần xuất hiện dày đặc trong chu kỳ bứt phá đầu năm, trong khi các phiên sàn tập trung ở sườn dốc giảm giá khi cổ phiếu chịu áp lực bán tháo liên tiếp[cite: 27].</p>
                    </div>
                </div>
            </div>

            <!-- Mục 4 -->
            <div class="item-card">
                <h3>4. Phân bố tần suất giá: 2 quý đầu năm vs 2 quý cuối năm</h3>
                <div class="item-body">
                    <div class="img-container">
                        <img src="{auto_charts['chart4']}" alt="Histogram 2 nửa năm">
                    </div>
                    <div class="desc-text">
                        <p><strong>Nhận xét:</strong> Hai giai đoạn thể hiện sự tương phản rõ rệt[cite: 27]. Hai quý đầu năm phân bố trải rộng ở vùng giá cao (tập trung từ 8,000 đến 16,000 VND)[cite: 27]. Ngược lại, hai quý cuối năm mật độ tần suất dồn cục bộ về bên trái, phần lớn các mức giá chỉ dao động dưới ngưỡng 5,000 VND[cite: 27].</p>
                    </div>
                </div>
            </div>

            <!-- Mục 5 -->
            <div class="item-card">
                <h3>5. Xu hướng giá trong năm</h3>
                <div class="item-body">
                    <div class="img-container">
                        <img src="{auto_charts['chart5']}" alt="Xu hướng giá trong năm">
                    </div>
                    <div class="desc-text">
                        <p><strong>Nhận xét:</strong> 
                            <br>• Giá bắt đầu tại 10,000 VND, bứt phá mạnh lên đỉnh cao nhất năm (đạt 18,628 VND) vào giai đoạn đầu năm[cite: 27].
                            <br>• Sau khi lập đỉnh, cổ phiếu bước vào chu kỳ suy thoái kéo dài, liên tục gãy các vùng hỗ trợ và rơi về đáy thấp nhất năm (chỉ còn 1,213 VND) trước khi đi ngang ở các phiên cuối năm[cite: 27].
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Script đồng bộ chỉ số theo tiến độ phát video (GIỮ NGUYÊN HOÀN TOÀN) -->
    <script>
        const video = document.getElementById('stockVideo');
        const marketData = {market_data_json};
        const totalDays = marketData.length;

        function updateMetrics() {{
            if (!video.duration || isNaN(video.duration)) return;
            const progress = Math.min(Math.max(video.currentTime / video.duration, 0), 1);
            let dayIndex = Math.floor(progress * totalDays);
            if (dayIndex >= totalDays) dayIndex = totalDays - 1;

            const d = marketData[dayIndex];
            if (!d) return;

            document.getElementById('metricTitle').innerText = `📊 Chỉ số chi tiết (Phiên Ngày ${{d.day}}/365)`;
            document.getElementById('valRef').innerText = `${{d.ref}} VND`;
            document.getElementById('valCeil').innerText = `${{d.ceil}} VND`;
            document.getElementById('valFloor').innerText = `${{d.floor}} VND`;
            document.getElementById('valHigh').innerText = `${{d.high}} VND`;
            document.getElementById('valLow').innerText = `${{d.low}} VND`;
            
            const closeEl = document.getElementById('valClose');
            closeEl.innerText = `${{d.close}} VND`;
            closeEl.style.color = d.color;

            const noteEl = document.getElementById('metricNote');
            noteEl.innerHTML = `* Phiên Ngày ${{d.day}}: Đóng cửa <strong>${{d.status}}</strong>, cây nến mang màu tương ứng.`;
        }}

        function renderLoop() {{
            updateMetrics();
            if (!video.paused && !video.ended) {{
                requestAnimationFrame(renderLoop);
            }}
        }}

        video.addEventListener('play', () => requestAnimationFrame(renderLoop));
        video.addEventListener('timeupdate', updateMetrics);
        video.addEventListener('seeked', updateMetrics);
        video.addEventListener('loadedmetadata', updateMetrics);
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_CONTENT