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
        "day_branch_idx": day_branch
    }

    #（10点満点ハイブリッド・運命の波計算エンジン)
def calculate_daily_score(user_nikkanshi, target_date):
    """ユーザーの日干支と対象日の干支を比較し、1〜10点のスコアと根拠を算出する"""
    target = get_date_kanshi(target_date)
    
    # ユーザーの日干と日支を分離
    stems_str = ["", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branches_str = ["", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    
    user_stem_str = user_nikkanshi[0]
    user_branch_str = user_nikkanshi[1]
    user_stem = stems_str.index(user_stem_str)
    user_branch = branches_str.index(user_branch_str)
    
    target_stem = target["day_stem_idx"]
    target_branch = target["day_branch_idx"]
    
    # -------------------------
    # 要素A：環境の波（位相法・天中殺） 1〜5点
    # -------------------------
    env_score = 3 # デフォルト（安定）
    env_reason = "安定した通常の日"
    
    # 天中殺の簡易判定（日干支から）
    tenchusatsu_map = {0: [11, 12], 2: [9, 10], 4: [7, 8], 6: [5, 6], 8: [3, 4], 10: [1, 2]}
    diff = (user_branch - user_stem) % 12
    t_branches = tenchusatsu_map.get(diff, [])
    
    if target_branch in t_branches:
        env_score = 1
        env_reason = "天中殺（リセット・向かい風）"
    else:
        # 位相法の簡易判定（日支同士の比較）
        # 冲（衝突: 差が6）
        if abs(user_branch - target_branch) == 6:
            env_score = 1
            env_reason = "冲（衝突・リセット）"
        # 大半会・半会（異次元の発展: 差が4か8）
        elif abs(user_branch - target_branch) in [4, 8]:
            if user_stem == target_stem:
                env_score = 5
                env_reason = "大半会（異常な追い風）"
            else:
                env_score = 4
                env_reason = "半会（スムーズな前進）"
        # 支合（まとまる）
        elif (user_branch + target_branch) % 12 in [3, 5]: # 簡易的な支合判定
            env_score = 4
            env_reason = "支合（結びつき・前進）"
        # 刑・害・破（ノイズ）
        elif abs(user_branch - target_branch) in [3, 9, 2, 10]: # 簡易判定
            env_score = 2
            env_reason = "刑・害（調整・ノイズ）"
            
    # -------------------------
    # 要素B：精神の波（十大主星） 1〜5点
    # -------------------------
    mind_score = 3
    mind_reason = "通常の精神状態"
    
    # ユーザーの日干(me)と、今日の日干(other)の五行による関係
    me_el = (user_stem - 1) // 2
    other_el = (target_stem - 1) // 2
    rel = (other_el - me_el) % 5
    same_parity = (user_stem % 2) == (target_stem % 2)
    
    stars_matrix = [
        ["貫索星(独立/守り)", "石門星(協調/政治)"], # 比和 (0)
        ["鳳閣星(表現/伝達)", "調舒星(孤独/芸術)"], # 相生(漏) (1)
        ["禄存星(引力/回転財)", "司禄星(蓄積/家庭)"], # 相剋(財) (2)
        ["車騎星(攻撃/前進)", "牽牛星(責任/名誉)"], # 相剋(官) (3)
        ["龍高星(変化/忍耐)", "玉堂星(伝統/静寂)"]  # 相生(印) (4)
    ]
    
    star_name = stars_matrix[rel][0 if same_parity else 1]
    
    if "車騎星" in star_name or "禄存星" in star_name:
        mind_score = 5
        mind_reason = star_name
    elif "貫索星" in star_name or "鳳閣星" in star_name:
        mind_score = 4
        mind_reason = star_name
    elif "石門星" in star_name or "司禄星" in star_name:
        mind_score = 3
        mind_reason = star_name
    elif "龍高星" in star_name or "調舒星" in star_name:
        mind_score = 2
        mind_reason = star_name
    else: # 牽牛星、玉堂星
        mind_score = 1
        mind_reason = star_name

    # -------------------------
    # 最終スコア（ハイブリッド10点満点）
    # -------------------------
    total_score = env_score + mind_score
    
    # スコアから記号を決定
    if total_score >= 9: symbol = "🟡"
    elif total_score >= 7: symbol = "🔴"
    elif total_score >= 5: symbol = "🟢"
    elif total_score >= 3: symbol = "🔵"
    else: symbol = "⚪️"
        
    return {
        "score": total_score,
        "symbol": symbol,
        "env_reason": env_reason,
        "mind_reason": mind_reason,
        "date_str": target_date.strftime("%Y/%m/%d")
    }

#（AIによる専門用語排除・運勢解説生成エンジン）
def generate_daily_advice(today_res):
    """
    算命学の計算結果（today_res）をAIに渡し、
    専門用語を一切使わない現代の言葉で、7項目のアドバイスを生成する
    """
    prompt = f"""
    あなたは、日本で最も予約が取れない、大人気の戦略的ライフ・コンサルタントです。
    以下の【本日の運気データ（算命学の裏ロジック）】をもとに、今日のユーザーへのアドバイスを作成してください。

    # 本日の運気データ
    ・総合スコア: 10点満点中 {today_res['score']} 点
    ・本日のシンボル: {today_res['symbol']}
    ・環境の波（位相法）: {today_res['env_reason']}
    ・精神の波（十大主星）: {today_res['mind_reason']}

    # 【絶対遵守の出力ルール】
    1. 「天中殺」「半会」「禄存星」などの**算命学・四柱推命の専門用語は【絶対に】出力しないでください。**
       必ず「今は少し向かい風が吹いています」「今日は異次元の発展が期待できる日です」「引力と魅力が高まっています」など、現代の日常的な言葉に翻訳して伝えてください。
    2. ユーザーのモチベーションを爆発させる、力強く、かつ温かいトーンで執筆してください。
    3. 以下の7つの項目について、具体的な行動指針（例：金運なら「今日は車などの大きな契約は避けて」など）を含めて、詳細に解説してください。

    # 出力構成（以下のマークダウン形式で必ず出力すること）

    ## 今日の運命の波（総合解説）
    [※10点満点のスコアとシンボルの意味を現代の言葉でキャッチーに解説し、今日1日をどう過ごすべきか総括してください。]

    ## 7つの指針と詳細解説
    ※以下の各項目について、今日の運気に基づいた3段階評価（★☆☆、★★☆、★★★）を付け、1〜2文で具体的なアドバイスを記載してください。

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
    
    tab1, tab2, tab3 = st.tabs(["🏠 マイページ", "📅 波乗りカレンダー", "📜 極秘レポート"])
    
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
        st.subheader("📅 運命の波乗りカレンダー")
        with st.spinner("運命の波を計算中..."):
            try:
                # ユーザーの日干支をスプレッドシートから取得
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
                        user_nikkanshi = row[6] # G列が日干支
                        break
                
                if not user_nikkanshi:
                    st.warning("⚠️ 運勢を計算するためのデータが見つかりません。先に診断を完了してください。")
                else:
                    import datetime
                    import pandas as pd
                    today = datetime.date.today()
                    
                    # 直近30日のデータ生成とグラフ化
                    start_date = today - datetime.timedelta(days=15)
                    dates = [start_date + datetime.timedelta(days=i) for i in range(31)]
                    chart_data = []
                    for d in dates:
                        res = calculate_daily_score(user_nikkanshi, d)
                        chart_data.append({"日付": d.strftime("%m/%d"), "運気スコア": res["score"]})
                    
                    df = pd.DataFrame(chart_data)
                    df.set_index("日付", inplace=True)
                    
                    st.markdown("### 🌊 直近1ヶ月の運命の波")
                    st.line_chart(df["運気スコア"], color="#D32F2F")
                    
                    st.markdown("### 🗓 今日の運勢")
                    today_res = calculate_daily_score(user_nikkanshi, today)
                    st.markdown(f"<p style='text-align: center; font-size: 1.2rem; font-weight: bold;'>{today.strftime('%Y年%m月%d日')}</p>", unsafe_allow_html=True)
                    st.markdown(f"<h1 style='text-align: center; font-size: 4rem; margin: 0;'>{today_res['symbol']}</h1>", unsafe_allow_html=True)
                    st.markdown(f"<h2 style='text-align: center; color: #b8860b;'>スコア: {today_res['score']} / 10</h2>", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    with st.spinner("専属コンサルタントが本日の戦略を執筆中..."):
                        # キャッシュを使って毎回APIを叩かないようにする（コスト削減）
                        @st.cache_data(ttl=3600) # 1時間キャッシュ
                        def get_cached_advice(date_str, _res):
                            return generate_daily_advice(_res)
                            
                        daily_advice = get_cached_advice(today.strftime("%Y%m%d"), today_res)
                        
                        st.markdown("""
                        <style>
                            .daily-advice-box { background: linear-gradient(180deg, #FFFFFF 0%, #F5F5F5 100%); border: 2px solid #b8860b; border-radius: 12px; padding: 25px; margin-top: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
                            .daily-advice-box h2 { color: #b8860b !important; font-size: 1.4rem !important; border-bottom: 1px solid #E0E0E0; padding-bottom: 10px; margin-bottom: 20px; }
                            .daily-advice-box h3 { color: #333333 !important; font-size: 1.1rem !important; margin-top: 20px !important; margin-bottom: 10px !important; border-left: 4px solid #b8860b; padding-left: 10px;}
                            .daily-advice-box p, .daily-advice-box li { font-size: 1rem; line-height: 1.7; color: #444444; }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("<div class='daily-advice-box'>", unsafe_allow_html=True)
                        st.markdown(daily_advice)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    with tab3:
        st.subheader("📜 極秘レポート完全版")
        with st.spinner("データベースからレポートを検索しています..."):
            try:
                creds_dict = st.secrets["gcp_service_account"]
                scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
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
