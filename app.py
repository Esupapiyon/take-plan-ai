import streamlit as st
import pandas as pd
import datetime
import statistics
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import requests
import openai # 【追加】OpenAIライブラリをインポート

# ==========================================
# 1. ページ設定とUI改善CSS（一番上に書く）
# ==========================================
st.set_page_config(
    page_title="プレミアム裏ステータス診断",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 【追加・修正①：ボタン余白を削る魔法のCSS】
st.markdown("""
    <style>
    div[data-testid="stButton"] button {
        padding: 0.2rem 0.5rem;
        min-height: 2.5rem;
    }
    div.stButton {
        margin-bottom: -15px; 
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CSS: 強制ライトモード ＆ ユニバーサルデザイン ＆ 余白極小化 ＆ LINEボタン化
# ==========================================
st.markdown("""
<style>
    /* Streamlit特有の上下余白を極限まで削る */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }

    /* 強制ライトモード（OSのダークモード設定を無効化） */
    .stApp, .stApp > header, .stApp .main {
        background-color: #FFFFFF !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, div, label, li {
        color: #000000 !important;
    }
    
    /* ユニバーサルデザインの回答ボタン (Secondary) */
    button[kind="secondary"] {
        width: 100% !important;
        height: 65px !important;
        font-size: 18px !important;
        font-weight: 900 !important;
        color: #000000 !important;
        background-color: #FFFFFF !important;
        border: 3px solid #444444 !important; /* 太くて濃いグレーの枠線 */
        border-radius: 12px !important;       /* 角丸 */
        margin-bottom: 12px !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05) !important;
    }
    
    /* ボタンホバー・タップ時の挙動 (Secondary) */
    button[kind="secondary"]:hover {
        background-color: #F5F5F5 !important;
        border-color: #111111 !important;
    }
    button[kind="secondary"]:active {
        background-color: #E0E0E0 !important;
        transform: translateY(2px) !important;
        box-shadow: 0px 0px 0px rgba(0,0,0,0) !important;
    }

    /* Primaryボタンのスタイル上書き（ベース） */
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

    /* LINEリンクボタンを強制的にLINEカラー（#06C755）にする強力なCSS */
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

    /* 質問テキストのスタイル（上下余白を小さく調整） */
    .question-title {
        font-size: 1.4rem;
        font-weight: 900;
        text-align: center;
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
        line-height: 1.6;
        color: #000000 !important;
    }
    
    /* 入力フォームのラベル強調 */
    .stSelectbox label, .stTextInput label, .stRadio label {
        font-weight: 900 !important;
        font-size: 1.1rem !important;
        color: #000000 !important;
    }
    
    /* ラジオボタンの選択肢テキストの色を強制的に黒に */
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
    # O（開放性）
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

    # C（勤勉性）
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

    # E（外向性）
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

    # A（協調性）
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

    # N（神経症的傾向）
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
    st.session_state.step = "user_info" # user_info -> test -> processing -> done
if "current_q" not in st.session_state:
    st.session_state.current_q = 1
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "max_q" not in st.session_state:
    st.session_state.max_q = 30 # 初期は30問で設定
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "line_id" not in st.session_state:
    st.session_state.line_id = None
if "line_name" not in st.session_state:
    st.session_state.line_name = None
if "stripe_id" not in st.session_state:
    st.session_state.stripe_id = "" # Stripe ID用のステートを追加
if "secret_report" not in st.session_state:
    st.session_state.secret_report = "" # 【追加】生成された極秘レポート保存用

# ==========================================
# ロジック・コールバック関数群
# ==========================================
def calculate_sanmeigaku(year, month, day, time_str):
    """【絶対遵守】算命学の自動計算エンジン（五鼠遁と堅牢な時間パースの実装）"""
    # 1. 出生時間が空欄の場合は12:00として処理を続行（絶対にエラーで止めない）
    if not time_str: 
        time_str = "12:00"
    
    target_date = datetime.date(year, month, day)
    
    # 2. 【日干支】1900/1/1(甲戌=11)を基準とした経過日数モジュロ演算
    elapsed = (target_date - datetime.date(1900, 1, 1)).days
    day_kanshi_num = (10 + elapsed) % 60 + 1
    day_stem = (day_kanshi_num - 1) % 10 + 1
    day_branch = (day_kanshi_num - 1) % 12 + 1
    
    stems_str = ["", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    branches_str = ["", "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    nikkanshi = stems_str[day_stem] + branches_str[day_branch]
    
    # 3. 【天中殺】日干支から割り出し
    tenchusatsu_map = {0: "戌亥", 2: "申酉", 4: "午未", 6: "辰巳", 8: "寅卯", 10: "子丑"}
    diff = (day_branch - day_stem) % 12
    tenchusatsu = tenchusatsu_map.get(diff, "")
    
    # 4. 【月干支・年干支の算出】簡易節入りロジック（毎月5日を基準）
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
    
    # 5. 【主星（十大主星）】日干と月支本元からの算出
    hon_gen_map = {1:10, 2:6, 3:1, 4:2, 5:5, 6:3, 7:4, 8:6, 9:7, 10:8, 11:5, 12:9}
    month_hidden_stem = hon_gen_map[month_branch]
    
    me_el = (day_stem - 1) // 2
    other_el = (month_hidden_stem - 1) // 2
    rel = (other_el - me_el) % 5
    same_parity = (day_stem % 2) == (month_hidden_stem % 2)
    
    stars_matrix = [
        ["貫索星", "石門星"],
        ["鳳閣星", "調舒星"],
        ["禄存星", "司禄星"],
        ["車騎星", "牽牛星"],
        ["龍高星", "玉堂星"]
    ]
    main_star = stars_matrix[rel][0 if same_parity else 1]
    
    # 6. 【十二大従星】日干を基準として算出するための共通関数
    star_names = ["天報星", "天印星", "天貴星", "天恍星", "天南星", "天禄星", "天将星", "天堂星", "天胡星", "天極星", "天庫星", "天馳星"]
    chosei_map = {1:12, 2:7, 3:3, 4:10, 5:3, 6:10, 7:6, 8:1, 9:9, 10:4}
    
    def get_12star(target_branch):
        if day_stem % 2 != 0: # 陽干
            offset = (target_branch - chosei_map[day_stem]) % 12
        else: # 陰干
            offset = (chosei_map[day_stem] - target_branch) % 12
        idx = (2 + offset) % 12
        return star_names[idx]
        
    shonen = get_12star(year_branch)
    chunen = get_12star(month_branch)
    bannen = get_12star(day_branch)

    # ---------------------------------------------------------
    # 【絶対遵守】時干支と十二大従星_最晩年の正確な算出（五鼠遁の実装）
    # ---------------------------------------------------------
    try:
        # 全角コロンを半角に変換、余計な空白を削除し、表記揺れを吸収
        clean_time = time_str.replace("：", ":").replace(" ", "").strip()
        
        if ":" in clean_time:
            hour = int(clean_time.split(':')[0])
        elif len(clean_time) == 4 and clean_time.isdigit():
            hour = int(clean_time[:2]) # 例: "2316" -> 23
        elif len(clean_time) == 3 and clean_time.isdigit():
            hour = int(clean_time[:1]) # 例: "915" -> 9
        else:
            hour = 12
    except Exception:
        hour = 12 # パースエラー時は12:00（午）として安全に処理
        
    # 1. 時間から「時支」への変換ルール（23:00〜00:59=子(1), 01:00〜02:59=丑(2)...）
    time_branch = ((hour + 1) // 2) % 12 + 1
    
    # 2. 「五鼠遁（ごそとん）」の実装（日干から子時間の十干を特定する）
    goso_map = {1: 1, 6: 1, 2: 3, 7: 3, 3: 5, 8: 5, 4: 7, 9: 7, 5: 9, 10: 9}
    base_time_stem = goso_map[day_stem]
    
    # 子時間を基準として、該当する時支まで十干を進める
    time_stem = (base_time_stem + time_branch - 2) % 10 + 1
    
    jikanshi = stems_str[time_stem] + branches_str[time_branch]
    
    # 3. 算出された時支と日干を用いて十二大従星（最晩年）を動的に算出
    saibannen = get_12star(time_branch)
    
    return {
        "日干支": nikkanshi,
        "天中殺": tenchusatsu,
        "主星": main_star,
        "初年": shonen,
        "中年": chunen,
        "晩年": bannen,
        "時干支": jikanshi,     # 正確な時干支
        "最晩年": saibannen     # 動的に変動する最晩年
    }

def start_test(line_name, line_id, dob_str, btime, gender):
    """基本情報の入力完了・バリデーション・テスト開始"""
    # 生年月日のチェック
    if not dob_str.isdigit() or len(dob_str) != 8:
        st.error("⚠️ 生年月日は8桁の半角数字で入力してください（例：19961229）")
        return
    
    # 実在する日付かどうかのチェック ＋ 年代の範囲チェック
    try:
        valid_date = datetime.datetime.strptime(dob_str, "%Y%m%d")
        current_year = datetime.date.today().year
        if not (1900 <= valid_date.year <= current_year):
            st.error(f"⚠️ 正しい年代の生年月日を入力してください（1900年〜{current_year}年）")
            return
        formatted_dob = valid_date.strftime("%Y/%m/%d")
    except ValueError:
        st.error("⚠️ 存在しない日付です。正しい生年月日を入力してください。")
        return

    st.session_state.user_data = {
        "User_ID": line_name,    # URLから取得したLINE名（またはゲスト）
        "LINE_ID": line_id,      # URLから取得したLINE_ID
        "DOB": formatted_dob,
        "Birth_Time": btime.strip() if btime else "",
        "Gender": gender
    }
    st.session_state.step = "test"

def handle_answer(q_id, answer_value):
    """回答を保存し、次へ進む（CATロジック・二重タップ防止含む）"""
    # 【二重タップ・スキップ防止】現在の問題番号と違うボタンの通信は無視する
    if st.session_state.current_q != q_id:
        return

    st.session_state.answers[q_id] = answer_value
    
    # 【CATロジック】第30問目で回答の分散（矛盾）をチェック
    if st.session_state.current_q == 30:
        ans_values = list(st.session_state.answers.values())
        variance = statistics.variance(ans_values) if len(ans_values) > 1 else 0
        
        # 分散が小さすぎる場合は50問に延長
        if variance < 0.8: 
            st.session_state.max_q = 50
        else:
            finish_test()
            return

    # 最終問題に到達した場合
    if st.session_state.current_q >= st.session_state.max_q:
        finish_test()
    else:
        st.session_state.current_q += 1

def go_back():
    """1つ前の質問に戻るコールバック"""
    if st.session_state.current_q > 1:
        st.session_state.current_q -= 1

def finish_test():
    """テスト終了処理・ステート切り替え"""
    st.session_state.step = "processing"
    
def calculate_scores():
    """Big5スコアの計算（逆転項目対応）"""
    scores = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    counts = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    
    for q_id, val in st.session_state.answers.items():
        question = QUESTIONS[q_id - 1]
        trait = question["trait"]
        is_reverse = question["is_reverse"]
        
        # 逆転項目の場合は数値を反転させる
        actual_val = 6 - val if is_reverse else val
        
        scores[trait] += actual_val
        counts[trait] += 1
        
    for t in scores:
        scores[t] = round(scores[t] / counts[t], 1) if counts[t] > 0 else 3.0
    return scores
    
def generate_report_prompt(sanmeigaku, scores):
    """LLM（ChatGPT等）に投げるための極秘レポート生成プロンプトを作成する"""
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
※ユーザーのデータから導き出される「具体的な特徴やクセ」を15個抽出してください（例：上下関係に厳しい星、プライドがエベレスト級の星、胃腸が弱りやすい星 など）。
※出力形式は「特徴」などのヘッダー文字は使わず、以下のようなシンプルな3列の表（Markdown形式）で出力してください。
| | | |
|---|---|---|
| 〇〇の星 | 〇〇の星 | 〇〇の星 |
（※これを5行分出力して15個にする）

## 生まれ持った宿命と現在の性格
※絶対に要約せず、以下の2つの見出しを分けて詳細に解説してください。
### ■ 本来の宿命（あなたが積んでいるエンジン）
本来どんな素晴らしい才能や気質を持って生まれてきたのかを、日常的な例え話を交えて深く解説してください。
### ■ 現在の性格（今のあなたの運転スタイル）
現在、社会でどんな風に振る舞っているのか（Big5のデータに基づくリアルな現状）を深く解説してください。

## 生きづらい正体とうまくいく考え方
本来の宿命と現在の性格の間にどんな「ズレ」が生じているか（なぜ疲れるのか、なぜ評価されないのか）をズバリ指摘し、どう考え方を変えればスッと楽になるのかをアドバイスしてください。

## 仕事・勉強
【〇〇〇〇〇〇〇〇〇〇〇〇〇〇】（※冒頭に目を引く一言キャッチコピー。例：好きなことで起業すると大金持ちになれるかも）
※以下の3項目を必ず含めて、詳細に解説してください。
・どんな特性の持ち主か
・強みと弱み（伸びしろ）
・具体的な向き不向き（適職や学習環境）
最後に以下の形式で3つのアドバイスを提示してください。
・[アドバイス1]
・[アドバイス2]
・[アドバイス3]

## 恋愛・結婚
【〇〇〇〇〇〇〇〇〇〇〇〇〇〇】（※冒頭に一言キャッチコピー）
※以下の3項目を必ず含めて、詳細に解説してください。
・恋愛や結婚においてどんな特性の持ち主か
・強みと弱み（愛嬌）
・具体的な向き不向き（どんな相手と合い、どんな相手だと疲れるか）
最後に以下の形式で3つのアドバイスを提示してください。
・[アドバイス1]
・[アドバイス2]
・[アドバイス3]

## お金
【〇〇〇〇〇〇〇〇〇〇〇〇〇〇】（※冒頭に一言キャッチコピー）
※お金の使い方のクセ、稼ぐ力、無意識のブロックなどを詳細に解説してください。
最後に以下の形式で3つのアドバイスを提示してください。
・[アドバイス1]
・[アドバイス2]
・[アドバイス3]

## 健康
【〇〇〇〇〇〇〇〇〇〇〇〇〇〇】（※冒頭に一言キャッチコピー）
※ストレスが出やすい部位、体調を崩すパターンなどを詳細に解説してください。
最後に以下の形式で3つのアドバイスを提示してください。
・[アドバイス1]
・[アドバイス2]
・[アドバイス3]

## あなたの5大欲求パラメーター
※必ず以下の順番で、判定結果とユーモアのある解説を出力してください。
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
明日から踏み出す「科学的な小さな一歩」を提案し、ユーザーの背中を優しく、力強く押す言葉で締めくくってください。
"""
    return prompt

def send_line_result(line_id, sanmeigaku, scores):
    """【要件定義4】LINEへのダイレクト結果送信（Messaging API）"""
    if not line_id:
        return
        
    try:
        token = st.secrets["LINE_ACCESS_TOKEN"]
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        # 美しくフォーマットされた結果テキスト
        text = "✨ 診断が完了しました！\n\n"
        text += "【あなたの宿命（算命学）】\n"
        text += f"日干支: {sanmeigaku['日干支']}\n"
        text += f"天中殺: {sanmeigaku['天中殺']}\n"
        text += f"主星: {sanmeigaku['主星']}\n"
        text += f"初年: {sanmeigaku['初年']} / 中年: {sanmeigaku['中年']} / 晩年: {sanmeigaku['晩年']}\n"
        text += f"時干支: {sanmeigaku['時干支']}\n"
        text += f"最晩年: {sanmeigaku['最晩年']}\n\n"
        
        text += "【深層心理（Big5スコア）】\n"
        text += f"開放性(O): {scores['O']}\n"
        text += f"勤勉性(C): {scores['C']}\n"
        text += f"外向性(E): {scores['E']}\n"
        text += f"協調性(A): {scores['A']}\n"
        text += f"神経症(N): {scores['N']}\n\n"
        text += "詳細な解説レポートは順次お届けします。お楽しみに！"

        payload = {
            "to": line_id,
            "messages": [{"type": "text", "text": text}]
        }
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        # 送信に失敗してもアプリ側の処理は止めない
        print(f"LINE送信エラー: {e}")

def save_to_spreadsheet():
    """Googleスプレッドシートへの書き込み処理とOpenAIによるレポート生成"""
    try:
        # Streamlit secretsから認証情報を取得
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 対象のスプレッドシートとワークシートを取得
        sheet_url = st.secrets["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url).sheet1
        
        # Big5スコアの計算
        scores = calculate_scores()
        
        # 算命学パラメータの自動計算
        ud = st.session_state.user_data
        y, m, d = map(int, ud["DOB"].split('/'))
        sanmeigaku = calculate_sanmeigaku(y, m, d, ud["Birth_Time"])
        
        # セッションからStripe IDを取得
        stripe_id = st.session_state.get("stripe_id", "")
        
        # 保存するデータの配列
        row_data = [
            ud["LINE_ID"],          # A列: LINEのID
            stripe_id,              # B列: Stripe決済ID
            ud["User_ID"],          # C列: LINEの登録名
            ud["DOB"],              # 生年月日
            ud["Birth_Time"],       # 出生時間
            ud["Gender"],           # 性別
            sanmeigaku["日干支"],    # 占い枠1
            sanmeigaku["天中殺"],    # 占い枠2
            sanmeigaku["主星"],      # 占い枠3
            sanmeigaku["初年"],      # 占い枠4
            sanmeigaku["中年"],      # 占い枠5
            sanmeigaku["晩年"],      # 占い枠6
            sanmeigaku["時干支"],    # 占い枠7
            sanmeigaku["最晩年"]     # 占い枠8
        ]
        
        # Q1〜Q50の回答
        for i in range(1, 51):
            row_data.append(st.session_state.answers.get(i, ""))
            
        # O, C, E, A, N Scores
        row_data.extend([scores["O"], scores["C"], scores["E"], scores["A"], scores["N"]])
        
      # 課金開始日, 極秘ライブラリ解放権限, 残回数
        today_str = datetime.date.today().strftime("%Y/%m/%d")
        row_data.extend([today_str, "FALSE", "FALSE", 3])
        
        # BV列用として空白を1つ追加
        row_data.append("")
        
        # LLM用プロンプトの生成
        llm_prompt = generate_report_prompt(sanmeigaku, scores)
        
        # -----------------------------------------------------
        # ▼ OpenAI APIによる極秘レポートの生成
        # -----------------------------------------------------
        generated_report = "" # 保存用の変数を初期化
        try:
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは、東洋哲学の最高峰「算命学」と、最新の行動心理学「Big5」を完全に統合した、国内唯一の『戦略的ライフ・コンサルタント』です。"},
                    {"role": "user", "content": llm_prompt}
                ],
                temperature=0.7
            )
            # 生成されたテキストを取得
            generated_report = response.choices[0].message.content
            st.session_state.secret_report = generated_report
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            st.session_state.secret_report = "" # エラー時は空にする
            st.error(f"【開発者向け詳細エラー(OpenAI)】: {e}")
        
        # 【修正】プロンプトではなく、AIが生成したテキスト結果をBW列に追加
        row_data.append(generated_report)
        
        # ▼ 最後にスプレッドシートへの書き込みを実行する
        sheet.append_row(row_data)
        
        # 完了時のLINEへのダイレクトプッシュ送信
        send_line_result(ud["LINE_ID"], sanmeigaku, scores)
        
        return True

        # -----------------------------------------------------
        # ▼ 【追加】OpenAI APIによる極秘レポートの生成とエラー出力
        # -----------------------------------------------------
        try:
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは、東洋哲学の最高峰「算命学」と、最新の行動心理学「Big5」を完全に統合した、国内唯一の『戦略的ライフ・コンサルタント』です。"},
                    {"role": "user", "content": llm_prompt}
                ],
                temperature=0.7
            )
            st.session_state.secret_report = response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            st.session_state.secret_report = "" # エラー時は空にする
            # 画面上に詳細なエラー文を出力（デバッグ用）
            st.error(f"【開発者向け詳細エラー(OpenAI)】: {e}")
        
        # 完了時のLINEへのダイレクトプッシュ送信
        send_line_result(ud["LINE_ID"], sanmeigaku, scores)
        
        return True
        
    except Exception as e:
        # スプレッドシート保存などの致命的なエラー用
        st.error(f"【開発者向け詳細エラー(Spreadsheet/System)】: {e}")
        return False

# ==========================================
# UI レンダリング
# ==========================================

# ---------------------------------------------------------
# 2. URLからのデータ受け取り（LIFF廃止・パラメータ一本化）
# ---------------------------------------------------------
def get_params_robust():
    """新旧バージョン・型違いに対応したパラメータ取得"""
    params = {}
    try:
        if hasattr(st.query_params, "to_dict"):
            params = st.query_params.to_dict()
        else:
            params = dict(st.query_params)
    except:
        try:
            params = st.experimental_get_query_params()
        except:
            pass
    return params

# セッションにまだIDがない場合のみ取得処理を行う
if not st.session_state.line_id:
    raw_params = get_params_robust()
    
    # 値抽出（リスト・文字列両対応）
    p_line_id = raw_params.get("line_id", "")
    if isinstance(p_line_id, list) and len(p_line_id) > 0:
        p_line_id = p_line_id[0]

    p_line_name = raw_params.get("line_name", "")
    if isinstance(p_line_name, list) and len(p_line_name) > 0:
        p_line_name = p_line_name[0]
        
    # 【追加②：Stripe IDを受け取る】
    p_stripe_id = raw_params.get("stripe_id", "")
    if isinstance(p_stripe_id, list) and len(p_stripe_id) > 0:
        p_stripe_id = p_stripe_id[0]

    # URLパラメータチェック
    if p_line_id and p_line_id != "不明":
        # IDがあればセッションに保存して承認
        st.session_state.line_id = p_line_id
        st.session_state.stripe_id = p_stripe_id
        
        if p_line_name and p_line_name != "ゲスト":
            st.session_state.line_name = urllib.parse.unquote(p_line_name)
        else:
            st.session_state.line_name = "ゲスト"
    else:
        # IDが無い場合はアクセス拒否
        st.warning("⚠️ このページは専用リンクからアクセスしてください。")
        st.info("LINE公式アカウントのメニュー、または決済完了ページから再度アクセスをお願いします。")
        st.stop() # 処理をここで完全に停止

# --- 1. 基本情報入力画面 ---
if st.session_state.step == "user_info":
    
# ==========================================
    # 3. タイトルと説明文の表示（差し替え）
    # ==========================================
    st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='font-weight: bold;'>プレミアム裏ステータス診断へ</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # 名前はセッションステートから呼び出して太字で表示
    st.markdown(f"数億通りのAI×宿命アルゴリズムで、**{st.session_state.line_name}さん**の深層心理と本来のポテンシャルを完全解析します。まずは基本プロフィールをご入力ください。")
    
    with st.form("info_form"):
        # 生年月日の8桁数字入力
        st.markdown("<p style='font-weight: 900; margin-bottom: 0;'>生年月日（半角数字8桁）</p>", unsafe_allow_html=True)
        dob_input = st.text_input("生年月日", max_chars=8, placeholder="例 19961229", label_visibility="collapsed")
        
        # 出生時間のプレースホルダー
        btime = st.text_input("出生時間（任意・不明なら空欄のまま）", value="", placeholder="例 23:16")
        
        # 性別入力
        gender = st.radio("性別", ["男性", "女性", "その他", "回答しない"], horizontal=True)
        
        # 送信ボタン
        submitted = st.form_submit_button("適性テストを開始する", type="primary")
        if submitted:
            # start_testには line_name と line_id を渡す
            start_test(st.session_state.line_name, st.session_state.line_id, dob_input, btime, gender)
            
            if st.session_state.step == "test":
                st.rerun()

# --- 2. CAT テスト画面 (SPA・1画面1問) ---
elif st.session_state.step == "test":
    current_q_num = st.session_state.current_q
    max_q_num = st.session_state.max_q
    
    # プログレスバー
    progress_val = current_q_num / max_q_num
    st.progress(progress_val)
    st.caption(f"現在 {current_q_num} 問目 / (最大 {max_q_num} 問)")
    
    # 1つ前に戻るボタン
    if current_q_num > 1:
        st.button("◀ 前の質問に戻る", on_click=go_back, key=f"btn_back_{current_q_num}", type="secondary")
    
    # 質問表示
    question_data = QUESTIONS[current_q_num - 1]
    st.markdown(f"<div class='question-title'>{question_data['text']}</div>", unsafe_allow_html=True)
    
    st.write("---")
    
    # 縦並びのUDボタン
    st.button("全く違う", on_click=handle_answer, args=(current_q_num, 1), key=f"btn_1_{current_q_num}", type="secondary")
    st.button("やや違う", on_click=handle_answer, args=(current_q_num, 2), key=f"btn_2_{current_q_num}", type="secondary")
    st.button("どちらでもない", on_click=handle_answer, args=(current_q_num, 3), key=f"btn_3_{current_q_num}", type="secondary")
    st.button("ややそう思う", on_click=handle_answer, args=(current_q_num, 4), key=f"btn_4_{current_q_num}", type="secondary")
    st.button("強くそう思う", on_click=handle_answer, args=(current_q_num, 5), key=f"btn_5_{current_q_num}", type="secondary")

# --- 3. 処理・完了画面 ---
elif st.session_state.step == "processing":
    with st.spinner("AIがあなた専用の極秘レポートを執筆しています...（約10〜20秒）"):
        success = save_to_spreadsheet()
        
    if success:
        st.session_state.step = "done"
        st.rerun()

elif st.session_state.step == "done":
    st.success("解析と極秘レポートの作成が完了しました！")
    
    # ---------------------------------------------------------
    # 極秘レポートの豪華な表示エリア
    # ---------------------------------------------------------
    if "secret_report" in st.session_state and st.session_state.secret_report:
        st.markdown("""
        <div style="padding: 1.5rem; background-color: #FFFCF9; border: 2px solid #FCEADE; border-radius: 12px; margin-bottom: 2rem; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);">
        """, unsafe_allow_html=True)
        
        # AIが生成したレポート本体を表示
        st.markdown(st.session_state.secret_report)
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ レポートの表示に時間がかかっています。データは正常に保存されました。")

    # ---------------------------------------------------------
    # LINEへの誘導ボタン
    # ---------------------------------------------------------
    st.markdown("<h4 style='text-align: center; font-weight: bold;'>▼ 日々の最適化アクションを受け取る ▼</h4>", unsafe_allow_html=True)
    
    # 本番LINE URLの直接埋め込み
    st.link_button("LINEに戻る", "https://lin.ee/FrawIyY", type="primary")
    
    st.info("このウィンドウは閉じて構いません。レポートはスクリーンショット等で保存することをお勧めします。")
