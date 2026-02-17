import streamlit as st
import datetime
import statistics
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

    /* 【絶対遵守3】LINEリンクボタンを強制的にLINEカラー（#06C755）にする強力なCSS */
    div[data-testid="stLinkButton"] > a {
        background-color: #06C755 !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        /* スマホ向けに押しやすくするためのレイアウト調整（既存の良質なUIを維持） */
        width: 100% !important;
        height: 60px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 12px !important;
        font-size: 18px !important;
        text-decoration: none !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1) !important;
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
# ロジック・コールバック関数
# ==========================================
def start_test(user_id, dob_str, btime, gender):
    """基本情報の入力完了・バリデーション・テスト開始"""
    if not user_id:
        st.error("User_IDを入力してください。")
        return
    
    # 生年月日のチェック
    if not dob_str.isdigit() or len(dob_str) != 8:
        st.error("⚠️ 生年月日は8桁の半角数字で入力してください（例：19961229）")
        return
    
    # 実在する日付かどうかのチェック ＋ 年代の範囲チェック
    try:
        valid_date = datetime.datetime.strptime(dob_str, "%Y%m%d")
        
        # 【追加】未来の日付や古すぎる日付（1111年など）を弾く処理
        current_year = datetime.date.today().year
        if not (1900 <= valid_date.year <= current_year):
            st.error(f"⚠️ 正しい年代の生年月日を入力してください（1900年〜{current_year}年）")
            return
            
        formatted_dob = valid_date.strftime("%Y/%m/%d")
    except ValueError:
        st.error("⚠️ 存在しない日付です。正しい生年月日を入力してください。")
        return

    st.session_state.user_data = {
        "User_ID": user_id,
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
        
        # 分散が小さすぎる（適当に真ん中ばかり押している等）場合は50問に延長
        if variance < 0.8: 
            st.session_state.max_q = 50
        else:
            # 精度クリアとみなし終了
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
        
        # 逆転項目の場合は数値を反転させる（5->1, 4->2, 3->3, 2->4, 1->5）
        actual_val = 6 - val if is_reverse else val
        
        scores[trait] += actual_val
        counts[trait] += 1
        
    # 平均値を算出
    for t in scores:
        scores[t] = round(scores[t] / counts[t], 1) if counts[t] > 0 else 3.0
    return scores

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
        
        # スコア計算
        scores = calculate_scores()
        
        # 1行分のデータを作成
        ud = st.session_state.user_data
        row_data = [
            ud["User_ID"],          # User_ID
            "",                     # Stripe_ID (空白)
            "",                     # LINE_ID (空白)
            ud["DOB"],              # 生年月日 (YYYY/MM/DD)
            ud["Birth_Time"],       # 出生時間 (空白許容)
            ud["Gender"],           # 性別
            "", "", "", "", "", ""  # 占い用データ枠（日干支,天中殺,主星,初年,中年,晩年）として6個の空白を追加
        ]
        
        # Q1〜Q50の回答 (未回答部分は空白)
        for i in range(1, 51):
            row_data.append(st.session_state.answers.get(i, ""))
            
        # O, C, E, A, N Scores
        row_data.extend([scores["O"], scores["C"], scores["E"], scores["A"], scores["N"]])
        
        # 課金開始日, 極秘ライブラリ(恋愛), 極秘ライブラリ(適職), 残回数
        today_str = datetime.date.today().strftime("%Y/%m/%d")
        row_data.extend([today_str, "FALSE", "FALSE", 3])
        
        # 書き込み
        sheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"データ保存中にエラーが発生しました: {e}")
        return False

# ==========================================
# UI レンダリング
# ==========================================

# --- 1. 基本情報入力画面 ---
if st.session_state.step == "user_info":
    st.title("【完全版】プレミアム裏ステータス診断")
    st.write("数億通りのAI×宿命アルゴリズムで、あなたの深層心理と本来のポテンシャルを完全解析します。まずは基本プロフィールをご入力ください。")
    
    with st.form("info_form"):
        user_id = st.text_input("User_ID（システム用）")
        
        # 生年月日の8桁数字入力（プレースホルダー維持）
        st.markdown("<p style='font-weight: 900; margin-bottom: 0;'>生年月日（半角数字8桁）</p>", unsafe_allow_html=True)
        dob_input = st.text_input("生年月日", max_chars=8, placeholder="例 19961229", label_visibility="collapsed")
        
        # 出生時間のプレースホルダー維持
        btime = st.text_input("出生時間（任意・不明なら空欄のまま）", value="", placeholder="例 23:16")
        
        # 性別入力のUI変更（バグ解消と1タップ化）
        gender = st.radio("性別", ["男性", "女性", "その他", "回答しない"], horizontal=True)
        
        # 送信ボタン
        submitted = st.form_submit_button("適性テストを開始する", type="primary")
        if submitted:
            # パート2で定義したstart_test関数を呼び出し（内部で【絶対遵守2】の厳格なバリデーション実行）
            start_test(user_id, dob_input, btime, gender)
            
            # エラーに引っかからず、testステップに進んだ場合のみ再描画（エラーメッセージを残すための必須処理）
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
    
    # 1つ前に戻るボタンをプログレスバーのすぐ下（質問文の上）に配置
    if current_q_num > 1:
        st.button("◀ 前の質問に戻る", on_click=go_back, key=f"btn_back_{current_q_num}", type="secondary")
    
    # 質問表示
    question_data = QUESTIONS[current_q_num - 1]
    st.markdown(f"<div class='question-title'>{question_data['text']}</div>", unsafe_allow_html=True)
    
    st.write("---")
    
    # スマホで押し間違いを防ぐため、縦並びのUDボタンを配置
    # ボタンを押した瞬間に handle_answer がコールバックされ、画面が瞬時に切り替わる
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
    st.markdown("### 下のボタンからLINEに戻り、結果をお受け取りください。")
    
    # 【絶対遵守1】本番LINE URLの直接埋め込み（dummy禁止）
    st.link_button("LINEに戻って結果を受け取る", "https://lin.ee/FrawIyY", type="primary")
    
    st.info("このウィンドウは閉じて構いません。")
