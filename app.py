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
import calendar
from datetime import timedelta
import altair as alt

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
    div[data-testid="stButton"] button {
        padding: 0.2rem 0.5rem;
        min-height: 2.5rem;
    }
    div.stButton {
        margin-bottom: -15px; 
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    .stApp, .stApp > header, .stApp .main {
        background-color: #FFFFFF !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, div, label, li {
        color: #000000 !important;
    }
    button[kind="secondary"] {
        width: 100% !important;
        height: 65px !important;
        font-size: 18px !important;
        font-weight: 900 !important;
        color: #000000 !important;
        background-color: #FFFFFF !important;
        border: 3px solid #444444 !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05) !important;
    }
    button[kind="secondary"]:hover {
        background-color: #F5F5F5 !important;
        border-color: #111111 !important;
    }
    button[kind="secondary"]:active {
        background-color: #E0E0E0 !important;
        transform: translateY(2px) !important;
        box-shadow: 0px 0px 0px rgba(0,0,0,0) !important;
    }
    button[kind="primary"] {
        width: 100% !important;
        height: 60px !important;
        font-size: 18px !important;
        font-weight: 900 !important;
        border: none !important;
        border-radius: 12px !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1) !important;
    }
    button[kind="primary"]:active {
        transform: translateY(2px) !important;
        box-shadow: 0px 0px 0px rgba(0,0,0,0) !important;
    }
    div[data-testid="stLinkButton"] > a {
        background-color: #06C755 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        width: 100% !important;
        height: 60px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 12px !important;
        font-size: 18px !important;
        text-decoration: none !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div[data-testid="stLinkButton"] > a:hover {
        background-color: #05b34c !important;
    }
    .question-title {
        font-size: 1.4rem;
        font-weight: 900;
        text-align: center;
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
        line-height: 1.6;
        color: #000000 !important;
    }
    .stSelectbox label, .stTextInput label, .stRadio label {
        font-weight: 900 !important;
        font-size: 1.1rem !important;
        color: #000000 !important;
    }
    .stRadio div[role="radiogroup"] label span {
        color: #000000 !important;
        font-weight: bold !important;
    }
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
    {"id": 1, "category": "社会・情報", "text": "Q1. 相手の話すスピードや声のトーンはどうですか？", 
     "options": ["早口で声が大きい・身振りが大きい", "普通・その場に合わせる", "ゆっくりで声は小さめ・落ち着いている", "わからない/観察していない"]},
    {"id": 2, "category": "社会・情報", "text": "Q2. 相手はLINEやメッセージをどう使いますか？", 
     "options": ["要件のみで短く、絵文字は少ない", "スタンプや絵文字をよく使い、雑談もする", "返信が極端に早い、または極端に遅い", "わからない/観察していない"]},
    {"id": 3, "category": "社会・情報", "text": "Q3. 相手の服装や持ち物の傾向は？", 
     "options": ["実用性やコスパを重視している", "ブランドや流行、デザイン性を重視している", "無頓着、またはいつも同じような服装", "わからない/観察していない"]},
    {"id": 4, "category": "恋愛・愛着", "text": "Q4. 相手は自分の弱みや失敗談、プライベートな悩みを話してきますか？", 
     "options": ["自分からよく話してくる（自己開示が多い）", "聞かれれば話すが、自分からはあまり話さない", "絶対にはぐらかす・秘密主義", "わからない/観察していない"]},
    {"id": 5, "category": "恋愛・愛着", "text": "Q5. 相手は「深夜や休日」など、プライベートな時間に仕事や用事以外の連絡をしてきますか？", 
     "options": ["遠慮なくしてくる（境界線が薄い）", "基本的には常識的な時間のみ", "全くしてこない・連絡が取りづらい", "わからない/観察していない"]},
    {"id": 6, "category": "恋愛・愛着", "text": "Q6. 相手が他人に感謝や愛情を示す時、どの行動が多いですか？", 
     "options": ["言葉で「ありがとう」「すごいね」と褒める", "お土産やプレゼントなど「モノ」をくれる", "仕事や作業を「手伝ってくれる（行動）」", "わからない/観察していない"]},
    {"id": 7, "category": "非常時・闘争", "text": "Q7. 予定外のトラブル（行きたい店が閉まっていた等）が起きた時の反応は？", 
     "options": ["すぐにスマホで次の解決策を探す（論理的）", "明らかに不機嫌になったり、口数が減る（感情的）", "「どうする？」と他人に判断を委ねる（依存的）", "わからない/観察していない"]},
    {"id": 8, "category": "非常時・闘争", "text": "Q8. 相手がミスや失敗を指摘された時、最初にとる態度は？", 
     "options": ["素直に非を認め、すぐに謝罪する", "「でも」「だって」と言い訳や反論から入る", "極度に落ち込んだり、自虐的になる", "わからない/観察していない"]},
    {"id": 9, "category": "非常時・闘争", "text": "Q9. 意見が対立した時や、怒りを感じた時、相手はどう表現しますか？", 
     "options": ["正論で理詰めにしたり、声を荒らげる", "無視する、ため息をつく、嫌味を言う", "争いを避けてその場から逃げる・黙る", "わからない/観察していない"]},
    {"id": 10, "category": "コア・相性", "text": "Q10. あなたと会話している時、どちらがたくさん喋っていますか？", 
     "options": ["相手の方が圧倒的に多く喋っている", "お互いに同じくらい", "自分（あなた）の方が多く喋っている", "わからない/観察していない"]},
    {"id": 11, "category": "コア・相性", "text": "Q11. 相手はあなたに対して、アドバイスや指示をしてくる（マウントをとる）傾向がありますか？", 
     "options": ["よくしてくる（教えたがり・上から目線）", "対等な立場で意見を交換する", "あなたの意見に同調・追従することが多い", "わからない/観察していない"]},
    {"id": 12, "category": "コア・相性", "text": "Q12. 相手の「店員やタクシー運転手（第三者）」への態度はどうですか？", 
     "options": ["とても丁寧で腰が低い", "普通・事務的", "横柄、または偉そうな態度をとる事がある", "わからない/観察していない"]}
]

# ==========================================
# 対人関係レーダー用：残回数（BU列）管理関数
# ==========================================
def check_radar_limit(line_id):
    """スプレッドシートのBU列（73番目のインデックス）から今月の残回数を取得する"""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_url = st.secrets["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url).sheet1
        all_data = sheet.get_all_values()
        
        # ヘッダーを探してBU列(残回数)の正確なインデックスを取得（無い場合はデフォルト72とする）
        headers = all_data[0]
        limit_idx = 72 # デフォルト(0始まりでBU列相当を想定)
        for i, h in enumerate(headers):
            if h == '残回数': 
                limit_idx = i
                break
                
        for row in reversed(all_data[1:]):
            if len(row) > 0 and row[0] == line_id:
                if len(row) > limit_idx:
                    try:
                        return int(row[limit_idx])
                    except ValueError:
                        return 3 # 空欄やエラーの場合は3回とする
                return 3
        return 0 # ユーザーがいない場合
    except Exception as e:
        print(f"残回数チェックエラー: {e}")
        return 0

def consume_radar_limit(line_id):
    """実行時にBU列の残回数を1減らす（上書き保存する）"""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet_url = st.secrets["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url).sheet1
        
        headers = sheet.row_values(1)
        limit_col_letter = 'BU' # デフォルト
        for i, h in enumerate(headers):
            if h == '残回数':
                # 列番号(1始まり)から列のアルファベットに変換（簡易版）
                if i < 26: limit_col_letter = chr(65 + i)
                else: limit_col_letter = chr(64 + (i // 26)) + chr(65 + (i % 26))
                break
                
        all_data = sheet.get_all_values()
        target_row_idx = -1
        current_limit = 3
        
        # 下から検索して最新のユーザー行を見つける
        for i in range(len(all_data)-1, 0, -1):
            if len(all_data[i]) > 0 and all_data[i][0] == line_id:
                target_row_idx = i + 1 # スプレッドシートは1行目から始まるため+1
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
# 対人関係レーダー用：ターゲット算命学計算＆プロンプトエンジン
# ==========================================
def calculate_target_sanmeigaku(dob_str):
    """ターゲットの生年月日から、主星(社会)と西方星(恋愛/家庭)、天中殺を算出する"""
    try:
        # ▼ ここが修正点です（.date() を追加して型を揃えました）
        valid_date = datetime.datetime.strptime(dob_str, "%Y%m%d").date()
        year = valid_date.year
        month = valid_date.month
        day = valid_date.day
        
        elapsed = (valid_date - datetime.date(1900, 1, 1)).days
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
        if solar_m == 0: solar_m = 12
        month_branch = (solar_m + 1) % 12
        if month_branch == 0: month_branch = 12
        
        hon_gen_map = {1:10, 2:6, 3:1, 4:2, 5:5, 6:3, 7:4, 8:6, 9:7, 10:8, 11:5, 12:9}
        
        def get_star(target_branch):
            hidden_stem = hon_gen_map[target_branch]
            me_el = (day_stem - 1) // 2
            other_el = (hidden_stem - 1) // 2
            rel = (other_el - me_el) % 5
            same_parity = (day_stem % 2) == (hidden_stem % 2)
            stars_matrix = [
                ["貫索星", "石門星"], ["鳳閣星", "調舒星"], ["禄存星", "司禄星"],
                ["車騎星", "牽牛星"], ["龍高星", "玉堂星"]
            ]
            return stars_matrix[rel][0 if same_parity else 1]
            
        main_star = get_star(month_branch)  
        west_star = get_star(day_branch)    
        
        return {
            "日干支": nikkanshi,
            "天中殺": tenchusatsu,
            "主星": main_star,
            "西方星": west_star
        }
    except Exception as e:
        print(f"ターゲット算命学計算エラー: {e}")
        return None

def generate_radar_prompt(target_name, relation, answers_dict, free_text, target_san, user_main_star):
    """SJTの回答と算命学を統合し、バイアスを排除した最強のプロファイリングプロンプトを生成"""
    
    sjt_text = ""
    for q in RADAR_QUESTIONS:
        ans_idx = answers_dict.get(q["id"], 3) # デフォルトは「わからない」
        ans_str = q["options"][ans_idx]
        sjt_text += f"- {q['text']}\n  回答: {ans_str}\n"
        
    prompt = f"""あなたは元FBIプロファイラーであり、日本一の戦略的ライフ・コンサルタントです。
ユーザーが入力した「ターゲットの行動データ」と「算命学の宿命データ」から、ターゲットの真の姿をプロファイリングしてください。

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
1. 推測語の完全排除: 「〜の傾向があります」「〜かもしれません」「〜のようです」は絶対に使用禁止。すべて「〜です」「〜します」「〜を嫌います」と断言してください。
2. 抽象的表現の禁止: 「論理的です」「優しいです」などの薄い言葉は禁止。「無駄な世間話を嫌い、結論を急ぎます」など、生々しい具体的な行動描写で出力してください。
3. 絵文字・Markdown記号の禁止: 絵文字や、#、* などのMarkdown記号は絶対に出力しないでください。見出しは必ず【 】のみを使用してください。
4. 専門用語の禁止: 算命学の「西方星」「車騎星」などの用語は一切使わず、現代の日常語に翻訳してください。

【出力構成】（必ず以下の7つの見出しと順序で出力すること）

【1. 本性】表の顔と、裏に隠された本当の性格
[算命学の主星とSJTから、基本スペックと無意識の行動原理を断言する]

【2. 仕事・適性】職場で見せる顔と、プロフェッショナルとしての行動原理
[プレッシャーへの耐性や、仕事において何を重視するタイプか、どうすれば評価されるかを解説]

【3. 友人・人脈】交友関係の築き方と、心を許す相手の条件
[広く浅くか、狭く深くか。プライベートでどういう人間を側に置きたがるかを解説]

【4. 恋愛・執着】親密になった時だけ見せる愛情のサインと危うさ
[算命学の西方星から、パーソナルスペースに入った瞬間にどう豹変するか、依存・回避のクセを解説]

【5. 地雷】絶対に触れてはいけないタブーと、ストレス時の攻撃パターン
[トラブル時の反応から、何にキレるのか、怒った時に「無視」か「攻撃」か「逃避」のどれを選ぶかを警告]

【6. 力関係】あの人は「あなた」をどう見て、どう扱おうとしているか
[会話の主導権やマウントの有無から、現在の二人の力関係と相手のスタンスを客観視させる]

【7. 完全攻略】明日から使える、あの人を動かす3つの具体策
[必ず「①〇〇 ②〇〇 ③〇〇」の箇条書き形式で、明日使えるセリフや行動を3つに固定して出力]
"""
    return prompt

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
# ロジック・コールバック関数群
# ==========================================
def calculate_sanmeigaku(year, month, day, time_str):
    if not time_str: time_str = "12:00"
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
    
    star_names = ["天報星", "天印星", "天貴星", "天恍星", "天南星", "天禄星", "天将星", "天堂星", "天胡星", "天極星", "天庫星", "天馳星"]
    chosei_map = {1:12, 2:7, 3:3, 4:10, 5:3, 6:10, 7:6, 8:1, 9:9, 10:4}

    #（カレンダー用・干支計算エンジン）
def get_date_kanshi(target_date):
    """指定した日付の『日・月・年』の干支を自動計算する関数"""
    # 日干支の計算
    elapsed = (target_date - datetime.date(1900, 1, 1)).days
    day_kanshi_num = (10 + elapsed) % 60 + 1
    day_stem = (day_kanshi_num - 1) % 10 + 1
    day_branch = (day_kanshi_num - 1) % 12 + 1
    
    stems_str = ["", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branches_str = ["", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    # 月干支・年干支の計算（簡易節入り：毎月5日基準）
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
    
    # 年と月の十干
    month_stem = ((solar_y % 10) * 2 + solar_m) % 10
    if month_stem == 0: month_stem = 10
    year_stem = (solar_y - 3) % 10
    if year_stem == 0: year_stem = 10
    
    return {
        "day": stems_str[day_stem] + branches_str[day_branch],
        "month": stems_str[month_stem] + branches_str[month_branch],
        "year": stems_str[year_stem] + branches_str[year_branch],
        "day_stem_idx": day_stem,
        "day_branch_idx": day_branch,
        # ▼ この2行を追加 ▼
        "month_stem_idx": month_stem,
        "month_branch_idx": month_branch,
        "year_stem_idx": year_stem,
        "year_branch_idx": year_branch
    }

def calculate_period_score(user_nikkanshi, target_date, period_type="day"):
    """ユーザーの日干支と対象の干支（日・月・年）を比較し、1〜10点のスコアを算出する"""
    target = get_date_kanshi(target_date)
    
    stems_str = ["", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branches_str = ["", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    user_stem_str = user_nikkanshi[0]
    user_branch_str = user_nikkanshi[1]
    user_stem = stems_str.index(user_stem_str)
    user_branch = branches_str.index(user_branch_str)
    
    # 期間に応じて比較対象を切り替え
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
        10: {"sym": "🌈", "title": "超幸運の波", "desc": "限界を超えて物事が予想以上の規模で大きく広がる奇跡的なタイミングです。普段なら届かない目標にも手が届く、異次元の追い風が吹いています。", "points": ["限界を決めずにスケールの大きな目標を立てる", "直感を信じて、普段なら躊躇する大勝負に出る", "周囲を巻き込みながら、リーダーシップを発揮する"]},
        9: {"sym": "⭐️", "title": "最高にツイてる波", "desc": "パズルのピースがピタッとハマるように物事が計画通りに進み、周囲から高く評価されるでしょう。大事な契約や決断に最適なタイミングです。", "points": ["夢の実現に向けて思い切って行動する", "自分の意見や感覚を大事にする", "ここで決めた目標や内容は、簡単には諦めない"]},
        8: {"sym": "🔴", "title": "迷わず動く波", "desc": "心の奥底から情熱が湧き上がり、スピーディーに物事を前進させられる時です。行動量がそのまま結果に直結するため、立ち止まらないことが鍵です。", "points": ["頭で考える前に、まずは第一歩を踏み出す", "自分の思いやアイデアを積極的に発信する", "多少の失敗は気にせず、スピードを最優先する"]},
        7: {"sym": "⚪️", "title": "思い切って決断する波", "desc": "これまでの曖昧な状態に白黒をつけ、新しいステージへ進むためのエネルギーに満ちています。重要な取捨選択を行い、覚悟を決めるのに最適な時です。", "points": ["先延ばしにしていた問題に明確な決断を下す", "不要な人間関係や悪習慣を思い切って断ち切る", "自分の信念を曲げず、毅然とした態度を貫く"]},
        6: {"sym": "🟡", "title": "基礎を固める波", "desc": "派手な動きよりも、足元を固めて実力を蓄えることで運気が安定します。あなたの誠実さやサービス精神が周囲の信頼を集め、豊かさを引き寄せるでしょう。", "points": ["新しいことよりも、今あるタスクを丁寧に仕上げる", "周囲への感謝や手助けを惜しまない", "資産運用や貯蓄など、現実的な管理を見直す"]},
        5: {"sym": "🟢", "title": "味方が増える波", "desc": "あなたの魅力が自然と伝わり、周囲との調和が生まれやすい時です。新しい人脈作りや、チームでの協力作業において、素晴らしい相乗効果を発揮できるでしょう。", "points": ["積極的に人と会い、コミュニケーションを楽しむ", "困っている人がいれば、損得抜きで手を差し伸べる", "新しいコミュニティや学びの場に参加してみる"]},
        4: {"sym": "🔵", "title": "頭の中を整理する波", "desc": "外に向かって動くよりも、内省し、知識を吸収することで運気が研ぎ澄まされます。柔軟な思考が生まれやすいため、計画の練り直しや軌道修正にぴったりです。", "points": ["一人の時間を確保し、静かに自分と向き合う", "読書や勉強などで、新しい知識をインプットする", "現状のやり方に固執せず、柔軟な視点を取り入れる"]},
        3: {"sym": "🟪", "title": "無理をしない波", "desc": "思い通りに進まないことや、人間関係での小さな摩擦が起きやすい調整期です。力技で解決しようとせず、相手に譲る余裕を持つことでトラブルを回避できます。", "points": ["スケジュールに余白を持たせ、時間に余裕を行動する", "意見が対立した時は、一歩引いて相手を立てる", "ストレスを感じたら、無理せず早めに休息をとる"]},
        2: {"sym": "⬜️", "title": "不要なものを手放す波", "desc": "物事がぶつかり合い、変化を余儀なくされる時です。これはネガティブなことではなく、新しい運気を迎え入れるために不要なものを強制的に手放す重要な儀式です。", "points": ["執着している過去の栄光やネガティブな感情を捨てる", "部屋の掃除やデジタルデータの断捨離を徹底する", "予定が急に変わっても、焦らず流れに身を任せる"]},
        1: {"sym": "⚫️", "title": "心と体を休ませる波", "desc": "現実の枠組みが外れ、コントロールが効かない「完全な休息とリセット」の期間です。ここで無理をして動くと空回りするため、エネルギーの充電に専念してください。", "points": ["新しい挑戦、大きな決断、高価な買い物は避ける", "損得勘定を捨て、ボランティアや人のために尽くす", "スマホやPCから離れ、たっぷりと睡眠をとる"]}
    }
    action_data = action_dict[safe_score]
        
    return {
        "score": safe_score, "symbol": action_data["sym"], "title": action_data["title"],
        "desc": action_data["desc"], "points": action_data["points"],
        "env_reason": env_reason, "mind_reason": mind_reason, "date_str": target_date.strftime("%Y/%m/%d")
    }

def get_rule_based_stars(score, mind_reason):
    """AIを使わず、スコアと星の属性から瞬時に31日分の評価を自動生成する関数"""
    if score >= 9: base_star = "★★★"
    elif score >= 5: base_star = "★★☆"
    else: base_star = "★☆☆"
        
    # 特性に応じた星評価の自動調整
    stars = {
        "総合運": "★★★" if score >= 8 else ("★★☆" if score >= 4 else "★☆☆"),
        "人間関係": "★★★" if "石門" in mind_reason or "禄存" in mind_reason else base_star,
        "仕事運": "★★★" if "車騎" in mind_reason or "牽牛" in mind_reason else base_star,
        "恋愛結婚": "★★★" if "禄存" in mind_reason or "司禄" in mind_reason else base_star,
        "金運": "★★★" if "禄存" in mind_reason or "司禄" in mind_reason else base_star,
        "健康運": "★★★" if score >= 5 else "★☆☆",
        "家族親子": "★★★" if "玉堂" in mind_reason or "司禄" in mind_reason else base_star
    }
    # スコアが極端に低い場合はすべて★1に制限
    if score <= 2:
        stars = {k: "★☆☆" for k in stars}
        
    return stars

def calculate_scores():
    scores = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    counts = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    for q_id, val in st.session_state.answers.items():
        question = QUESTIONS[q_id - 1]
        trait = question["trait"]
        is_reverse = question["is_reverse"]
        actual_val = 6 - val if is_reverse else val
        scores[trait] += actual_val
        counts[trait] += 1
    for t in scores:
        scores[t] = round(scores[t] / counts[t], 1) if counts[t] > 0 else 3.0
    return scores

def generate_daily_advice(today_res):
    """
    算命学の計算結果（today_res）をAIに渡し、
    専門用語を一切使わない現代の言葉で、7項目のアドバイスを生成する
    """
    prompt = f"""
    あなたは、日本で最も予約が取れない戦略的ライフ・コンサルタントです。
    以下のデータをもとに、今日のユーザーへのアドバイスを作成してください。
    [スコア: {today_res['score']}点, シンボル: {today_res['symbol']}, 環境: {today_res['env_reason']}, 精神: {today_res['mind_reason']}]

    # 【絶対遵守の出力ルール】
    1. 算命学・四柱推命の専門用語は【絶対に】出力せず、現代の言葉に翻訳すること。
    2. モチベーションを上げる力強いトーンで書くこと。
    3. 7つの項目（総合、人間関係、仕事、恋愛結婚、金運、健康、家族）について、必ず【3段階評価（★☆☆、★★☆、★★★ のいずれか）】を付けてください。※絶対に5段階評価（★★★★★等）や4段階評価は使用しないでください。
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
    
    def get_12star(target_branch):
        if day_stem % 2 != 0:
            offset = (target_branch - chosei_map[day_stem]) % 12
        else:
            offset = (chosei_map[day_stem] - target_branch) % 12
        idx = (2 + offset) % 12
        return star_names[idx]
        
    shonen = get_12star(year_branch)
    chunen = get_12star(month_branch)
    bannen = get_12star(day_branch)

    try:
        clean_time = time_str.replace("：", ":").replace(" ", "").strip()
        if ":" in clean_time: hour = int(clean_time.split(':')[0])
        elif len(clean_time) == 4 and clean_time.isdigit(): hour = int(clean_time[:2])
        elif len(clean_time) == 3 and clean_time.isdigit(): hour = int(clean_time[:1])
        else: hour = 12
    except Exception:
        hour = 12
        
    time_branch = ((hour + 1) // 2) % 12 + 1
    goso_map = {1: 1, 6: 1, 2: 3, 7: 3, 3: 5, 8: 5, 4: 7, 9: 7, 5: 9, 10: 9}
    base_time_stem = goso_map[day_stem]
    time_stem = (base_time_stem + time_branch - 2) % 10 + 1
    jikanshi = stems_str[time_stem] + branches_str[time_branch]
    saibannen = get_12star(time_branch)
    
    return {
        "日干支": nikkanshi, "天中殺": tenchusatsu, "主星": main_star,
        "初年": shonen, "中年": chunen, "晩年": bannen,
        "時干支": jikanshi, "最晩年": saibannen
    }

def start_test(line_name, line_id, dob_str, btime, gender):
    if not dob_str.isdigit() or len(dob_str) != 8:
        st.error("⚠️ 生年月日は8桁の半角数字で入力してください")
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
        "DOB": formatted_dob, "Birth_Time": btime.strip() if btime else "", "Gender": gender
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
    
def calculate_scores():
    scores = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    counts = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    for q_id, val in st.session_state.answers.items():
        question = QUESTIONS[q_id - 1]
        trait = question["trait"]
        is_reverse = question["is_reverse"]
        actual_val = 6 - val if is_reverse else val
        scores[trait] += actual_val
        counts[trait] += 1
    for t in scores:
        scores[t] = round(scores[t] / counts[t], 1) if counts[t] > 0 else 3.0
    return scores
    
def calculate_scores():
    scores = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    counts = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    for q_id, val in st.session_state.answers.items():
        question = QUESTIONS[q_id - 1]
        trait = question["trait"]
        is_reverse = question["is_reverse"]
        actual_val = 6 - val if is_reverse else val
        scores[trait] += actual_val
        counts[trait] += 1
    for t in scores:
        scores[t] = round(scores[t] / counts[t], 1) if counts[t] > 0 else 3.0
    return scores
    
def generate_report_prompt(sanmeigaku, scores):
    prompt = f"""あなたは、専門用語を一切使わず、日常的でユーモアのある表現（例え話など）を使ってユーザーの心を鷲掴みにする、大人気の天才占い師兼ライフ・コンサルタントです。
以下の【ユーザーの分析データ】をインプットとしますが、出力する文章には「癸酉」「石門星」「天将星」「Big5」「開放性」といった【専門用語は絶対にそのまま出力しないでください】。すべて日常的な言葉に翻訳してください。

# ユーザーの分析データ
[算命学]
日干支: {sanmeigaku['日干支']}, 主星: {sanmeigaku['主星']}
12星: 初年[{sanmeigaku['初年']}], 中年[{sanmeigaku['中年']}], 晩年[{sanmeigaku['晩年']}], 最晩年[{sanmeigaku['最晩年']}]
[Big5スコア（1〜5）]
O(開放): {scores['O']}, C(勤勉): {scores['C']}, E(外向): {scores['E']}, A(協調): {scores['A']}, N(神経症): {scores['N']}

# 出力ルール
・「第○章」という見出しは使用禁止。
・ユーザーが最も知りたい部分なので、決して要約せず、具体例や例え話を交えて【詳細に、たっぷりと】語ってください。
・欠点は「伸びしろ」や「愛嬌」としてマイルドかつ面白く伝えること。

# 出力構成（以下のマークダウンと指定の順番通りに必ず出力してください）

## 宿命と現実
宿命のキャッチコピー：[※専門用語を排除した、本来の気質を一言で]
現実のキャッチコピー：[※専門用語を排除した、現在の性格を一言で]
→【ここにユーザーの現状と本質を表す、最大級にキャッチーでユーモアのある総合キャッチコピー】

## あなたの中に眠る15の星
※ユーザーのデータから導き出される「具体的な特徴やクセ」を15個抽出してください。
| | | |
|---|---|---|
| 〇〇の星 | 〇〇の星 | 〇〇の星 |
（※これを5行分出力して15個にする）

## 生まれ持った宿命と現在の性格
### ■ 本来の宿命（あなたが積んでいるエンジン）
本来どんな素晴らしい才能や気質を持って生まれてきたのかを、日常的な例え話を交えて深く解説してください。
### ■ 現在の性格（今のあなたの運転スタイル）
現在、社会でどんな風に振る舞っているのかを深く解説してください。

## 生きづらい正体とうまくいく考え方
本来の宿命と現在の性格の間にどんな「ズレ」が生じているかをズバリ指摘し、どう考え方を変えればスッと楽になるのかをアドバイスしてください。

## 仕事・勉強
【〇〇〇〇〇〇〇〇〇〇〇〇〇〇】
・どんな特性の持ち主か
・強みと弱み（伸びしろ）
・具体的な向き不向き（適職や学習環境）
・[アドバイス1]
・[アドバイス2]
・[アドバイス3]

## 恋愛・結婚
【〇〇〇〇〇〇〇〇〇〇〇〇〇〇】
・恋愛や結婚においてどんな特性の持ち主か
・強みと弱み（愛嬌）
・具体的な向き不向き
・[アドバイス1]
・[アドバイス2]
・[アドバイス3]

## お金
【〇〇〇〇〇〇〇〇〇〇〇〇〇〇】
・[アドバイス1]
・[アドバイス2]
・[アドバイス3]

## 健康
【〇〇〇〇〇〇〇〇〇〇〇〇〇〇】
・[アドバイス1]
・[アドバイス2]
・[アドバイス3]

## あなたの5大欲求パラメーター
1. 自我・自己実現欲（自分のこだわりを貫きたい欲）：[判定結果]
　[解説文]
2. 快楽・表現欲（食欲・性欲・遊びなど楽しむ欲）：[判定結果]
　[解説文]
3. 引力・金銭欲（人やお金を引き寄せ所有したい欲）：[判定結果]
　[解説文]
4. 支配・達成欲（他者をコントロールし達成したい欲）：[判定結果]
　[解説文]
5. 探求・知恵欲（知識を得て自由に考えたい欲）：[判定結果]
　[解説文]

## 結びの言葉
明日から踏み出す「科学的な小さな一歩」を提案し、背中を押す言葉で締めくくってください。
"""
    return prompt

#（AIによる専門用語排除・運勢解説生成エンジン）
def generate_daily_advice(today_res):
    """
    算命学の計算結果（today_res）をAIに渡し、
    専門用語を一切使わない現代の言葉で、7項目のアドバイスを生成する
    """
    prompt = f"""
    あなたは、日本で最も予約が取れない戦略的ライフ・コンサルタントです。
    以下のデータをもとに、今日のユーザーへのアドバイスを作成してください。
    [スコア: {today_res['score']}点, シンボル: {today_res['symbol']}, 環境: {today_res['env_reason']}, 精神: {today_res['mind_reason']}]

    # 【絶対遵守の出力ルール】
    1. 算命学・四柱推命の専門用語は【絶対に】出力せず、現代の言葉に翻訳すること。
    2. モチベーションを上げる力強いトーンで書くこと。
    3. 7つの項目（総合、人間関係、仕事、恋愛結婚、金運、健康、家族）について、必ず【3段階評価（★☆☆、★★☆、★★★ のいずれか）】を付けてください。※絶対に5段階評価（★★★★★等）や4段階評価は使用しないでください。
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
        y, m, d = map(int, ud["DOB"].split('/'))
        sanmeigaku = calculate_sanmeigaku(y, m, d, ud["Birth_Time"])
        stripe_id = st.session_state.get("stripe_id", "")
        
        row_data = [
            ud["LINE_ID"], stripe_id, ud["User_ID"], ud["DOB"], ud["Birth_Time"], ud["Gender"],
            sanmeigaku["日干支"], sanmeigaku["天中殺"], sanmeigaku["主星"], sanmeigaku["初年"],
            sanmeigaku["中年"], sanmeigaku["晩年"], sanmeigaku["時干支"], sanmeigaku["最晩年"]
        ]
        
        for i in range(1, 51): row_data.append(st.session_state.answers.get(i, ""))
        row_data.extend([scores["O"], scores["C"], scores["E"], scores["A"], scores["N"]])
        today_str = datetime.date.today().strftime("%Y/%m/%d")
        row_data.extend([today_str, "FALSE", "FALSE", 3])
        
        llm_prompt = generate_report_prompt(sanmeigaku, scores)
        generated_report = ""
        try:
            openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは国内唯一の『戦略的ライフ・コンサルタント』です。"},
                    {"role": "user", "content": llm_prompt}
                ],
                temperature=0.7
            )
            generated_report = response.choices[0].message.content
            st.session_state.secret_report = generated_report
        except Exception as e:
            st.error(f"【開発者向けエラー(OpenAI)】: {e}")
        
        row_data.append(generated_report)
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
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 マイページ", "📅 波乗りダッシュボード", "📜 極秘レポート", "🎯 対人レーダー"])
    
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
                from oauth2client.service_account import ServiceAccountCredentials
                import gspread
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
                    import datetime
                    import pandas as pd
                    import altair as alt
                    import calendar
                    
                    today = datetime.date.today()
                    current_year = today.year
                    
                    # 画面をスッキリさせるための3つのサブタブ
                    t_day, t_month, t_year = st.tabs(["🌊 今日の波と今月", "🗓 月間グラフ (15ヶ月)", "🗻 年間グラフ (8年)"])
                    
                    # ==========================================
                    # 【サブタブ1】今日の波と今月のカレンダー
                    # ==========================================
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

                    # ==========================================
                    # 【サブタブ2】月間グラフ（前年10月〜今年12月の15ヶ月）
                    # ==========================================
                    with t_month:
                        st.markdown(f"### 🗓 月間・運命の波（{current_year}年の計画）")
                        st.info("前年終盤からの流れと、今年の着地点を確認して長期計画に活用してください。")
                        
                        months_data = []
                        # 前年の10月〜12月（3ヶ月）
                        for m in range(10, 13):
                            m_date = datetime.date(current_year - 1, m, 15)
                            res = calculate_period_score(user_nikkanshi, m_date, period_type="month")
                            months_data.append({"年月": m_date.strftime("%Y年%m月"), "スコア": res["score"], "シンボル": res["symbol"], "タイトル": res["title"], "環境理由": res["env_reason"], "精神理由": res["mind_reason"]})
                        # 今年の1月〜12月（12ヶ月）
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
                        
                        # AIに15ヶ月分の固有解説を「一括で」書かせる（APIコストと速度の最適化）
                        with st.spinner("AIが各月の固有テーマを分析中..."):
                            @st.cache_data(ttl=86400) # 年が切り替わるまでキャッシュ
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

                    # ==========================================
                    # 【サブタブ3】年間グラフ（過去2年+今年+未来5年 = 8年間）と今年の詳細
                    # ==========================================
                    with t_year:
                        st.markdown("### 🗻 年間・運命の波（8年推移）")
                        years_data = []
                        # 過去2年〜未来5年（計8年）
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
                            @st.cache_data(ttl=86400) # 年間は1日キャッシュ（年が変われば自動更新）
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
                                    return "⚠️ エラーが発生しました。"

                            yearly_advice = get_cached_yearly_advice(str(current_year), this_year_res)
                            st.markdown(f"<div class='advice-box'>{yearly_advice}</div>", unsafe_allow_html=True)
                            
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    with tab3:
        st.subheader("📜 極秘レポート完全版")
        with st.spinner("データベースからレポートを検索しています..."):
            try:
                creds_dict = st.secrets["gcp_service_account"]
                scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                from oauth2client.service_account import ServiceAccountCredentials
                import gspread
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
                    st.markdown("""
                    <style>
                        .secret-report-box { background: linear-gradient(180deg, #FFFFFF 0%, #FAFAFA 100%); border: 2px solid #D32F2F; border-radius: 15px; padding: 30px 20px; margin-top: 10px; margin-bottom: 30px; box-shadow: 0 8px 25px rgba(0,0,0,0.08); }
                        .secret-report-box h2 { color: #C62828 !important; font-size: 1.6rem !important; text-align: center; border-bottom: 2px solid #FFEBEE; padding-bottom: 15px; margin-bottom: 25px; }
                        .secret-report-box h3 { color: #111111 !important; font-size: 1.3rem !important; border-left: 5px solid #D32F2F; padding-left: 10px; margin-top: 35px !important; margin-bottom: 15px !important; }
                        .secret-report-box p, .secret-report-box li { font-size: 1.05rem; line-height: 1.8; color: #333333; }
                    </style>
                    """, unsafe_allow_html=True)
                    st.markdown("<div class='secret-report-box'>", unsafe_allow_html=True)
                    st.markdown(report_text)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.warning("⚠️ レポートが見つかりませんでした。まだ診断が完了していないか、データが存在しません。")
            except Exception as e:
                st.error(f"データベース通信エラー: {e}")

    # ==========================================
    # 【タブ4】対人関係レーダー（SJT12問 ＋ AIプロファイリング）
    # ==========================================

    with tab4:
        st.subheader("対人関係レーダー")
        
        # ▼ ドロップダウンリスト（選択肢）も白く見やすくするための完全版CSS
        st.markdown("""
        <style>
            div[data-baseweb="select"] > div, 
            div[data-baseweb="input"] > div, 
            div[data-baseweb="textarea"] > div {
                background-color: #FAFAFA !important;
                border: 1px solid #CCCCCC !important;
            }
            div[data-baseweb="select"] span {
                color: #000000 !important;
            }
            ul[role="listbox"], ul[data-baseweb="menu"], li[role="option"] {
                background-color: #FAFAFA !important;
                color: #000000 !important;
            }
            input, textarea {
                color: #000000 !important;
                background-color: transparent !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # セッションステートの初期化（タブ4専用）
        if "radar_answers" not in st.session_state:
            st.session_state.radar_answers = {}
        if "radar_result" not in st.session_state:
            st.session_state.radar_result = None
            
        with st.spinner("システム接続中..."):
            radar_limit = check_radar_limit(st.session_state.line_id)

        # ==========================================
        # 状態1：結果表示画面（上限に関わらず、直前の結果があれば最優先で表示する）
        # ==========================================
       elif st.session_state.radar_result:
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
            
            if st.button("▶︎ 別の相手を検索する（クリックするとレポーが消えます）"):
                st.session_state.radar_result = None
                st.session_state.radar_answers = {}
                st.rerun()

        # ==========================================
        # 状態2：AI解析中画面
        # ==========================================
        elif st.session_state.radar_result == "processing":
            with st.spinner("AIが相手の深層心理と攻略法を解析中...（約20秒）"):
                # ここで残回数を消費
                success = consume_radar_limit(st.session_state.line_id)
                if not success:
                    st.error("データベースの更新に失敗しました。")
                    st.session_state.radar_result = None
                    st.rerun()
                else:
                    try:
                        # ユーザー自身のデータを取得
                        creds_dict = st.secrets["gcp_service_account"]
                        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                        client = gspread.authorize(creds)
                        sheet = client.open_by_url(st.secrets["spreadsheet_url"]).sheet1
                        all_data = sheet.get_all_values()
                        
                        user_main_star = "不明"
                        for row in reversed(all_data):
                            if len(row) > 8 and row[0] == st.session_state.line_id:
                                user_main_star = row[8] # I列(主星)を想定
                                break
                                
                        # プロンプト生成（セッションに保存されたデータを使用）
                        prompt = generate_radar_prompt(
                            st.session_state.target_name, 
                            st.session_state.target_relation, 
                            st.session_state.radar_answers, 
                            st.session_state.free_text, 
                            st.session_state.target_san, 
                            user_main_star
                        )
                        
                        openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                        response = openai_client.chat.completions.create(
                            model="gpt-4o", 
                            messages=[
                                {"role": "system", "content": "あなたは国内唯一の『戦略的ライフ・コンサルタント』です。専門用語は絶対に使わず、現代の言葉でアドバイスします。"},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7
                        )
                        st.session_state.radar_result = response.choices[0].message.content
                        st.rerun() # 画面をリロードして状態1へ遷移
                    except Exception as e:
                        st.error(f"AI解析中にエラーが発生しました: {e}")
                        st.session_state.radar_result = None
                        st.rerun()

        # ==========================================
        # 状態3：入力フォーム画面
        # ==========================================
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
                                # 状態2(処理中)に遷移するため、フォームの入力をセッションに保存
                                st.session_state.target_name = target_name
                                st.session_state.target_relation = target_relation
                                st.session_state.free_text = free_text
                                st.session_state.target_san = target_san
                                st.session_state.radar_result = "processing"
                                st.rerun()

    st.stop()

# ==========================================
# 診断テストの描画
# ==========================================
if st.session_state.step == "user_info":
    st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h2 style='font-weight: bold;'>プレミアム裏ステータス診断へ</h2></div>", unsafe_allow_html=True)
    st.markdown(f"数億通りのAI×宿命アルゴリズムで、**{st.session_state.line_name}さん**の深層心理と本来のポテンシャルを完全解析します。まずは基本プロフィールをご入力ください。")
    
    with st.form("info_form"):
        st.markdown("<p style='font-weight: 900; margin-bottom: 0;'>生年月日（半角数字8桁）</p>", unsafe_allow_html=True)
        dob_input = st.text_input("生年月日", max_chars=8, placeholder="例 19961229", label_visibility="collapsed")
        btime = st.text_input("出生時間（任意・不明なら空欄のまま）", value="", placeholder="例 23:16")
        gender = st.radio("性別", ["男性", "女性", "その他", "回答しない"], horizontal=True)
        submitted = st.form_submit_button("適性テストを開始する", type="primary")
        if submitted:
            start_test(st.session_state.line_name, st.session_state.line_id, dob_input, btime, gender)
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
        st.markdown('<div style="padding: 1.5rem; background-color: #FFFCF9; border: 2px solid #FCEADE; border-radius: 12px; margin-bottom: 2rem; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);">', unsafe_allow_html=True)
        st.markdown(st.session_state.secret_report)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ レポートの表示に時間がかかっています。データは正常に保存されました。")
    
    st.markdown("<h4 style='text-align: center; font-weight: bold;'>▼ 日々の最適化アクションを受け取る ▼</h4>", unsafe_allow_html=True)
    st.link_button("LINEに戻る", "https://lin.ee/FrawIyY", type="primary")
    st.info("このウィンドウは閉じて構いません。レポートはスクリーンショット等で保存することをお勧めします。")
