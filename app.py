import streamlit as st
import datetime
import statistics
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 必要なモジュールのインポート
import streamlit.components.v1 as components
import urllib.parse
import requests

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(
    page_title="性格適性診断 | オンボーディング",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

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
    """基本情報の入力完了・バリデーション・テスト開始（LIFF連携対応）"""
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
        "User_ID": line_name,    # 自動取得したLINE名
        "LINE_ID": line_id,      # 自動取得したLINE_ID
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
    """Googleスプレッドシートへの書き込み処理"""
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
        
        # 算命学パラメータの自動計算（五鼠遁と堅牢な時間パース対応済）
        ud = st.session_state.user_data
        y, m, d = map(int, ud["DOB"].split('/'))
        sanmeigaku = calculate_sanmeigaku(y, m, d, ud["Birth_Time"])
        
        # スプレッドシートの書き込み枠（8枠完全対応 + LINE ID統合）
        row_data = [
            ud["User_ID"],          # User_ID (自動取得したLINE名)
            "",                     # Stripe_ID (空白)
            ud["LINE_ID"],          # LINE_ID (自動取得したLINE_ID)
            ud["DOB"],              # 生年月日 (YYYY/MM/DD)
            ud["Birth_Time"],       # 出生時間 (空白許容)
            ud["Gender"],           # 性別
            sanmeigaku["日干支"],    # 占い枠1
            sanmeigaku["天中殺"],    # 占い枠2
            sanmeigaku["主星"],      # 占い枠3
            sanmeigaku["初年"],      # 占い枠4
            sanmeigaku["中年"],      # 占い枠5
            sanmeigaku["晩年"],      # 占い枠6
            sanmeigaku["時干支"],    # 占い枠7（動的変動）
            sanmeigaku["最晩年"]     # 占い枠8（動的変動）
        ]
        
        # Q1〜Q50の回答 (未回答部分は空白)
        for i in range(1, 51):
            row_data.append(st.session_state.answers.get(i, ""))
            
        # O, C, E, A, N Scores
        row_data.extend([scores["O"], scores["C"], scores["E"], scores["A"], scores["N"]])
        
        # 課金開始日, 極秘ライブラリ解放権限, 残回数
        today_str = datetime.date.today().strftime("%Y/%m/%d")
        row_data.extend([today_str, "FALSE", "FALSE", 3])
        
        # 書き込み
        sheet.append_row(row_data)
        
        # 完了時のLINEへのダイレクトプッシュ送信
        send_line_result(ud["LINE_ID"], sanmeigaku, scores)
        
        return True
        
    except Exception as e:
        st.error(f"データ保存中にエラーが発生しました: {e}")
        return False

# ==========================================
# UI レンダリング
# ==========================================

# 【修正：無限ループ防止・パラメータ取得ロジック】
def get_params_robust():
    """新旧バージョン・型違いに対応したパラメータ取得"""
    params = {}
    try:
        # 新しいAPI (st.query_params)
        if hasattr(st.query_params, "to_dict"):
            params = st.query_params.to_dict()
        else:
            params = dict(st.query_params)
    except:
        try:
            # 古いAPI
            params = st.experimental_get_query_params()
        except:
            pass
    return params

# パラメータ取得
raw_params = get_params_robust()

# 値抽出（リスト・文字列両対応）
p_line_id = raw_params.get("line_id", "")
if isinstance(p_line_id, list) and len(p_line_id) > 0:
    p_line_id = p_line_id[0]

p_line_name = raw_params.get("line_name", "")
if isinstance(p_line_name, list) and len(p_line_name) > 0:
    p_line_name = p_line_name[0]

# セッション保存（IDさえあれば許可・名前は任意）
if "line_id" not in st.session_state and p_line_id:
    st.session_state.line_id = p_line_id
    # 名前が取れていれば保存、なければゲスト扱い
    if p_line_name:
        st.session_state.line_name = urllib.parse.unquote(p_line_name)
    else:
        st.session_state.line_name = "ゲスト"
    st.rerun()

# まだセッションに無い場合 -> LIFF認証へ
if "line_id" not in st.session_state:
    app_url = "https://take-plan-ai-gwrexhn6yztk5swygdm4bn.streamlit.app/"
    liff_id = "2009158681-7tv2nwIm"
    
    # ループ防止機能付きLIFFコード
    liff_js_template = """
    <div id="loader" style="text-align:center; font-family:sans-serif; color:#666; margin-top: 20px;">
        🔄 認証状況を確認中...
    </div>
    
    <div id="start_btn_container" style="display:none; justify-content:center; align-items:center; margin-top: 20px;">
        <a id="start_link" href="#" target="_top" style="display:block; width:90%; text-align:center; padding: 25px 0; background-color: #06C755; color: white; text-decoration: none; border-radius: 12px; font-size: 20px; font-weight: bold; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
            🚀 診断をスタートする
        </a>
        <p style="text-align:center; font-size:12px; color:#999; margin-top:10px;">※自動で始まらない場合はタップしてください</p>
    </div>

    <div id="login_btn_container" style="display:none; justify-content:center; align-items:center; margin-top: 20px;">
         <button id="manual_login_btn" style="width:90%; padding: 20px 0; background-color: #06C755; color: white; border: none; border-radius: 12px; font-size: 18px; font-weight: bold;">
            LINEでログインして開始
         </button>
    </div>
    
    <div id="debug_msg" style="color:red; font-size:10px; text-align:center; margin-top:20px;"></div>

    <script charset="utf-8" src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            // 【重要】すでにURLにline_idがある場合、LIFF処理をスキップしてループを止める
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('line_id')) {
                document.getElementById('loader').style.display = 'none';
                document.getElementById('start_btn_container').style.display = 'flex';
                // 現在のURLを再読み込みするリンクを設定
                document.getElementById('start_link').href = window.location.href;
                return; // ここで処理終了（無限ループ回避）
            }

            // URLにIDがない場合のみ、LIFF初期化を行う
            liff.init({ liffId: "LIFF_ID_VAL" }).then(() => {
                if (liff.isLoggedIn()) {
                    liff.getProfile().then(profile => {
                        const url = new URL("APP_URL_VAL");
                        url.searchParams.set('line_id', profile.userId);
                        url.searchParams.set('line_name', encodeURIComponent(profile.displayName));
                        
                        // リダイレクト実行
                        window.location.replace(url.toString());
                        
                    }).catch(err => {
                        document.getElementById('debug_msg').innerText = "Profile Error: " + err;
                    });
                } else {
                    // 未ログイン時
                    document.getElementById('loader').style.display = 'none';
                    document.getElementById('login_btn_container').style.display = 'flex';
                    document.getElementById('manual_login_btn').onclick = function() {
                        liff.login();
                    };
                }
            }).catch(err => {
                document.getElementById('debug_msg').innerText = "LIFF Init Error: " + err;
            });
        });
    </script>
    """
    
    liff_js = liff_js_template.replace("LIFF_ID_VAL", liff_id).replace("APP_URL_VAL", app_url)
    components.html(liff_js, height=350)
    st.stop()


# --- 1. 基本情報入力画面 ---
if st.session_state.step == "user_info":
    
    # ようこそメッセージ（LINE名表示）
    st.markdown(f"### ようこそ、{st.session_state.line_name} さん！")
    
    st.title("【完全版】プレミアム裏ステータス診断")
    st.write("数億通りのAI×宿命アルゴリズムで、あなたの深層心理と本来のポテンシャルを完全解析します。まずは基本プロフィールをご入力ください。")
    
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
            # 自動取得したLINE情報を渡して開始
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
    with st.spinner("AIがあなたの深層心理を解析し、データベースに保存しています..."):
        success = save_to_spreadsheet()
        
    if success:
        st.session_state.step = "done"
        st.rerun()

elif st.session_state.step == "done":
    st.success("解析が完了しました。")
    st.markdown("### LINEに診断結果をお送りしました！<br>下のボタンからLINEにお戻りください。", unsafe_allow_html=True)
    
    # 本番LINE URLの直接埋め込み
    st.link_button("LINEに戻って結果を受け取る", "https://lin.ee/FrawIyY", type="primary")
    
    st.info("このウィンドウは閉じて構いません。")
