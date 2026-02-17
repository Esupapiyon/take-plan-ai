import streamlit as st
import datetime
import statistics
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# ページ設定とCSS（スマホ最適化）
# ==========================================
st.set_page_config(
    page_title="性格適性診断 | オンボーディング",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ボタンや全体レイアウトをスマホで押しやすくするモダンCSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        margin-bottom: 10px;
        transition: 0.3s;
    }
    .stButton>button:active {
        background-color: #00C853 !important;
        color: white !important;
    }
    .question-title {
        font-size: 1.5rem;
        font-weight: 800;
        text-align: center;
        margin-top: 2rem;
        margin-bottom: 2rem;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CAT（適応型テスト）用 ダミー質問データ (50問)
# O: 開放性, C: 勤勉性, E: 外向性, A: 協調性, N: 神経症的傾向
# ==========================================
TRAITS = ["O", "C", "E", "A", "N"]
QUESTIONS = []
for i in range(1, 51):
    trait = TRAITS[(i - 1) % 5]
    QUESTIONS.append({
        "id": i,
        "text": f"質問 {i}：自分は「{trait}」に関する特徴が当てはまる方だと思う。（ダミー質問）",
        "trait": trait
    })

# ==========================================
# セッションステートの初期化
# ==========================================
if "step" not in st.session_state:
    st.session_state.step = "user_info" # user_info -> test -> done
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
def start_test(user_id, dob, btime, gender):
    """基本情報の入力完了・テスト開始"""
    if not user_id:
        st.error("User_IDを入力してください。")
        return
    
    st.session_state.user_data = {
        "User_ID": user_id,
        "DOB": dob.strftime("%Y/%m/%d"),
        "Birth_Time": btime.strftime("%H:%M"),
        "Gender": gender
    }
    st.session_state.step = "test"

def handle_answer(q_id, answer_value):
    """回答を保存し、次へ進む（CATロジック含む）"""
    st.session_state.answers[q_id] = answer_value
    
    # 【CATロジック】第30問目で回答の分散（矛盾）をチェック
    if st.session_state.current_q == 30:
        ans_values = list(st.session_state.answers.values())
        variance = statistics.variance(ans_values) if len(ans_values) > 1 else 0
        
        # 分散が小さすぎる（適当に真ん中ばかり押している等）場合は50問に延長
        if variance < 0.8: 
            st.session_state.max_q = 50
        else:
            # 精度95%以上とみなし終了
            finish_test()
            return

    # 最終問題に到達した場合
    if st.session_state.current_q >= st.session_state.max_q:
        finish_test()
    else:
        st.session_state.current_q += 1

def finish_test():
    """テスト終了処理・スプレッドシートへの書き込み"""
    st.session_state.step = "processing"
    
def calculate_scores():
    """Big5スコアの計算（モック）"""
    scores = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    counts = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    
    for q_id, val in st.session_state.answers.items():
        trait = QUESTIONS[q_id - 1]["trait"]
        scores[trait] += val
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
            ud["DOB"],              # 生年月日
            ud["Birth_Time"],       # 出生時間
            ud["Gender"]            # 性別
        ]
        
        # Q1〜Q50の回答 (未回答は空白)
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
    st.title("ようこそ！初期設定を始めましょう")
    st.write("精密な解析を行うため、まずはプロフィールをご入力ください。")
    
    with st.form("info_form"):
        user_id = st.text_input("User_ID（システム用）")
        dob = st.date_input("生年月日", min_value=datetime.date(1920, 1, 1), max_value=datetime.date.today())
        btime = st.time_input("出生時間（不明な場合は12:00のまま）", datetime.time(12, 0))
        gender = st.selectbox("性別", ["男性", "女性", "その他", "回答しない"])
        
        submitted = st.form_submit_button("適性テストを開始する", type="primary")
        if submitted:
            start_test(user_id, dob, btime, gender)
            st.rerun()

# --- 2. CAT テスト画面 (SPA・1画面1問) ---
elif st.session_state.step == "test":
    current_q_num = st.session_state.current_q
    max_q_num = st.session_state.max_q
    
    # プログレスバー
    progress_val = current_q_num / max_q_num
    st.progress(progress_val)
    st.caption(f"現在 {current_q_num} 問目 / (最大 {max_q_num} 問)")
    
    # 質問表示
    question_data = QUESTIONS[current_q_num - 1]
    st.markdown(f"<div class='question-title'>{question_data['text']}</div>", unsafe_allow_html=True)
    
    st.write("---")
    
    # スマホで押しやすいようにカラムでボタンを配置
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # ボタンを押した瞬間に handle_answer がコールバックされ、画面が瞬時に切り替わる
    with col1:
        st.button("全く\n違う", on_click=handle_answer, args=(current_q_num, 1), key=f"btn_1_{current_q_num}")
    with col2:
        st.button("やや\n違う", on_click=handle_answer, args=(current_q_num, 2), key=f"btn_2_{current_q_num}")
    with col3:
        st.button("どちらでも\nない", on_click=handle_answer, args=(current_q_num, 3), key=f"btn_3_{current_q_num}")
    with col4:
        st.button("やや\nそう思う", on_click=handle_answer, args=(current_q_num, 4), key=f"btn_4_{current_q_num}")
    with col5:
        st.button("強く\nそう思う", on_click=handle_answer, args=(current_q_num, 5), key=f"btn_5_{current_q_num}")

# --- 3. 処理・完了画面 ---
elif st.session_state.step == "processing":
    with st.spinner("AIがあなたの深層心理を解析し、データベースに保存しています..."):
        success = save_to_spreadsheet()
        
    if success:
        st.session_state.step = "done"
        st.rerun()

elif st.session_state.step == "done":
    st.success("解析が完了しました。")
    st.markdown("### LINEに戻って結果をお待ちください。")
    st.info("このウィンドウは閉じて構いません。")
