import streamlit as st
import pandas as pd
import datetime
import math
import statistics
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import requests
import openai
import anthropic
import calendar
from datetime import timedelta
import altair as alt
import re

# ==========================================
# 1. ページ設定とUI改善CSS
# ==========================================
st.set_page_config(
    page_title="プレミアム裏ステータス診断",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    div[data-testid="stButton"] button { padding: 0.2rem 0.5rem; min-height: 2.5rem; }
    div.stButton { margin-bottom: -15px; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    .stApp, .stApp > header, .stApp .main { background-color: #FFFFFF !important; }
    h1, h2, h3, h4, h5, h6, p, span, div, label, li { color: #000000 !important; }
    button[kind="secondary"] { width: 100% !important; height: 65px !important; font-size: 18px !important; font-weight: 900 !important; color: #000000 !important; background-color: #FFFFFF !important; border: 3px solid #444444 !important; border-radius: 12px !important; margin-bottom: 12px !important; transition: all 0.2s ease-in-out !important; box-shadow: 0px 4px 6px rgba(0,0,0,0.05) !important; }
    button[kind="secondary"]:hover { background-color: #F5F5F5 !important; border-color: #111111 !important; }
    button[kind="secondary"]:active { background-color: #E0E0E0 !important; transform: translateY(2px) !important; box-shadow: 0px 0px 0px rgba(0,0,0,0) !important; }
    button[kind="primary"] { width: 100% !important; height: 60px !important; font-size: 18px !important; font-weight: 900 !important; border: none !important; border-radius: 12px !important; transition: all 0.2s ease-in-out !important; box-shadow: 0px 4px 6px rgba(0,0,0,0.1) !important; }
    button[kind="primary"]:active { transform: translateY(2px) !important; box-shadow: 0px 0px 0px rgba(0,0,0,0) !important; }
    div[data-testid="stLinkButton"] > a { background-color: #06C755 !important; color: white !important; border: none !important; font-weight: bold !important; width: 100% !important; height: 60px !important; display: flex !important; align-items: center !important; justify-content: center !important; border-radius: 12px !important; font-size: 18px !important; text-decoration: none !important; box-shadow: 0px 4px 6px rgba(0,0,0,0.1) !important; transition: all 0.2s ease-in-out !important; }
    div[data-testid="stLinkButton"] > a:hover { background-color: #05b34c !important; }
    .question-title { font-size: 1.4rem; font-weight: 900; text-align: center; margin-top: 1rem !important; margin-bottom: 1rem !important; line-height: 1.6; color: #000000 !important; }
    .stSelectbox label, .stTextInput label, .stRadio label { font-weight: 900 !important; font-size: 1.1rem !important; color: #000000 !important; }
    .stRadio div[role="radiogroup"] label span { color: #000000 !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 本番用 Big5 質問データ (50問)
# ==========================================
QUESTIONS = [
    {"id": 1, "text": "新しいアイデアや企画を考えるのが好きだ。", "trait": "O", "is_reverse": False},
    {"id": 2, "text": "芸術、音楽、文化的なものに深く心を動かされる。", "trait": "O", "is_reverse": False},
    {"id": 3, "text": "ルーティンワーク（単純作業）よりも、変化のある環境を好む。", "trait": "O", "is_reverse": False},
    {"id": 4, "text": "複雑で抽象的な概念について考えるのが得意だ。", "trait": "O", "is_reverse": False},
    {"id": 5, "text": "慣習や伝統にとらわれず、新しいやり方を試したい。", "trait": "O", "is_reverse": False},
    {"id": 6, "text": "未知の分野や、自分の知らない世界について学ぶことにワクワクする。", "trait": "O", "is_reverse": False},
    {"id": 7, "text": "想像力が豊かで、つい空想にふけることがある。", "trait": "O", "is_reverse": False},
    {"id": 8, "text": "物事の表面だけでなく、背後にある「なぜ？」を深く追求する。", "trait": "O", "is_reverse": False},
    {"id": 9, "text": "哲学的、あるいは思想的な議論を交わすことに喜びを感じる。", "trait": "O", "is_reverse": False},
    {"id": 10, "text": "想像を膨らませるより、現実的で具体的な事実だけを見ていたい。", "trait": "O", "is_reverse": True},
    {"id": 11, "text": "仕事や作業は、細部まで正確に仕上げないと気が済まない。", "trait": "C", "is_reverse": False},
    {"id": 12, "text": "立てた計画は、最後までスケジュール通りに実行する自信がある。", "trait": "C", "is_reverse": False},
    {"id": 13, "text": "身の回りの整理整頓が常にできている方だ。", "trait": "C", "is_reverse": False},
    {"id": 14, "text": "面倒なことでも、一度引き受けた約束や責任は必ず果たす。", "trait": "C", "is_reverse": False},
    {"id": 15, "text": "衝動買いや、その場のノリでの行動はあまりしない。", "trait": "C", "is_reverse": False},
    {"id": 16, "text": "目標達成のためなら、目先の遊びや誘惑を我慢できる。", "trait": "C", "is_reverse": False},
    {"id": 17, "text": "仕事に取り掛かるのが早く、ギリギリまで先延ばしにすることはない。", "trait": "C", "is_reverse": False},
    {"id": 18, "text": "効率を常に意識し、無駄のない動きを心がけている。", "trait": "C", "is_reverse": False},
    {"id": 19, "text": "ミスを防ぐため、提出前や完了前に必ず二重チェックを行う。", "trait": "C", "is_reverse": False},
    {"id": 20, "text": "計画を立てるのが苦手で、行き当たりばったりで行動しがちだ。", "trait": "C", "is_reverse": True},
    {"id": 21, "text": "初対面の人とも、緊張せずにすぐ打ち解けられる。", "trait": "E", "is_reverse": False},
    {"id": 22, "text": "飲み会やイベントなど、人が多く集まる活気ある場所が好きだ。", "trait": "E", "is_reverse": False},
    {"id": 23, "text": "チームや集団の中では、自らリーダーシップを取ることが多い。", "trait": "E", "is_reverse": False},
    {"id": 24, "text": "休日は一人で過ごすより、誰かと会ってエネルギーをチャージしたい。", "trait": "E", "is_reverse": False},
    {"id": 25, "text": "自分の意見や考えを、ためらわずにハッキリと主張できる。", "trait": "E", "is_reverse": False},
    {"id": 26, "text": "会話の中心になり、場を盛り上げるのが得意な方だ。", "trait": "E", "is_reverse": False},
    {"id": 27, "text": "話すスピードや行動のテンポが、周りの人より早いと言われる。", "trait": "E", "is_reverse": False},
    {"id": 28, "text": "ポジティブな感情（喜び・楽しさ）を、素直に大きく表現する。", "trait": "E", "is_reverse": False},
    {"id": 29, "text": "人と話すことで思考が整理され、新しいアイデアが湧いてくる。", "trait": "E", "is_reverse": False},
    {"id": 30, "text": "大勢でワイワイ騒ぐよりも、少人数で静かに過ごす方が好きだ。", "trait": "E", "is_reverse": True},
    {"id": 31, "text": "困っている人を見ると、自分の作業を止めてでも助けたくなる。", "trait": "A", "is_reverse": False},
    {"id": 32, "text": "チーム内での対立や揉め事を避けるためなら、自分が折れることができる。", "trait": "A", "is_reverse": False},
    {"id": 33, "text": "相手の些細な感情の変化に気づき、共感するのが得意だ。", "trait": "A", "is_reverse": False},
    {"id": 34, "text": "他人の長所を見つけ、素直に褒めることができる。", "trait": "A", "is_reverse": False},
    {"id": 35, "text": "人から頼み事をされると、嫌とは言えず引き受けてしまうことが多い。", "trait": "A", "is_reverse": False},
    {"id": 36, "text": "競争して勝つことよりも、全員で協力して成果を出すことに価値を感じる。", "trait": "A", "is_reverse": False},
    {"id": 37, "text": "他人のミスに対して寛容で、厳しく責め立てることはしない。", "trait": "A", "is_reverse": False},
    {"id": 38, "text": "自分の利益よりも、周囲の人やチーム全体の利益を優先しがちだ。", "trait": "A", "is_reverse": False},
    {"id": 39, "text": "誰に対しても丁寧で、礼儀正しい態度で接することを心がけている。", "trait": "A", "is_reverse": False},
    {"id": 40, "text": "他人の悩みやトラブルには、正直あまり関心がない。", "trait": "A", "is_reverse": True},
    {"id": 41, "text": "プレッシャーのかかる場面では、極度に緊張したり不安になりやすい。", "trait": "N", "is_reverse": False},
    {"id": 42, "text": "他人からの何気ない一言を、深く気に病んでしまうことがある。", "trait": "N", "is_reverse": False},
    {"id": 43, "text": "失敗した時のことを考えると、心配で行動を起こせなくなる。", "trait": "N", "is_reverse": False},
    {"id": 44, "text": "気分が落ち込みやすく、立ち直るまでに時間がかかる方だ。", "trait": "N", "is_reverse": False},
    {"id": 45, "text": "予想外のトラブルが起きると、パニックになり冷静な判断ができなくなる。", "trait": "N", "is_reverse": False},
    {"id": 46, "text": "自分の能力や将来について、強い焦りや劣等感を感じることがある。", "trait": "N", "is_reverse": False},
    {"id": 47, "text": "イライラしやすく、些細なことで感情的になってしまうことがある。", "trait": "N", "is_reverse": False},
    {"id": 48, "text": "夜、考え事をしてしまい眠れなくなる日がよくある。", "trait": "N", "is_reverse": False},
    {"id": 49, "text": "ストレスが溜まると、体調（胃腸や頭痛など）にすぐ表れる。", "trait": "N", "is_reverse": False},
    {"id": 50, "text": "どんなピンチの状況でも、常にリラックスして冷静でいられる。", "trait": "N", "is_reverse": True}
]

# ==========================================
# 対人関係レーダー用 SJT質問データ (12問)
# ==========================================
RADAR_QUESTIONS = [
    {"id": 1, "category": "社会・情報", "text": "Q1. 相手の話すスピードや声のトーンはどうですか？", "options": ["早口で声が大きい・身振りが大きい", "普通・その場に合わせる", "ゆっくりで声は小さめ・落ち着いている", "わからない/観察していない"]},
    {"id": 2, "category": "社会・情報", "text": "Q2. 相手はLINEやメッセージをどう使いますか？", "options": ["要件のみで短く、絵文字は少ない", "スタンプや絵文字をよく使い、雑談もする", "返信が極端に早い、または極端に遅い", "わからない/観察していない"]},
    {"id": 3, "category": "社会・情報", "text": "Q3. 相手の服装や持ち物の傾向は？", "options": ["実用性やコスパを重視している", "ブランドや流行、デザイン性を重視している", "無頓着、またはいつも同じような服装", "わからない/観察していない"]},
    {"id": 4, "category": "恋愛・愛着", "text": "Q4. 相手は自分の弱みや失敗談、プライベートな悩みを話してきますか？", "options": ["自分からよく話してくる（自己開示が多い）", "聞かれれば話すが、自分からはあまり話さない", "絶対にはぐらかす・秘密主義", "わからない/観察していない"]},
    {"id": 5, "category": "恋愛・愛着", "text": "Q5. 相手は「深夜や休日」など、プライベートな時間に仕事や用事以外の連絡をしてきますか？", "options": ["遠慮なくしてくる（境界線が薄い）", "基本的には常識的な時間のみ", "全くしてこない・連絡が取りづらい", "わからない/観察していない"]},
    {"id": 6, "category": "恋愛・愛着", "text": "Q6. 相手が他人に感謝や愛情を示す時、どの行動が多いですか？", "options": ["言葉で「ありがとう」「すごいね」と褒める", "お土産やプレゼントなど「モノ」をくれる", "仕事や作業を「手伝ってくれる（行動）」", "わからない/観察していない"]},
    {"id": 7, "category": "非常時・闘争", "text": "Q7. 予定外のトラブル（行きたい店が閉まっていた等）が起きた時の反応は？", "options": ["すぐにスマホで次の解決策を探す（論理的）", "明らかに不機嫌になったり、口数が減る（感情的）", "「どうする？」と他人に判断を委ねる（依存的）", "わからない/観察していない"]},
    {"id": 8, "category": "非常時・闘争", "text": "Q8. 相手がミスや失敗を指摘された時、最初にとる態度は？", "options": ["素直に非を認め、すぐに謝罪する", "「でも」「だって」と言い訳や反論から入る", "極度に落ち込んだり、自虐的になる", "わからない/観察していない"]},
    {"id": 9, "category": "非常時・闘争", "text": "Q9. 意見が対立した時や、怒りを感じた時、相手はどう表現しますか？", "options": ["正論で理詰めにしたり、声を荒らげる", "無視する、ため息をつく、嫌味を言う", "争いを避けてその場から逃げる・黙る", "わからない/観察していない"]},
    {"id": 10, "category": "コア・相性", "text": "Q10. あなたと会話している時、どちらがたくさん喋っていますか？", "options": ["相手の方が圧倒的に多く喋っている", "お互いに同じくらい", "自分（あなた）の方が多く喋っている", "わからない/観察していない"]},
    {"id": 11, "category": "コア・相性", "text": "Q11. 相手はあなたに対して、アドバイスや指示をしてくる（マウントをとる）傾向がありますか？", "options": ["よくしてくる（教えたがり・上から目線）", "対等な立場で意見を交換する", "あなたの意見に同調・追従することが多い", "わからない/観察していない"]},
    {"id": 12, "category": "コア・相性", "text": "Q12. 相手の「店員やタクシー運転手（第三者）」への態度はどうですか？", "options": ["とても丁寧で腰が低い", "普通・事務的", "横柄、または偉そうな態度をとる事がある", "わからない/観察していない"]}
]

# ==========================================
# 対人関係レーダー用：残回数（BU列）管理関数
# ==========================================
def check_radar_limit(line_id):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_url = st.secrets["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url).sheet1
        all_data = sheet.get_all_values()
        
        headers = all_data[0]
        limit_idx = 72
        for i, h in enumerate(headers):
            if h == '残回数': 
                limit_idx = i
                break
                
        for row in reversed(all_data[1:]):
            if len(row) > 0 and row[0] == line_id:
                if len(row) > limit_idx:
                    try: return int(row[limit_idx])
                    except ValueError: return 3
                return 3
        return 0
    except Exception as e:
        print(f"残回数チェックエラー: {e}")
        return 0

def consume_radar_limit(line_id):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_url = st.secrets["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url).sheet1
        
        headers = sheet.row_values(1)
        limit_col_letter = 'BU'
        for i, h in enumerate(headers):
            if h == '残回数':
                if i < 26: limit_col_letter = chr(65 + i)
                else: limit_col_letter = chr(64 + (i // 26)) + chr(65 + (i % 26))
                break
                
        all_data = sheet.get_all_values()
        target_row_idx = -1
        current_limit = 3
        
        for i in range(len(all_data)-1, 0, -1):
            if len(all_data[i]) > 0 and all_data[i][0] == line_id:
                target_row_idx = i + 1
                col_idx = headers.index('残回数') if '残回数' in headers else 72
                if len(all_data[i]) > col_idx:
                    try: current_limit = int(all_data[i][col_idx])
                    except: current_limit = 3
                break
                
        if target_row_idx != -1 and current_limit > 0:
            new_limit = current_limit - 1
            cell_address = f"{limit_col_letter}{target_row_idx}"
            sheet.update_acell(cell_address, new_limit)
            return True
        return False
    except Exception as e:
        print(f"残回数消費エラー: {e}")
        return False

# ==========================================
# 算命学計算＆プロンプトエンジン
# ==========================================
def calculate_sanmeigaku(year, month, day, time_str):
    try:
        target_date = datetime.date(year, month, day)
        elapsed = (target_date - datetime.date(1900, 1, 1)).days
        day_kanshi_num = (10 + elapsed) % 60 + 1
        day_stem = (day_kanshi_num - 1) % 10 + 1
        day_branch = (day_kanshi_num - 1) % 12 + 1
        
        stems_str = ["", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        branches_str = ["", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        nikkanshi = stems_str[day_stem] + branches_str[day_branch]
        
        tenchusatsu_map = {0: "戌亥", 2: "申酉", 4: "午未", 6: "辰巳", 8: "寅卯", 10: "子丑"}
        diff = (day_branch - day_stem) % 12
        tenchusatsu = tenchusatsu_map.get(diff, "")
        
        solar_m = month if day >= 5 else month - 1
        solar_y = year
        if solar_m == 0:
            solar_m = 12
            solar_y -= 1
        if solar_m == 1:
            solar_y -= 1
        
        month_branch = (solar_m + 1) % 12
        if month_branch == 0: month_branch = 12
        year_branch = (solar_y - 3) % 12
        if year_branch == 0: year_branch = 12
        
        hon_gen_map = {1:10, 2:6, 3:1, 4:2, 5:5, 6:3, 7:4, 8:6, 9:7, 10:8, 11:5, 12:9}
        month_hidden_stem = hon_gen_map[month_branch]
        
        me_el = (day_stem - 1) // 2
        other_el = (month_hidden_stem - 1) // 2
        rel = (other_el - me_el) % 5
        same_parity = (day_stem % 2) == (month_hidden_stem % 2)
        
        stars_matrix = [
            ["貫索星", "石門星"], ["鳳閣星", "調舒星"], ["禄存星", "司禄星"],
            ["車騎星", "牽牛星"], ["龍高星", "玉堂星"]
        ]
        main_star = stars_matrix[rel][0 if same_parity else 1]
        
        # 西方星の追加
        day_hidden_stem = hon_gen_map[day_branch]
        d_other_el = (day_hidden_stem - 1) // 2
        d_rel = (d_other_el - me_el) % 5
        d_same_parity = (day_stem % 2) == (day_hidden_stem % 2)
        west_star = stars_matrix[d_rel][0 if d_same_parity else 1]
        
        star_names = ["天報星", "天印星", "天貴星", "天恍星", "天南星", "天禄星", "天将星", "天堂星", "天胡星", "天極星", "天庫星", "天馳星"]
        chosei_map = {1:12, 2:7, 3:3, 4:10, 5:3, 6:10, 7:6, 8:1, 9:9, 10:4}

        def get_12star(target_branch):
            if day_stem % 2 != 0: offset = (target_branch - chosei_map[day_stem]) % 12
            else: offset = (chosei_map[day_stem] - target_branch) % 12
            return star_names[(2 + offset) % 12]
            
        shonen = get_12star(year_branch)
        chunen = get_12star(month_branch)
        bannen = get_12star(day_branch)

        # 出生時間の透明化
        if not time_str or time_str.strip() == "":
            jikanshi = "不明"
            saibannen = "不明"
        else:
            try:
                clean_time = time_str.replace("：", ":").replace(" ", "").strip()
                if ":" in clean_time: hour = int(clean_time.split(':')[0])
                elif len(clean_time) == 4 and clean_time.isdigit(): hour = int(clean_time[:2])
                elif len(clean_time) == 3 and clean_time.isdigit(): hour = int(clean_time[:1])
                else: hour = 12
                
                time_branch = ((hour + 1) // 2) % 12 + 1
                goso_map = {1: 1, 6: 1, 2: 3, 7: 3, 3: 5, 8: 5, 4: 7, 9: 7, 5: 9, 10: 9}
                base_time_stem = goso_map[day_stem]
                time_stem = (base_time_stem + time_branch - 2) % 10 + 1
                jikanshi = stems_str[time_stem] + branches_str[time_branch]
                saibannen = get_12star(time_branch)
            except Exception:
                jikanshi = "不明"
                saibannen = "不明"
            
        return {
            "日干支": nikkanshi, "天中殺": tenchusatsu, 
            "主星": main_star, "西方星": west_star,
            "初年": shonen, "中年": chunen, "晩年": bannen,
            "時干支": jikanshi, "最晩年": saibannen
        }
    except Exception as e:
        print(f"算命学エンジンエラー: {e}")
        return {
            "日干支": "不明", "天中殺": "不明", "主星": "不明", "西方星": "不明",
            "初年": "不明", "中年": "不明", "晩年": "不明", "時干支": "不明", "最晩年": "不明"
        }

def calculate_target_sanmeigaku(dob_str):
    try:
        valid_date = datetime.datetime.strptime(dob_str, "%Y%m%d").date()
        year = valid_date.year
        month = valid_date.month
        day = valid_date.day
        return calculate_sanmeigaku(year, month, day, "")
    except Exception as e:
        print(f"ターゲット算命学計算エラー: {e}")
        return None

def get_date_kanshi(target_date):
    elapsed = (target_date - datetime.date(1900, 1, 1)).days
    day_kanshi_num = (10 + elapsed) % 60 + 1
    day_stem = (day_kanshi_num - 1) % 10 + 1
    day_branch = (day_kanshi_num - 1) % 12 + 1
    
    stems_str = ["", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branches_str = ["", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    solar_m = target_date.month if target_date.day >= 5 else target_date.month - 1
    solar_y = target_date.year
    if solar_m == 0:
        solar_m = 12
        solar_y -= 1
    if solar_m == 1:
        solar_y -= 1
        
    month_branch = (solar_m + 1) % 12
    if month_branch == 0: month_branch = 12
    year_branch = (solar_y - 3) % 12
    if year_branch == 0: year_branch = 12
    
    month_stem = ((solar_y % 10) * 2 + solar_m) % 10
    if month_stem == 0: month_stem = 10
    year_stem = (solar_y - 3) % 10
    if year_stem == 0: year_stem = 10
    
    return {
        "day": stems_str[day_stem] + branches_str[day_branch],
        "month": stems_str[month_stem] + branches_str[month_branch],
        "year": stems_str[year_stem] + branches_str[year_branch],
        "day_stem_idx": day_stem, "day_branch_idx": day_branch,
        "month_stem_idx": month_stem, "month_branch_idx": month_branch,
        "year_stem_idx": year_stem, "year_branch_idx": year_branch
    }

def calculate_period_score(user_nikkanshi, target_date, period_type="day"):
    target = get_date_kanshi(target_date)
    stems_str = ["", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branches_str = ["", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    user_stem_str = user_nikkanshi[0]
    user_branch_str = user_nikkanshi[1]
    user_stem = stems_str.index(user_stem_str)
    user_branch = branches_str.index(user_branch_str)
    
    if period_type == "day":
        target_stem = target["day_stem_idx"]
        target_branch = target["day_branch_idx"]
    elif period_type == "month":
        target_stem = target["month_stem_idx"]
        target_branch = target["month_branch_idx"]
    elif period_type == "year":
        target_stem = target["year_stem_idx"]
        target_branch = target["year_branch_idx"]
    
    env_score = 3
    env_reason = "安定した通常期"
    
    tenchusatsu_map = {0: [11, 12], 2: [9, 10], 4: [7, 8], 6: [5, 6], 8: [3, 4], 10: [1, 2]}
    diff = (user_branch - user_stem) % 12
    t_branches = tenchusatsu_map.get(diff, [])
    
    if target_branch in t_branches:
        env_score = 1
        env_reason = "天中殺（リセット・向かい風）"
    else:
        if abs(user_branch - target_branch) == 6:
            env_score = 1
            env_reason = "冲（衝突・リセット）"
        elif abs(user_branch - target_branch) in [4, 8]:
            if user_stem == target_stem:
                env_score = 5
                env_reason = "大半会（異常な追い風）"
            else:
                env_score = 4
                env_reason = "半会（スムーズな前進）"
        elif (user_branch + target_branch) % 12 in [3, 5]:
            env_score = 4
            env_reason = "支合（結びつき・前進）"
        elif abs(user_branch - target_branch) in [3, 9, 2, 10]:
            env_score = 2
            env_reason = "刑・害（調整・ノイズ）"
            
    mind_score = 3
    mind_reason = "通常の精神状態"
    
    me_el = (user_stem - 1) // 2
    other_el = (target_stem - 1) // 2
    rel = (other_el - me_el) % 5
    same_parity = (user_stem % 2) == (target_stem % 2)
    
    stars_matrix = [
        ["貫索星(独立/守り)", "石門星(協調/政治)"],
        ["鳳閣星(表現/伝達)", "調舒星(孤独/芸術)"],
        ["禄存星(引力/回転財)", "司禄星(蓄積/家庭)"],
        ["車騎星(攻撃/前進)", "牽牛星(責任/名誉)"],
        ["龍高星(変化/忍耐)", "玉堂星(伝統/静寂)"]
    ]
    star_name = stars_matrix[rel][0 if same_parity else 1]
    
    if "車騎星" in star_name or "禄存星" in star_name: mind_score = 5; mind_reason = star_name
    elif "貫索星" in star_name or "鳳閣星" in star_name: mind_score = 4; mind_reason = star_name
    elif "石門星" in star_name or "司禄星" in star_name: mind_score = 3; mind_reason = star_name
    elif "龍高星" in star_name or "調舒星" in star_name: mind_score = 2; mind_reason = star_name
    else: mind_score = 1; mind_reason = star_name

    total_score = env_score + mind_score
    safe_score = max(1, min(10, total_score))
    
    action_dict = {
        10: {"sym": "🌈", "title": "超幸運の波", "desc": "限界を超えて物事が予想以上の規模で大きく広がる奇跡的なタイミングです。", "points": ["限界を決めずにスケールの大きな目標を立てる", "直感を信じて、普段なら躊躇する大勝負に出る", "周囲を巻き込みながら、リーダーシップを発揮する"]},
        9: {"sym": "⭐️", "title": "最高にツイてる波", "desc": "パズルのピースがピタッとハマるように物事が計画通りに進みます。", "points": ["夢の実現に向けて思い切って行動する", "自分の意見や感覚を大事にする", "ここで決めた目標や内容は、簡単には諦めない"]},
        8: {"sym": "🔴", "title": "迷わず動く波", "desc": "心の奥底から情熱が湧き上がり、スピーディーに物事を前進させられる時です。", "points": ["頭で考える前に、まずは第一歩を踏み出す", "自分の思いやアイデアを積極的に発信する", "多少の失敗は気にせず、スピードを最優先する"]},
        7: {"sym": "⚪️", "title": "思い切って決断する波", "desc": "これまでの曖昧な状態に白黒をつけ、新しいステージへ進むためのエネルギーに満ちています。", "points": ["先延ばしにしていた問題に明確な決断を下す", "不要な人間関係や悪習慣を思い切って断ち切る", "自分の信念を曲げず、毅然とした態度を貫く"]},
        6: {"sym": "🟡", "title": "基礎を固める波", "desc": "派手な動きよりも、足元を固めて実力を蓄えることで運気が安定します。", "points": ["新しいことよりも、今あるタスクを丁寧に仕上げる", "周囲への感謝や手助けを惜しまない", "資産運用や貯蓄など、現実的な管理を見直す"]},
        5: {"sym": "🟢", "title": "味方が増える波", "desc": "あなたの魅力が自然と伝わり、周囲との調和が生まれやすい時です。", "points": ["積極的に人と会い、コミュニケーションを楽しむ", "困っている人がいれば、損得抜きで手を差し伸べる", "新しいコミュニティや学びの場に参加してみる"]},
        4: {"sym": "🔵", "title": "頭の中を整理する波", "desc": "外に向かって動くよりも、内省し、知識を吸収することで運気が研ぎ澄まされます。", "points": ["一人の時間を確保し、静かに自分と向き合う", "読書や勉強などで、新しい知識をインプットする", "現状のやり方に固執せず、柔軟な視点を取り入れる"]},
        3: {"sym": "🟪", "title": "無理をしない波", "desc": "思い通りに進まないことや、人間関係での小さな摩擦が起きやすい調整期です。", "points": ["スケジュールに余白を持たせ、時間に余裕を行動する", "意見が対立した時は、一歩引いて相手を立てる", "ストレスを感じたら、無理せず早めに休息をとる"]},
        2: {"sym": "⬜️", "title": "不要なものを手放す波", "desc": "物事がぶつかり合い、変化を余儀なくされる時です。不要なものを捨てる儀式です。", "points": ["執着している過去の栄光やネガティブな感情を捨てる", "部屋の掃除やデジタルデータの断捨離を徹底する", "予定が急に変わっても、焦らず流れに身を任せる"]},
        1: {"sym": "⚫️", "title": "心と体を休ませる波", "desc": "現実の枠組みが外れ、コントロールが効かない「完全な休息とリセット」の期間です。", "points": ["新しい挑戦、大きな決断、高価な買い物は避ける", "損得勘定を捨て、ボランティアや人のために尽くす", "スマホやPCから離れ、たっぷりと睡眠をとる"]}
    }
    action_data = action_dict[safe_score]
        
    return {
        "score": safe_score, "symbol": action_data["sym"], "title": action_data["title"],
        "desc": action_data["desc"], "points": action_data["points"],
        "env_reason": env_reason, "mind_reason": mind_reason, "date_str": target_date.strftime("%Y/%m/%d")
    }

def get_rule_based_stars(score, mind_reason):
    if score >= 9: base_star = "★★★"
    elif score >= 5: base_star = "★★☆"
    else: base_star = "★☆☆"
        
    stars = {
        "総合運": "★★★" if score >= 8 else ("★★☆" if score >= 4 else "★☆☆"),
        "人間関係": "★★★" if "石門" in mind_reason or "禄存" in mind_reason else base_star,
        "仕事運": "★★★" if "車騎" in mind_reason or "牽牛" in mind_reason else base_star,
        "恋愛結婚": "★★★" if "禄存" in mind_reason or "司禄" in mind_reason else base_star,
        "金運": "★★★" if "禄存" in mind_reason or "司禄" in mind_reason else base_star,
        "健康運": "★★★" if score >= 5 else "★☆☆",
        "家族親子": "★★★" if "玉堂" in mind_reason or "司禄" in mind_reason else base_star
    }
    if score <= 2: stars = {k: "★☆☆" for k in stars}
    return stars

def generate_report_prompt(sanmeigaku, scores, user_data):
    gender = user_data.get("Gender", "回答しない")
    gender_instruction = ""
    if gender in ["男性", "女性"]:
        gender_instruction = f"""
【サイレント・チューニング指示】
対象者の生物学的・進化心理学的な行動傾向（{gender}特有のストレス反応や社会的プレッシャー）を分析の裏付けとして組み込んでください。
"""

    prompt = f"""あなたは、専門用語を一切使わず、圧倒的な洞察力でユーザーの心を鷲掴みにする大人気の天才プロファイラー兼占い師です。ゲッターズ飯田氏のように、長所の裏にある「生々しい欠点や矛盾」を、具体的かつ的確に突くスタイルが特徴です。専門用語は絶対にそのまま出力しないでください。

# ユーザーの分析データ
・年齢/生年月日: {user_data.get("DOB")}
・職業/立場: {user_data.get("Job", "不明")}
・現在フォーカスしたい悩み: {user_data.get("Pains", "特になし")}
・具体的な悩みや理想(自由記述): {user_data.get("Free_Text", "特になし")}

[算命学]
日干支: {sanmeigaku['日干支']}, 天中殺: {sanmeigaku['天中殺']}
主星: {sanmeigaku['主星']}, 西方星: {sanmeigaku.get('西方星', '不明')}
12星: 初年[{sanmeigaku['初年']}], 中年[{sanmeigaku['中年']}], 晩年[{sanmeigaku['晩年']}], 最晩年[{sanmeigaku['最晩年']}]
[Big5スコア 1〜5]
O(開放性): {scores['O']}, C(勤勉性): {scores['C']}, E(外向性): {scores['E']}, A(協調性): {scores['A']}, N(神経症的傾向): {scores['N']}

{gender_instruction}

# 【絶対遵守の基本ルール】
1. 抽象表現の禁止: 必ず「休日は〇〇をしてしまう」「会議では〇〇な態度をとる」といった【超・具体的な日常の行動】で描写すること。
2. 摩擦の描写: 長所と短所（摩擦）を必ずセットで生々しく書くこと。
3. アドバイスの禁止: 解決策やアドバイス（例：〇〇しましょう等）は【絶対に一切書かない】こと。事実の提示のみ。
4. 絵文字の完全禁止: レポート内に絵文字は一切使用しないでください。

# 出力構成（以下のマークダウンと指定の順番・文言を1文字も変えずに必ず出力してください）

## 宿命と現実
宿命：[※本来の気質を表す、鋭く具体的な一言]
現実：[※現在の性格を表す、生々しくリアルな一言]

## あなたの中に眠る15の星
※絶対に表（テーブル）形式にはしないでください。必ず以下のように「・」を用いた箇条書きで15個出力してください。
・〇〇の星
・〇〇の星
（※これを15個出力する）

## 生まれ持った宿命と現在の性格のギャップ
### ■ 本来の宿命（あなたが持って生まれた基礎設計）
あなたが本来どんな環境で輝く人間なのかを、具体的な例えを用いて深く長く解説してください。
### ■ 現在の性格（今のあなたが作っている外観）
現在あなたが社会の中でどう振る舞っているか、本来の宿命とどうギャップが生じているかを生々しく書いてください。

## カテゴリ別・究極の自己分析
### ■ 仕事と才能
どういう環境だと輝き、どういう環境だと完全に腐るのかを断言してください。
### ■ 恋愛と人間関係
プライベート空間に入った途端にどう豹変するのかを生々しく解説してください。
### ■ お金と豊かさ
何にはお金を惜しまず、何には極端にケチになるのかを具体的に指摘してください。
### ■ 健康とメンタル
ストレスが限界に達した時に、どういう自滅的な行動をとってしまうのかを解説してください。

## あなたの5大欲求パラメーター
※5つの欲求を「異常値（95%）」のように数値化し、ドロドロした欲望や恐怖として解説してください。
1. 自我・自己実現欲：[〇〇%]
　[解説文]
2. 快楽・表現欲：[〇〇%]
　[解説文]
3. 引力・金銭欲：[〇〇%]
　[解説文]
4. 支配・達成欲：[〇〇%]
　[解説文]
5. 探求・知恵欲：[〇〇%]
　[解説文]

## 結びの言葉
自分自身の本性を受け入れることの重要性を説く、プロファイラーとしての重厚な言葉で締めくくってください。
"""
    return prompt

def generate_daily_advice(today_res):
    prompt = f"""
    あなたは、日本で最も予約が取れない戦略的ライフ・コンサルタントです。
    以下のデータをもとに、今日のユーザーへのアドバイスを作成してください。
    [スコア: {today_res['score']}点, シンボル: {today_res['symbol']}, 環境: {today_res['env_reason']}, 精神: {today_res['mind_reason']}]

    # 【絶対遵守の出力ルール】
    1. 算命学・四柱推命の専門用語は【絶対に】出力せず、現代の言葉に翻訳すること。
    2. モチベーションを上げる力強いトーンで書くこと。
    3. 7つの項目（総合、人間関係、仕事、恋愛結婚、金運、健康、家族）について、必ず【3段階評価（★☆☆、★★☆、★★★ のいずれか）】を付けてください。
    4. 【重要】ユーザーが行動をイメージしやすいように「例えば、車などの大きな契約は避けてください」といった『具体的なアクション例』を必ず各項目に入れてください。

    出力はマークダウン形式で「## 今日の運命の波（総合解説）」と「## 7つの指針と詳細解説」の構成にしてください。

    ## 今日の運命の波（総合解説）
    今日のスコアとシンボルの意味を現代の言葉でキャッチーに解説し、今日1日をどう過ごすべきか総括してください。

    ## 7つの指針と詳細解説
    ### 1. 総合運 [評価]
    [解説]
    ### 2. 人間関係運 [評価]
    [解説]
    ### 3. 仕事運 [評価]
    [解説]
    ### 4. 恋愛＆結婚運 [評価]
    [解説]
    ### 5. 金運（契約・買い物） [評価]
    [解説]
    ### 6. 健康運 [評価]
    [解説]
    ### 7. 家族・親子運 [評価]
    [解説]
    """
    try:
        openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは国内唯一の『戦略的ライフ・コンサルタント』です。専門用語は絶対に使わず、現代の言葉でアドバイスします。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API Error (Daily Advice): {e}")
        return "⚠️ 現在、AIアドバイザーが混み合っております。少し時間をおいて再度お試しください。"

def generate_radar_prompt(target_name, relation, answers_dict, free_text, target_san, user_main_star):
    sjt_text = ""
    for q in RADAR_QUESTIONS:
        ans_idx = answers_dict.get(q["id"], 3)
        ans_str = q["options"][ans_idx]
        sjt_text += f"- {q['text']}\n  回答: {ans_str}\n"
        
    prompt = f"""あなたは元FBIプロファイラーであり、日本一の戦略的ライフ・コンサルタントです。
ユーザーが入力した「行動データ」と「算命学の宿命データ」から、相手の真の姿をプロファイリングしてください。

【ターゲット情報】
名前: {target_name}
あなたとの関係: {relation}
算命学データ: 主星(社会の顔)={target_san['主星']}, 西方星(恋愛・家庭の顔)={target_san['西方星']}, 天中殺={target_san['天中殺']}

【ユーザー情報】
ユーザー自身の主星: {user_main_star}

【行動観察データ（SJT）】
{sjt_text}

【自由記述（エピソード）】
{free_text if free_text else '特になし'}

【絶対遵守のシステムルール】
1. 呼称のルール: 文章内で「ターゲット」や「彼/彼女」という言葉は絶対に使用せず、必ず「{target_name}さん」と呼んでください。
2. 推測語の完全排除: 「〜の傾向があります」「〜かもしれません」「〜のようです」は絶対に使用禁止。すべて「〜です」「〜します」「〜を嫌います」と断言してください。
3. 抽象的表現の禁止: 「論理的です」などの薄い言葉は禁止。「無駄な世間話を嫌い、結論を急ぎます」など、生々しい具体的な行動描写で出力してください。
4. 絵文字・#記号の禁止: 絵文字や、#、* などのリスト記号は絶対に出力しないでください。
5. 専門用語の禁止: 算命学の「西方星」「車騎星」などの用語は一切使わず、現代の日常語に翻訳してください。

【出力構成】
※見出しは必ず以下の7つを使い、文字を ** （アスタリスク2つ）で囲んで「太文字」にしてください。

**【1. 本性】表の顔と、裏に隠された本当の性格**
[算命学の主星とSJTから、基本スペックと無意識の行動原理を断言する]

**【2. 仕事・適性】職場で見せる顔と、プロフェッショナルとしての行動原理**
[プレッシャーへの耐性や、仕事において何を重視するタイプか、どうすれば評価されるかを解説]

**【3. 友人・人脈】交友関係の築き方と、心を許す相手の条件**
[広く浅くか、狭く深くか。プライベートでどういう人間を側に置きたがるかを解説]

**【4. 恋愛・執着】親密になった時だけ見せる愛情のサインと危うさ**
[算命学の西方星から、パーソナルスペースに入った瞬間にどう豹変するか、依存・回避のクセを解説]

**【5. 地雷】絶対に触れてはいけないタブーと、ストレス時の攻撃パターン**
[トラブル時の反応から、何にキレるのか、怒った時に「無視」か「攻撃」か「逃避」のどれを選ぶかを警告]

**【6. 力関係】あの人は「あなた」をどう見て、どう扱おうとしているか**
[会話の主導権やマウントの有無から、現在の二人の力関係と相手のスタンスを客観視させる]

**【7. 完全攻略】明日から使える、あの人を動かす3つの具体策**
[必ず「①」「②」「③」と番号を振り、3つ出力してください。]
[【重要ルール】「具体的なアクション：」「なぜ有効か：」「どうなるか：」といった見出しや箇条書きは絶対に書かないでください。代わりに、セリフ（または行動）、その理由、そしてどういう結果になるのか（ベネフィット）を、ひと繋がりの自然で滑らかな「1つの段落（文章）」として記述してください。]
[出力例: ① 「これ、結論から言うとね」と前置きしてから話しかけてみてください。なぜなら、{target_name}さんは合理性を重んじて時間を奪われることを極端に嫌うからです。これをすることで「この人は話が早くて有能だ」と無意識に格付けされ、あなたの提案がスムーズに通るようになります。]
"""
    return prompt

def send_line_result(line_id, sanmeigaku, scores):
    if not line_id: return
    try:
        token = st.secrets["LINE_ACCESS_TOKEN"]
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        app_url = "https://take-plan-ai-gwrexhn6yztk5swygdm4bn.streamlit.app"
        report_url = f"{app_url}?mode=portal&line_id={line_id}"
        
        text = "✨ 極秘レポートが完成しました！\n\nあなた専用の取扱説明書（完全版）は、以下の専用リンクからいつでも何度でも読み返すことができます。\n\n▼ あなたの極秘レポートを開く ▼\n" + report_url
        payload = {"to": line_id, "messages": [{"type": "text", "text": text}]}
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"LINE送信エラー: {e}")

def save_to_spreadsheet():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_url = st.secrets["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url).sheet1
        
        scores = calculate_scores()
        ud = st.session_state.user_data
        
        # 安全装置
        if not ud or "DOB" not in ud:
            st.error("セッションが切れました。最初からやり直してください。")
            return False
            
        y, m, d = map(int, ud["DOB"].split('/'))
        sanmeigaku = calculate_sanmeigaku(y, m, d, ud.get("Birth_Time", ""))
        stripe_id = st.session_state.get("stripe_id", "")
        
        row_data = [
            ud["LINE_ID"], stripe_id, ud["User_ID"], ud["DOB"], ud.get("Birth_Time", ""), ud.get("Gender", ""),
            sanmeigaku["日干支"], sanmeigaku["天中殺"], sanmeigaku["主星"], sanmeigaku["初年"],
            sanmeigaku["中年"], sanmeigaku["晩年"], sanmeigaku["時干支"], sanmeigaku["最晩年"]
        ]
        
        for i in range(1, 51): row_data.append(st.session_state.answers.get(i, ""))
        row_data.extend([scores["O"], scores["C"], scores["E"], scores["A"], scores["N"]])
        today_str = datetime.date.today().strftime("%Y/%m/%d")
        row_data.extend([today_str, "FALSE", "FALSE", 3])
        
        llm_prompt = generate_report_prompt(sanmeigaku, scores, ud)
        generated_report = ""
        
        try:
            # ▼ 確実に動く OpenAI の最高峰モデル「GPT-4o」に変更
            openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = openai_client.chat.completions.create(
                model="gpt-4o", # ← miniではなく、一番賢い gpt-4o を指定
                messages=[
                    {"role": "system", "content": "あなたは国内唯一の『戦略的ライフ・コンサルタント』です。専門用語は絶対に使わず、現代の言葉でアドバイスします。ユーザーの心に深く刺さる、エモーショナルで説得力のある文章を作成してください。"},
                    {"role": "user", "content": llm_prompt}
                ],
                temperature=0.7,
                max_tokens=4000 # 長文を出力させるために上限を開放
            )
            generated_report = response.choices[0].message.content
            st.session_state.secret_report = generated_report
            
        except Exception as e:
            error_msg = f"【OpenAI通信エラー】: {e}"
            print(error_msg)
            st.error(error_msg)
            generated_report = f"AIの生成に失敗しました。\n\n詳細なエラー理由:\n{e}"
            st.session_state.secret_report = generated_report
            
        # 1. 既存のフォーマット通りにレポートを追加
        row_data.append(generated_report)
        
        # 2. 既存のシステムを壊さないよう、右端の新しい列に情報を追記
        row_data.extend([
            ud.get("Job", "不明"),
            ud.get("Pains", "未選択"),
            ud.get("Free_Text", "なし")
        ])
        
        sheet.append_row(row_data)
        
        send_line_result(ud["LINE_ID"], sanmeigaku, scores)
        return True
        
    except Exception as e:
        st.error(f"【開発者向けエラー(System)】: {e}")
        return False
        
def get_user_status(line_id):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_url = st.secrets["spreadsheet_url"]
        premium_sheet = client.open_by_url(sheet_url).worksheet("シート1")
        all_data = premium_sheet.get_all_values()
        
        headers = all_data[0]
        exp_idx = -1
        theme_idx = -1
        for i, h in enumerate(headers):
            if h == 'EXP': exp_idx = i
            if h == '次週のテーマ': theme_idx = i
            
        for row in reversed(all_data[1:]):
            if len(row) > 0 and row[0] == line_id:
                exp = int(row[exp_idx]) if exp_idx != -1 and len(row) > exp_idx and str(row[exp_idx]).isdigit() else 0
                theme = row[theme_idx] if theme_idx != -1 and len(row) > theme_idx else "未装備（算命学の自動選択）"
                if not theme: theme = "未装備（算命学の自動選択）"
                return exp, theme
        return 0, "データが見つかりません"
    except Exception as e:
        print(f"データベース接続エラー: {e}")
        return 0, "エラー"

def start_test(line_name, line_id, dob_str, btime, gender, job_status, pain_points, free_goal):
    if not dob_str.isdigit() or len(dob_str) != 8:
        st.error("⚠️ 生年月日は8桁の半角数字で入力してください")
        return
    if not pain_points:
        st.error("⚠️ フォーカスしたいテーマを少なくとも1つ選択してください")
        return
        
    try:
        valid_date = datetime.datetime.strptime(dob_str, "%Y%m%d")
        current_year = datetime.date.today().year
        if not (1900 <= valid_date.year <= current_year):
            st.error(f"⚠️ 正しい年代の生年月日を入力してください")
            return
        formatted_dob = valid_date.strftime("%Y/%m/%d")
    except ValueError:
        st.error("⚠️ 存在しない日付です。")
        return

    st.session_state.user_data = {
        "User_ID": line_name, "LINE_ID": line_id,
        "DOB": formatted_dob, "Birth_Time": btime.strip() if btime else "", "Gender": gender,
        "Job": job_status, "Pains": ", ".join(pain_points), "Free_Text": free_goal
    }
    st.session_state.step = "test"

def handle_answer(q_id, answer_value):
    if st.session_state.current_q != q_id: return
    st.session_state.answers[q_id] = answer_value
    if st.session_state.current_q == 30:
        ans_values = list(st.session_state.answers.values())
        variance = statistics.variance(ans_values) if len(ans_values) > 1 else 0
        if variance < 0.8: st.session_state.max_q = 50
        else:
            finish_test()
            return
    if st.session_state.current_q >= st.session_state.max_q: finish_test()
    else: st.session_state.current_q += 1

def go_back():
    if st.session_state.current_q > 1: st.session_state.current_q -= 1

def finish_test():
    st.session_state.step = "processing"

# ==========================================
# セッションステートの初期化
# ==========================================
if "step" not in st.session_state:
    st.session_state.step = "user_info"
if "current_q" not in st.session_state:
    st.session_state.current_q = 1
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "max_q" not in st.session_state:
    st.session_state.max_q = 30
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "line_id" not in st.session_state:
    st.session_state.line_id = None
if "line_name" not in st.session_state:
    st.session_state.line_name = None
if "stripe_id" not in st.session_state:
    st.session_state.stripe_id = ""
if "secret_report" not in st.session_state:
    st.session_state.secret_report = ""

# ==========================================
# グローバルパラメータ処理
# ==========================================
def get_params_robust():
    params = {}
    try:
        if hasattr(st.query_params, "to_dict"): params = st.query_params.to_dict()
        else: params = dict(st.query_params)
    except:
        pass
    return params

raw_params = get_params_robust()
p_line_id = raw_params.get("line_id", [""])[0] if isinstance(raw_params.get("line_id", ""), list) else raw_params.get("line_id", "")
p_line_name = raw_params.get("line_name", [""])[0] if isinstance(raw_params.get("line_name", ""), list) else raw_params.get("line_name", "")
p_stripe_id = raw_params.get("stripe_id", [""])[0] if isinstance(raw_params.get("stripe_id", ""), list) else raw_params.get("stripe_id", "")
p_mode = raw_params.get("mode", [""])[0] if isinstance(raw_params.get("mode", ""), list) else raw_params.get("mode", "")

if p_line_id and p_line_id != "不明":
    st.session_state.line_id = p_line_id
    st.session_state.stripe_id = p_stripe_id
    if p_line_name and p_line_name != "ゲスト":
        st.session_state.line_name = urllib.parse.unquote(p_line_name)
    elif not st.session_state.line_name:
        st.session_state.line_name = "ゲスト"
elif not st.session_state.line_id:
    st.warning("⚠️ このページは専用リンクからアクセスしてください。")
    st.info("LINE公式アカウントのメニューから再度アクセスをお願いします。")
    st.stop()

# ==========================================
# ★大統合ポータルモードの描画
# ==========================================
if p_mode in ["portal", "report"] and st.session_state.line_id:
    st.markdown("<h2 style='text-align: center; color: #b8860b; margin-bottom: 20px;'>裏ステータス完全攻略ポータル</h2>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["マイページ", "波乗りダッシュボード", "極秘レポート", "対人レーダー"])
    
    with tab1:
        with st.spinner("ステータスを同期中..."):
            exp, theme = get_user_status(st.session_state.line_id)
            level = math.floor(exp / 50) + 1
            next_exp = level * 50
            progress = (exp % 50) / 50.0

        st.markdown(f"""
        <div style='background-color: #FAFAFA; padding: 20px; border-radius: 10px; border: 2px solid #b8860b; margin-bottom: 20px;'>
            <h3 style='color: #b8860b; text-align: center; margin-top: 0;'>YOUR STATUS</h3>
            <h1 style='color: #D32F2F; text-align: center; font-size: 3rem; margin: 10px 0;'>Lv. {level}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.progress(progress, text=f"次のレベルまで あと {next_exp - exp} EXP")
        
        col1, col2 = st.columns(2)
        col1.metric(label="獲得累計 EXP", value=f"{exp} ✨")
        col2.metric(label="現在装備中のスキル", value="装備中", delta=theme, delta_color="normal")
        st.info("💡 毎朝LINEに届くクエストを完了させるとEXPが貯まります。継続は最大の魔法です！")

    with tab2:
        st.subheader("📅 運命の波乗りダッシュボード")
        with st.spinner("運命の波を計算中..."):
            try:
                creds_dict = st.secrets["gcp_service_account"]
                scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                client = gspread.authorize(creds)
                sheet_url = st.secrets["spreadsheet_url"]
                sheet = client.open_by_url(sheet_url).sheet1
                all_data = sheet.get_all_values()
                
                user_nikkanshi = None
                for row in reversed(all_data):
                    if len(row) > 6 and row[0] == st.session_state.line_id:
                        user_nikkanshi = row[6]
                        break
                
                if not user_nikkanshi:
                    st.warning("⚠️ 運勢を計算するためのデータが見つかりません。先に診断を完了してください。")
                else:
                    today = datetime.date.today()
                    current_year = today.year
                    
                    t_day, t_month, t_year = st.tabs(["🌊 今日の波と今月", "🗓 月間グラフ (15ヶ月)", "🗻 年間グラフ (8年)"])
                    
                    with t_day:
                        st.markdown("### 🗓 今日の運勢")
                        today_res = calculate_period_score(user_nikkanshi, today, period_type="day")
                        
                        st.markdown(f"<p style='text-align: center; font-size: 1.2rem; font-weight: bold;'>{today.strftime('%Y年%m月%d日')}</p>", unsafe_allow_html=True)
                        st.markdown(f"<h1 style='text-align: center; font-size: 4.5rem; margin: 0;'>{today_res['symbol']}</h1>", unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align: center; font-size: 1.3rem; font-weight: bold; margin-top: -10px;'>（{today_res['title']}）</p>", unsafe_allow_html=True)
                        st.markdown(f"<h2 style='text-align: center; color: #b8860b;'>スコア: {today_res['score']} / 10</h2>", unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div style='background-color: #FAFAFA; border-left: 5px solid #b8860b; padding: 15px; margin: 20px 0; border-radius: 4px;'>
                            <p style='font-size: 1.05rem; color: #333; margin-bottom: 15px;'>{today_res['desc']}</p>
                            <p style='font-weight: bold; color: #b8860b; margin-bottom: 5px;'>○ポイント</p>
                            <ul style='color: #444; line-height: 1.8;'>
                                <li>{today_res['points'][0]}</li>
                                <li>{today_res['points'][1]}</li>
                                <li>{today_res['points'][2]}</li>
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        with st.spinner("専属コンサルタントが本日の戦略を執筆中..."):
                            @st.cache_data(ttl=3600)
                            def get_cached_daily_advice(date_str, _res):
                                return generate_daily_advice(_res)
                            daily_advice = get_cached_daily_advice(today.strftime("%Y%m%d"), today_res)
                            
                            st.markdown("""
                            <style>
                                .advice-box { background: linear-gradient(180deg, #FFFFFF 0%, #F5F5F5 100%); border: 2px solid #b8860b; border-radius: 12px; padding: 25px; margin-top: 10px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
                                .advice-box h2 { color: #b8860b !important; font-size: 1.4rem !important; border-bottom: 1px solid #E0E0E0; padding-bottom: 10px; margin-bottom: 20px; }
                                .advice-box h3 { color: #333333 !important; font-size: 1.1rem !important; margin-top: 20px !important; margin-bottom: 10px !important; border-left: 4px solid #b8860b; padding-left: 10px;}
                                .advice-box p, .advice-box li { font-size: 1rem; line-height: 1.7; color: #444444; }
                            </style>
                            """, unsafe_allow_html=True)
                            st.markdown(f"<div class='advice-box'>{daily_advice}</div>", unsafe_allow_html=True)

                        st.markdown(f"### 🌊 {today.month}月の運命の波")
                        _, last_day = calendar.monthrange(today.year, today.month)
                        start_date = datetime.date(today.year, today.month, 1)
                        dates = [start_date + datetime.timedelta(days=i) for i in range(last_day)]
                        
                        chart_data = []
                        for d in dates:
                            res = calculate_period_score(user_nikkanshi, d, period_type="day")
                            chart_data.append({"日付": d.strftime("%m/%d"), "運気スコア": res["score"], "シンボル": res["symbol"], "フル日付": d, "精神理由": res["mind_reason"]})
                        
                        df = pd.DataFrame(chart_data)
                        base = alt.Chart(df).encode(x=alt.X('日付:O', axis=alt.Axis(labelAngle=-45, title=None, labelColor='black', tickColor='black', domainColor='black')))
                        line = base.mark_line(color='black', strokeWidth=3).encode(y=alt.Y('運気スコア:Q', scale=alt.Scale(domain=[0, 11]), axis=alt.Axis(title='スコア', labelColor='black', titleColor='black', tickColor='black', domainColor='black')))
                        symbols = base.mark_text(size=18, dy=0).encode(y=alt.Y('運気スコア:Q'), text='シンボル:N')
                        st.altair_chart((line + symbols).properties(height=300, background='#FFFFFF'), use_container_width=True)
                        
                        st.markdown("""
                        <div style='font-size: 0.85rem; color: #555555; background-color: #FAFAFA; padding: 15px; border-radius: 8px; border-left: 4px solid #b8860b; margin-bottom: 20px;'>
                        <b>※【記号の意味】</b> 🌈(10):超幸運 / ⭐️(9):最高 / 🔴(8):迷わず動く / ⚪️(7):決断 / 🟡(6):基礎固め / 🟢(5):味方増 / 🔵(4):整理 / 🟪(3):無理しない / ⬜️(2):手放し / ⚫️(1):休む
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown(f"### 🗓 {today.month}月の日別カレンダー一覧")
                        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
                        for data in chart_data:
                            d_obj = data["フル日付"]
                            stars = get_rule_based_stars(data["運気スコア"], data["精神理由"])
                            st.markdown(f"**{d_obj.month}月{d_obj.day}日（{weekdays[d_obj.weekday()]}） {data['シンボル']} (スコア: {data['運気スコア']})**")
                            st.markdown(f"<p style='font-size: 0.95rem; margin-top: 0px;'>総合: {stars['総合運']} | 人間関係: {stars['人間関係']} | 仕事: {stars['仕事運']} | 恋愛: {stars['恋愛結婚']} | 金運: {stars['金運']} | 健康: {stars['健康運']} | 家族: {stars['家族親子']}</p><hr style='margin: 10px 0;'>", unsafe_allow_html=True)

                    with t_month:
                        st.markdown(f"### 🗓 月間・運命の波（{current_year}年の計画）")
                        st.info("前年終盤からの流れと、今年の着地点を確認して長期計画に活用してください。")
                        
                        months_data = []
                        for m in range(10, 13):
                            m_date = datetime.date(current_year - 1, m, 15)
                            res = calculate_period_score(user_nikkanshi, m_date, period_type="month")
                            months_data.append({"年月": m_date.strftime("%Y年%m月"), "スコア": res["score"], "シンボル": res["symbol"], "タイトル": res["title"], "環境理由": res["env_reason"], "精神理由": res["mind_reason"]})
                        for m in range(1, 13):
                            m_date = datetime.date(current_year, m, 15)
                            res = calculate_period_score(user_nikkanshi, m_date, period_type="month")
                            months_data.append({"年月": m_date.strftime("%Y年%m月"), "スコア": res["score"], "シンボル": res["symbol"], "タイトル": res["title"], "環境理由": res["env_reason"], "精神理由": res["mind_reason"]})
                            
                        df_m = pd.DataFrame(months_data)
                        base_m = alt.Chart(df_m).encode(x=alt.X('年月:O', axis=alt.Axis(labelAngle=-45, title=None, labelColor='black', tickColor='black', domainColor='black')))
                        line_m = base_m.mark_line(color='#06C755', strokeWidth=3).encode(y=alt.Y('スコア:Q', scale=alt.Scale(domain=[0, 11]), axis=alt.Axis(title='月間スコア', labelColor='black', titleColor='black', tickColor='black', domainColor='black')))
                        symbols_m = base_m.mark_text(size=18, dy=0).encode(y=alt.Y('スコア:Q'), text='シンボル:N')
                        st.altair_chart((line_m + symbols_m).properties(height=300, background='#FFFFFF'), use_container_width=True)
                        
                        st.markdown("### 📝 各月の総合解説と7つの指針")
                        
                        with st.spinner("AIが各月の固有テーマを分析中..."):
                            @st.cache_data(ttl=86400)
                            def get_cached_monthly_advices(year_str, _months_data):
                                prompt = "あなたは日本一の戦略的ライフ・コンサルタントです。\n"
                                prompt += "以下の15ヶ月分のデータをもとに、各月の「総合解説（2〜3文）」を作成してください。\n"
                                prompt += "【重要】同じスコアの月でも、環境と精神のテーマに合わせて全く違う切り口で具体的な解説を書いてください。専門用語は使わず現代語に翻訳してください。\n\n"
                                prompt += "# データ\n"
                                for d in _months_data:
                                    prompt += f"- {d['年月']}: スコア{d['スコア']}, 環境({d['環境理由']}), 精神({d['精神理由']})\n"
                                prompt += "\n# 出力形式（以下のフォーマットを厳守）\n"
                                for d in _months_data:
                                    prompt += f"■{d['年月']}\n[ここに独自の解説]\n"
                                    
                                try:
                                    openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                                    response = openai_client.chat.completions.create(
                                        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], temperature=0.7
                                    )
                                    return response.choices[0].message.content
                                except:
                                    return ""
                            
                            raw_ai_text = get_cached_monthly_advices(str(current_year), months_data)
                            ai_dict = {}
                            if raw_ai_text:
                                parts = raw_ai_text.split("■")
                                for part in parts:
                                    if "\n" in part:
                                        lines = part.strip().split("\n", 1)
                                        ym = lines[0].strip()
                                        desc = lines[1].strip() if len(lines) > 1 else ""
                                        ai_dict[ym] = desc
                        
                        for data in months_data:
                            stars = get_rule_based_stars(data["スコア"], data["精神理由"])
                            ai_desc = ai_dict.get(data['年月'], f"スコア{data['スコア']}の月です。自身のテーマに沿って着実に行動しましょう。")
                            
                            st.markdown(f"#### {data['年月']} {data['シンボル']} {data['タイトル']} (スコア: {data['スコア']})")
                            st.markdown(f"<p style='color:#333; line-height:1.6; margin-bottom:5px;'>{ai_desc}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-size: 0.95rem; margin-top: 0px;'>総合: {stars['総合運']} | 人間関係: {stars['人間関係']} | 仕事: {stars['仕事運']} | 恋愛: {stars['恋愛結婚']} | 金運: {stars['金運']} | 健康: {stars['健康運']} | 家族: {stars['家族親子']}</p><hr style='margin: 15px 0;'>", unsafe_allow_html=True)

                    with t_year:
                        st.markdown("### 🗻 年間・運命の波（8年推移）")
                        years_data = []
                        for i in range(-2, 6):
                            y_date = datetime.date(current_year + i, 6, 1)
                            res = calculate_period_score(user_nikkanshi, y_date, period_type="year")
                            years_data.append({"年": f"{y_date.year}年", "スコア": res["score"], "シンボル": res["symbol"], "res_obj": res})
                            if i == 0: this_year_res = res
                            
                        df_y = pd.DataFrame(years_data)
                        base_y = alt.Chart(df_y).encode(x=alt.X('年:O', axis=alt.Axis(labelAngle=0, title=None, labelColor='black', tickColor='black', domainColor='black')))
                        line_y = base_y.mark_line(color='#D32F2F', strokeWidth=4).encode(y=alt.Y('スコア:Q', scale=alt.Scale(domain=[0, 11]), axis=alt.Axis(title='年間スコア', labelColor='black', titleColor='black', tickColor='black', domainColor='black')))
                        symbols_y = base_y.mark_text(size=24, dy=-5).encode(y=alt.Y('スコア:Q'), text='シンボル:N')
                        st.altair_chart((line_y + symbols_y).properties(height=300, background='#FFFFFF'), use_container_width=True)
                        
                        st.markdown(f"### 🎯 {current_year}年の年間テーマと詳細戦略")
                        with st.spinner(f"AIが{current_year}年の年間戦略を執筆中..."):
                            @st.cache_data(ttl=86400)
                            def get_cached_yearly_advice(year_str, _res):
                                prompt = f"""
                                あなたは日本一の戦略的ライフ・コンサルタントです。以下のデータをもとに、【今年のユーザーへの年間アドバイス】を作成してください。
                                [今年のスコア: {_res['score']}点, シンボル: {_res['symbol']}, 環境: {_res['env_reason']}, 精神: {_res['mind_reason']}]

                                # 【絶対遵守の出力ルール】
                                1. 算命学・四柱推命の専門用語は【絶対に】出力せず、現代の言葉に翻訳すること。
                                2. 1年間の長期的な視点で、ワクワクする力強いトーンで書くこと。
                                3. 【重要】星評価（★☆☆など）は絶対に出力しないでください。文章のみで解説してください。
                                4. 各項目に「具体的なアクション」を必ず入れること。
                                5. 【重要】同じスコアや記号であっても、背景にある「環境」と「精神」のテーマ（例：今年は学びの年、今年は行動の年など）を反映し、その年ならではの独自の解説にしてください。

                                # 出力構成
                                ## 今年の運命の波（総合解説）
                                今年のスコアとシンボルの意味を解説するとともに、「あなたにとって今年全体がどのような意味を持つ1年なのか（例：成長の年、手放しの年、飛躍の年など）」を追加して総括してください。

                                ## 7つの指針と詳細解説（※星評価は書かない）
                                ### 1. 総合運
                                [解説]
                                ### 2. 人間関係運
                                [解説]
                                ### 3. 仕事運
                                [解説]
                                ### 4. 恋愛＆結婚運
                                [解説]
                                ### 5. 金運（契約・買い物）
                                [解説]
                                ### 6. 健康運
                                [解説]
                                ### 7. 家族・親子運
                                [解説]
                                """
                                try:
                                    openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                                    response = openai_client.chat.completions.create(
                                        model="gpt-4o-mini", messages=[{"role": "system", "content": "あなたは国内唯一の『戦略的ライフ・コンサルタント』です。専門用語は絶対に使わず、現代の言葉でアドバイスします。"}, {"role": "user", "content": prompt}], temperature=0.7
                                    )
                                    return response.choices[0].message.content
                                except:
                                    return "エラーが発生しました。"

                            yearly_advice = get_cached_yearly_advice(str(current_year), this_year_res)
                            st.markdown(f"<div class='advice-box'>{yearly_advice}</div>", unsafe_allow_html=True)
                            
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    # ==========================================
    # 【タブ3】極秘レポート完全版
    # ==========================================
    with tab3:
        st.subheader("📜 極秘レポート完全版")
        with st.spinner("データベースからレポートを検索しています..."):
            try:
                creds_dict = st.secrets["gcp_service_account"]
                scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                from oauth2client.service_account import ServiceAccountCredentials
                import gspread
                import re # 正規表現モジュールを追加
                
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                client = gspread.authorize(creds)
                sheet_url = st.secrets["spreadsheet_url"]
                sheet = client.open_by_url(sheet_url).sheet1
                all_data = sheet.get_all_values()
                
                report_text = None
                for row in reversed(all_data):
                    if len(row) > 0 and row[0] == st.session_state.line_id:
                        if len(row) > 73 and row[73].strip() != "":
                            report_text = row[73]
                        break
                
                if report_text:
                    # ====================================================
                    # 🚀 Pythonの力で「超UDデザイン」に強制変換
                    # ====================================================
                    
                    # 過去のレポートに残っているテーブル(表)のゴミを消去
                    report_text = report_text.replace("| | | |", "")
                    report_text = report_text.replace("|---|---|---|", "")
                    report_text = report_text.replace("|", "")
                    
                    # 🌟 新規追加：15の星の「タグデザイン化」ハック
                    # 「あなたの中に眠る15の星」から「生まれ持った宿命」までの文字を切り出す
                    star_match = re.search(r'(あなたの中に眠る15の星.*?\n)(.*?)(生まれ持った宿命)', report_text, re.DOTALL)
                    if star_match:
                        heading_part = star_match.group(1)
                        content_part = star_match.group(2)
                        
                        # 不要な記号や改行をスペースに変換
                        clean_text = re.sub(r'[・\-\n]', ' ', content_part)
                        
                        # 「星」という文字で文章をハサミで切り、リスト化する（最後に「星」を付け直す）
                        stars = [s.strip() + "星" for s in clean_text.split("星") if s.strip()]
                        
                        # フレックスボックスを使ったタグデザインのHTMLを自動生成
                        tags_html = "<div style='display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0 40px 0;'>"
                        for star in stars:
                            if len(star) < 40: # 異常な長文の巻き込みを防ぐ安全装置
                                tags_html += f"<span style='background-color: #FFFFFF; color: #333333; padding: 8px 18px; border-radius: 25px; font-size: 0.95rem; font-weight: 800; border: 2px solid #E0E0E0; box-shadow: 0 2px 5px rgba(0,0,0,0.05);'>{star}</span>"
                        tags_html += "</div>"
                        
                        # レポート本文の該当箇所を、生成したタグデザインのHTMLに差し替え
                        report_text = report_text[:star_match.start(2)] + tags_html + report_text[star_match.end(2):]

                    # 宿命と現実の「確実な改行」
                    report_text = report_text.replace("宿命：", "<span style='font-weight:900; color:#111; font-size:1.1rem;'>宿命：</span>")
                    report_text = report_text.replace("現実：", "<br><br><span style='font-weight:900; color:#111; font-size:1.1rem;'>現実：</span><br><br>")
                    
                    # 大見出し（##）の装飾
                    headings = [
                        "宿命と現実", "あなたの中に眠る15の星", "生まれ持った宿命と現在の性格のギャップ", 
                        "カテゴリ別・究極の自己分析", "あなたの5大欲求パラメーター", "結びの言葉"
                    ]
                    for h in headings:
                        report_text = report_text.replace(f"## {h}", f"<h2 style='color:#111; font-size:1.5rem; border-bottom:3px solid #E0E0E0; padding-bottom:10px; margin-top:50px; margin-bottom:20px; font-weight:900;'>{h}</h2>")
                    
                    # 小見出しの装飾
                    report_text = report_text.replace("### ■ 本来の宿命（あなたが持って生まれた基礎設計）", "<h3 style='color:#333; font-size:1.2rem; border-left:5px solid #777; padding-left:10px; margin-top:30px; font-weight:800;'>■ 本来の宿命（あなたが持って生まれた基礎設計）</h3>")
                    report_text = report_text.replace("### ■ 現在の性格（今のあなたが作っている外観）", "<h3 style='color:#333; font-size:1.2rem; border-left:5px solid #777; padding-left:10px; margin-top:30px; font-weight:800;'>■ 現在の性格（今のあなたが作っている外観）</h3>")
                    
                    # カテゴリ別の「カラーブロック化」（絵文字なし）
                    report_text = report_text.replace("### ■ 仕事と才能", "<div style='background-color:#FFF3E0; padding:12px 15px; border-left:6px solid #FF9800; border-radius:4px; margin-top:35px; margin-bottom:15px;'><h3 style='color:#E65100; margin:0; font-size:1.25rem; font-weight:800;'>仕事と才能</h3></div>")
                    report_text = report_text.replace("### ■ 恋愛と人間関係", "<div style='background-color:#FCE4EC; padding:12px 15px; border-left:6px solid #E91E63; border-radius:4px; margin-top:35px; margin-bottom:15px;'><h3 style='color:#C2185B; margin:0; font-size:1.25rem; font-weight:800;'>恋愛と人間関係</h3></div>")
                    report_text = report_text.replace("### ■ お金と豊かさ", "<div style='background-color:#E8F5E9; padding:12px 15px; border-left:6px solid #4CAF50; border-radius:4px; margin-top:35px; margin-bottom:15px;'><h3 style='color:#2E7D32; margin:0; font-size:1.25rem; font-weight:800;'>お金と豊かさ</h3></div>")
                    report_text = report_text.replace("### ■ 健康とメンタル", "<div style='background-color:#E3F2FD; padding:12px 15px; border-left:6px solid #2196F3; border-radius:4px; margin-top:35px; margin-bottom:15px;'><h3 style='color:#1565C0; margin:0; font-size:1.25rem; font-weight:800;'>健康とメンタル</h3></div>")

                    # テキストの改行(\n)をHTMLの改行(<br>)に変換
                    report_text = report_text.replace("\n", "<br>")

                    # CSSベースの枠組み
                    st.markdown("""
                    <style>
                        .ud-report-box { 
                            background-color: #FAFAFA;
                            border: 1px solid #E0E0E0; 
                            border-radius: 8px; 
                            padding: 30px 25px; 
                            margin-top: 20px; 
                            margin-bottom: 40px; 
                            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                            color: #222222;
                            font-size: 1.05rem;
                            line-height: 1.9;
                            letter-spacing: 0.05em;
                        }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='ud-report-box'>{report_text}</div>", unsafe_allow_html=True)
                    
                else:
                    st.warning("レポートが見つかりませんでした。まだ診断が完了していないか、データが存在しません。")
            except Exception as e:
                st.error(f"データベース通信エラー: {e}")

    # ==========================================
    # 【タブ4】対人関係レーダー（SJT12問 ＋ AIプロファイリング）
    # ==========================================
    with tab4:
        st.subheader("対人関係レーダー")
        
        st.markdown("""
        <style>
            div[data-baseweb="select"] > div, 
            div[data-baseweb="input"] > div, 
            div[data-baseweb="textarea"] > div { background-color: #FAFAFA !important; border: 1px solid #CCCCCC !important; }
            div[data-baseweb="select"] span { color: #000000 !important; }
            ul[role="listbox"], ul[data-baseweb="menu"], li[role="option"] { background-color: #FAFAFA !important; color: #000000 !important; }
            input, textarea { color: #000000 !important; background-color: transparent !important; }
            div[data-testid="stForm"] button[kind="primary"] { background-color: #4A90E2 !important; border: none !important; }
            div[data-testid="stForm"] button[kind="primary"] p, div[data-testid="stForm"] button[kind="primary"] span { color: #FFFFFF !important; font-weight: 900 !important; font-size: 1.1rem !important; }
        </style>
        """, unsafe_allow_html=True)

        if "radar_answers" not in st.session_state: st.session_state.radar_answers = {}
        if "radar_result" not in st.session_state: st.session_state.radar_result = None
            
        with st.spinner("システム接続中..."):
            radar_limit = check_radar_limit(st.session_state.line_id)

        if st.session_state.radar_result:
            st.success("解析完了。取扱説明書が作成されました。")
            st.warning("このレポートは履歴に保存されません。画面を閉じると消えるため、スクリーンショット等で保存してください。")
            
            st.markdown("""
            <style>
                .radar-box { background: linear-gradient(180deg, #FFFFFF 0%, #F0F8FF 100%); border: 2px solid #0056b3; border-radius: 12px; padding: 25px; margin-top: 10px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
                .radar-box h2 { color: #0056b3 !important; font-size: 1.5rem !important; border-bottom: 2px solid #D0E2F3; padding-bottom: 10px; margin-bottom: 20px; text-align: center;}
                .radar-box h3 { color: #111111 !important; font-size: 1.2rem !important; margin-top: 25px !important; margin-bottom: 10px !important; border-left: 5px solid #0056b3; padding-left: 10px;}
                .radar-box p, .radar-box li { font-size: 1.05rem; line-height: 1.7; color: #333333; }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(f"<div class='radar-box'><h2>{st.session_state.get('target_name', 'ターゲット')} の完全攻略レポート</h2>\n\n{st.session_state.radar_result}</div>", unsafe_allow_html=True)
            
            if st.button("▶︎ 別の相手を検索する（タップするとレポートが消えます）"):
                st.session_state.radar_result = None
                st.session_state.radar_answers = {}
                st.rerun()

        else:
            if radar_limit <= 0:
                st.error("今月のターゲット検索回数（3回）を使い切りました。来月までお待ちください。")
            else:
                st.info(f"今月の検索可能回数：あと {radar_limit} 回")
                st.markdown("相手の生年月日と、あなたの観察に基づく行動データから、AIが相手の「取扱説明書」を作成します。**※相手には一切通知されません。**")
                
                with st.form("radar_form"):
                    st.markdown("#### Step 1: ターゲットの基本情報")
                    with st.expander("💡 相手の生年月日を自然に聞き出すには？"):
                        st.markdown("・「最近、職場で動物占いが流行ってて、〇〇さんは何ですか？」と聞き、一緒に調べる流れで入力してもらう。\n・「運転免許証の写真って盛れないよね？見せて」と言ってさりげなく確認する。\n・「自分と同じ誕生日の芸能人を調べるサイトが面白い」と話題を振る。")
                    
                    col1, col2 = st.columns(2)
                    with col1: target_name = st.text_input("相手の名前（仮名・ニックネームOK）", placeholder="例：A部長")
                    with col2: target_dob = st.text_input("相手の生年月日（半角数字8桁・必須）", max_chars=8, placeholder="例：19900101")
                        
                    target_relation = st.selectbox("あなたと相手の現在の関係性は？", ["初対面・数回しか会っていない", "職場の同僚・上司・部下", "友人・知人", "恋人・配偶者・非常に親しい"])
                    
                    st.markdown("---")
                    st.markdown("#### Step 2: 相手の行動プロファイリング（12問）")
                    st.write("相手の普段の行動を思い出して、最も近いものを選択してください。分からない場合は無理せず「わからない」を選んでください。")
                    
                    for q in RADAR_QUESTIONS:
                        st.markdown(f"<p style='font-weight:bold; margin-bottom: 5px; margin-top: 15px;'>{q['text']}</p>", unsafe_allow_html=True)
                        ans_idx = st.radio("選択", range(len(q["options"])), format_func=lambda i: q["options"][i], key=f"radar_q_{q['id']}", label_visibility="collapsed", index=3)
                        st.session_state.radar_answers[q['id']] = ans_idx

                    st.markdown("---")
                    st.markdown("#### Step 3: エピソードの自由記述（任意・AI解析用）")
                    with st.expander("💡 何を書けばいい？（AIがより深く分析するためのヒント）"):
                        st.markdown("・最近あったイラッとしたこと、または嬉しかったこと\n・相手のLINEのクセ（絵文字がない、返信が遅い等）\n・口癖や、第三者（店員など）への態度\n・「ここを直してほしい」と思っている不満")
                        
                    free_text = st.text_area("エピソードや気になっている行動（箇条書きOK）", height=150, placeholder="例：仕事は完璧でミスを許さないタイプ。でも昨日、パソコンがフリーズした時に舌打ちして不機嫌になり周りが気を使いました。LINEは要件だけで絵文字は一切ありません。私には少し偉そうにアドバイスしてきます。")
                    
                    st.markdown("---")
                    submitted = st.form_submit_button("検索実行（残回数を1消費します）", type="primary")

                if submitted:
                    if not target_name: st.error("相手の名前を入力してください。")
                    elif not target_dob or len(target_dob) != 8 or not target_dob.isdigit(): st.error("正しい生年月日（半角数字8桁）を入力してください。")
                    else:
                        target_san = calculate_target_sanmeigaku(target_dob)
                        if not target_san: st.error("存在しない日付、または生年月日の計算に失敗しました。")
                        else:
                            with st.spinner("AIが相手の深層心理と攻略法を解析中...（約20秒）"):
                                success = consume_radar_limit(st.session_state.line_id)
                                if not success:
                                    st.error("データベースの更新に失敗しました。")
                                else:
                                    try:
                                        creds_dict = st.secrets["gcp_service_account"]
                                        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                                        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                                        client = gspread.authorize(creds)
                                        sheet = client.open_by_url(st.secrets["spreadsheet_url"]).sheet1
                                        all_data = sheet.get_all_values()
                                        
                                        user_main_star = "不明"
                                        for row in reversed(all_data):
                                            if len(row) > 8 and row[0] == st.session_state.line_id:
                                                user_main_star = row[8]
                                                break
                                                
                                        prompt = generate_radar_prompt(
                                            target_name, target_relation, 
                                            st.session_state.radar_answers, 
                                            free_text, target_san, user_main_star
                                        )
                                        
                                        openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                                        response = openai_client.chat.completions.create(
                                            model="gpt-4o-mini", 
                                            messages=[
                                                {"role": "system", "content": "あなたは国内唯一の『戦略的ライフ・コンサルタント』です。専門用語は絶対に使わず、現代の言葉でアドバイスします。"},
                                                {"role": "user", "content": prompt}
                                            ],
                                            temperature=0.7
                                        )
                                        st.session_state.target_name = target_name
                                        st.session_state.radar_result = response.choices[0].message.content
                                        st.rerun() 
                                        
                                    except Exception as e:
                                        st.error(f"AI解析中にエラーが発生しました: {e}")

    st.stop()

# ==========================================
# 診断テストの描画 (初回のテストモード)
# ==========================================
if st.session_state.step == "user_info":
    st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h2 style='font-weight: bold;'>プレミアム裏ステータス診断へ</h2></div>", unsafe_allow_html=True)
    st.markdown(f"独自の宿命解析アルゴリズムと最新のAIを掛け合わせ、**{st.session_state.line_name}さん**の深層心理と本来のポテンシャルを完全解析します。まずはプロファイリングに必要な基本情報をご入力ください。")
    
    with st.form("info_form"):
        st.markdown("""
        <style>
            div[data-baseweb="input"] > div, 
            div[data-baseweb="textarea"] > div, 
            div[data-baseweb="select"] > div { background-color: #FAFAFA !important; border: 1px solid #CCCCCC !important; }
            input, textarea { color: #000000 !important; background-color: transparent !important; }
            /* ▼ 追加：プレースホルダー（薄い文字）の色を確実にグレーにする */
            input::placeholder, textarea::placeholder { color: #999999 !important; opacity: 1 !important; }
            div[data-baseweb="select"] span { color: #000000 !important; }
            ul[role="listbox"], ul[data-baseweb="menu"], li[role="option"] { background-color: #FAFAFA !important; color: #000000 !important; }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("<p style='font-weight: 900; margin-bottom: 0;'>生年月日（半角数字8桁・必須）</p>", unsafe_allow_html=True)
        # ▼ 修正：value="" を追加して空欄を明示
        dob_input = st.text_input("生年月日", value="", max_chars=8, placeholder="19961229", label_visibility="collapsed")
        
        st.markdown("<p style='font-weight: 900; margin-top: 15px; margin-bottom: 0;'>出生時間（任意・不明なら空欄のまま）</p>", unsafe_allow_html=True)
        st.caption("※出生時間が不明な場合、最晩年の運勢に関する一部の解析は正確を期すために秘匿されます。")
        # ▼ 修正：value="" を追加して空欄を明示
        btime = st.text_input("出生時間", value="", placeholder="1700", label_visibility="collapsed")
        
        st.markdown("<p style='font-weight: 900; margin-top: 15px;'>性別</p>", unsafe_allow_html=True)
        gender = st.radio("性別", ["男性", "女性", "その他", "回答しない"], horizontal=True, label_visibility="collapsed")
        
        st.markdown("---")
        st.markdown("#### 現在の状況と、解決したい課題について")
        
        job_status = st.selectbox(
            "現在の職業・お立場（必須）",
            ["会社員（一般）", "会社員（管理職・マネージャー）", "経営者・役員", "フリーランス・個人事業主", "公務員", "学生", "主婦・主夫", "その他"]
        )
        
        pain_points = st.multiselect(
            "現在、最も解決したい・フォーカスしたいテーマはどれですか？（複数選択可）",
            ["仕事での評価・キャリアアップ", "転職・独立・起業", "職場の人間関係", "恋愛関係・パートナー探し", "夫婦・家族関係", "お金・収入の不安", "自分自身の性格・メンタルの悩み", "人生の目標ややりがい探し"],
            placeholder="ここをタップして選択（複数可）"
        )
        
        # ▼ 修正：例文が確実に見えるように改行コード（\n）を使用して配置
        free_placeholder = "【箇条書き・文章のどちらでも可】\n（悩みの例）今の仕事が向いているかわからない。恋人といつも同じ理由で喧嘩してしまう。\n（理想の例）独立して自分のビジネスを持ちたい。心から安心できるパートナーに出会いたい。"
        
        free_goal = st.text_area(
            "現状の具体的な悩み、または理想の姿があれば教えてください（任意）",
            value="",
            placeholder=free_placeholder,
            height=120
        )
        
        submitted = st.form_submit_button("適性テスト（全50問）を開始する", type="primary")
        
        if submitted:
            start_test(st.session_state.line_name, st.session_state.line_id, dob_input, btime, gender, job_status, pain_points, free_goal)
            if st.session_state.step == "test":
                st.rerun()

elif st.session_state.step == "test":
    current_q_num = st.session_state.current_q
    max_q_num = st.session_state.max_q
    
    progress_val = current_q_num / max_q_num
    st.progress(progress_val)
    st.caption(f"現在 {current_q_num} 問目 / (最大 {max_q_num} 問)")
    
    if current_q_num > 1:
        st.button("◀ 前の質問に戻る", on_click=go_back, key=f"btn_back_{current_q_num}", type="secondary")
    
    question_data = QUESTIONS[current_q_num - 1]
    st.markdown(f"<div class='question-title'>{question_data['text']}</div>", unsafe_allow_html=True)
    st.write("---")
    
    st.button("全く違う", on_click=handle_answer, args=(current_q_num, 1), key=f"btn_1_{current_q_num}", type="secondary")
    st.button("やや違う", on_click=handle_answer, args=(current_q_num, 2), key=f"btn_2_{current_q_num}", type="secondary")
    st.button("どちらでもない", on_click=handle_answer, args=(current_q_num, 3), key=f"btn_3_{current_q_num}", type="secondary")
    st.button("ややそう思う", on_click=handle_answer, args=(current_q_num, 4), key=f"btn_4_{current_q_num}", type="secondary")
    st.button("強くそう思う", on_click=handle_answer, args=(current_q_num, 5), key=f"btn_5_{current_q_num}", type="secondary")

elif st.session_state.step == "processing":
    with st.spinner("AIがあなた専用の極秘レポートを執筆しています...（約10〜20秒）"):
        success = save_to_spreadsheet()
    if success:
        st.session_state.step = "done"
        st.rerun()

elif st.session_state.step == "done":
    st.success("解析と極秘レポートの作成が完了しました！")
    
    if "secret_report" in st.session_state and st.session_state.secret_report:
        report_text = st.session_state.secret_report
        
        # UDデザインと黒波線のCSSを注入
        st.markdown("""
        <style>
            .ud-report-box { 
                background-color: #FAFAFA; /* 目に優しいオフホワイト */
                border: 1px solid #E0E0E0; 
                border-radius: 8px; 
                padding: 40px 30px; 
                margin-top: 20px; 
                margin-bottom: 40px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                color: #222222; /* コントラストの高い黒 */
                font-size: 1.05rem;
                line-height: 1.9;
                letter-spacing: 0.05em;
            }
            .ud-report-box h2 { 
                color: #111111 !important; 
                font-size: 1.5rem !important; 
                text-align: center; 
                border-bottom: 2px solid #DDDDDD; 
                padding-bottom: 12px; 
                margin-top: 40px !important; 
                margin-bottom: 25px !important; 
                font-weight: 900;
            }
            .ud-report-box h2:first-child {
                margin-top: 0 !important;
            }
            .ud-report-box h3 { 
                color: #333333 !important; 
                font-size: 1.25rem !important; 
                border-left: 6px solid #555555; 
                padding-left: 15px; 
                margin-top: 40px !important; 
                margin-bottom: 20px !important; 
                font-weight: 800;
                background-color: #F0F0F0;
                padding-top: 5px;
                padding-bottom: 5px;
            }
            .ud-report-box p, .ud-report-box li { 
                color: #333333; 
            }
            /* Markdownの太字(**)を「黒文字＋波線」に変換する魔法のCSS */
            .ud-report-box strong {
                font-weight: 900;
                color: #000000;
                text-decoration: underline wavy #555555; /* ダークグレーの波線 */
                text-decoration-thickness: 2px;
                text-underline-offset: 5px;
                background-color: rgba(0,0,0,0.03); /* ほんのり背景色で視認性アップ */
                padding: 0 4px;
            }
            .ud-report-box table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 25px;
            }
            .ud-report-box th, .ud-report-box td {
                border: 1px solid #CCCCCC;
                padding: 12px;
                text-align: center;
                color: #222222;
                background-color: #FFFFFF;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # レポートをUDボックスの中に流し込む
        st.markdown(f"<div class='ud-report-box'>{report_text}</div>", unsafe_allow_html=True)
        
    else:
        st.warning("レポートの表示に失敗しました。データは正常に保存されています。")
    
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; font-weight: bold;'>レポートはポータルからいつでも確認できます</h4>", unsafe_allow_html=True)
    st.link_button("◀ LINEへ戻る", "https://lin.ee/FrawIyY", type="primary")
    st.info("このウィンドウは閉じて構いません。スクリーンショット等での保存をお勧めします。")
