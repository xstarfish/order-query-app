import streamlit as st
import requests
import re

# ------------------- 配置 -------------------
FILE_ID = st.secrets["FILE_ID"]
SCRIPT_ID = st.secrets["SCRIPT_ID"]
TOKEN = st.secrets["TOKEN"]
# ------------------------------------------

def call_wps_script(func_name):
    url = f"https://www.kdocs.cn/api/v3/ide/file/{FILE_ID}/script/{SCRIPT_ID}/sync_task"
    headers = {"Content-Type": "application/json", "AirScript-Token": TOKEN}
    payload = {"Context": {"argv": {"funcName": func_name, "args": []}}}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        st.error(f"网络错误：{e}")
        return None

def extract_tracking_numbers(text):
    pattern = r'\b(?:SF|JD|YT|JT|ZT|DPK|DPL|ZTO|YTO)[A-Z0-9]+\b'
    return re.findall(pattern, text, re.IGNORECASE)

def get_existing_numbers():
    result = call_wps_script("get_all_tracking_numbers")
    if result and "data" in result and "result" in result["data"]:
        return result["data"]["result"]
    return []

def main_query(auto_text, manual_text):
    auto_numbers = [n.upper() for n in extract_tracking_numbers(auto_text)] if auto_text else []
    manual_numbers = [n.strip().upper() for n in manual_text.splitlines() if n.strip()] if manual_text else []
    all_numbers = list(dict.fromkeys(auto_numbers + manual_numbers))
    if not all_numbers:
        return [], []
    existing = get_existing_numbers()
    missing = [n for n in all_numbers if n not in existing]
    return all_numbers, missing

# ------------------- UI -------------------
st.set_page_config(page_title="订单入库查询", layout="centered")
st.title("📦 订单入库状态查询")
st.markdown("---")

# 用于控制输入框是否重置的 key
if "reset_flag" not in st.session_state:
    st.session_state.reset_flag = False

# 定义输入框区域的占位符
input_placeholder = st.empty()

def render_inputs():
    """渲染两个输入框，使用唯一的 key 以保证每次重置时刷新"""
    col1, col2 = st.columns(2)
    with col1:
        st.text_area(
            "📋 自动提取快递单号（SF/JD/YT/JT/ZT/DPK/DPL/ZTO/YTO）",
            height=250,
            placeholder="粘贴报单文本...",
            key=f"auto_input_{st.session_state.reset_flag}"
        )
    with col2:
        st.text_area(
            "✍️ 手动输入单号（换行分隔）",
            height=250,
            placeholder="SF...\nYT...\n每行一个",
            key=f"manual_input_{st.session_state.reset_flag}"
        )

# 初始渲染
with input_placeholder.container():
    render_inputs()

# 按钮行
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🔍 开始查询", type="primary"):
        # 根据当前 reset_flag 获取对应的输入框值
        auto_text = st.session_state.get(f"auto_input_{st.session_state.reset_flag}", "")
        manual_text = st.session_state.get(f"manual_input_{st.session_state.reset_flag}", "")
        if not auto_text and not manual_text:
            st.warning("请至少填写一个区域的单号")
        else:
            with st.spinner("查询中..."):
                all_nums, missing = main_query(auto_text, manual_text)
            if not all_nums:
                st.warning("未提取到有效单号")
            else:
                st.success(f"共 {len(all_nums)} 个单号，{len(missing)} 个未入库")
                if missing:
                    st.subheader("❌ 未入库单号列表")
                    st.code("\n".join(missing), language="text")
                else:
                    st.balloons()
                    st.info("🎉 所有单号均已入库！")

with col_btn2:
    if st.button("🔄 重置"):
        # 改变 reset_flag → 强制重新创建输入框（旧输入框被销毁，新输入框为空）
        st.session_state.reset_flag = not st.session_state.reset_flag
        st.rerun()   # 立即刷新页面，重新渲染输入框区域
