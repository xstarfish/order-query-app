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
    pattern = r'\b(?:SF|JD|YT|JT|ZT|DPK|DPL|ZTO|YTO|KD)[A-Z0-9]+\b'
    return re.findall(pattern, text, re.IGNORECASE)

def norm(s) -> str:
    """规范化单号：去掉所有空白/全角空格/零宽字符，统一大写"""
    s = str(s)
    for ch in ("\u3000", " ", "\n", "\r", "\t", "\u200b", "\ufeff"):
        s = s.replace(ch, "")
    return s.upper()

def get_existing_numbers():
    """调用 WPS 宏，取回表格里已有的所有单号（兼容 dict / 裸 list 两种返回）"""
    result = call_wps_script("get_all_tracking_numbers")

    if not result or "data" not in result:
        st.error("读取表格失败：call_wps_script 无返回，请检查 WPS 宏是否已加载！")
        return []

    payload = result["data"].get("result")

    # 新版宏返回 {ok, book, sheet, lastRow, count, numbers}
    if isinstance(payload, dict):
        if not payload.get("ok"):
            st.error(f"宏返回异常：{payload.get('err')}")
            return []
        numbers = payload.get("numbers", [])
        st.caption(
            f"表格：{payload.get('book')} / {payload.get('sheet')} | "
            f"lastRow={payload.get('lastRow')} | 单号数={payload.get('count')}"
        )
        return numbers

    # 兼容旧版宏：直接返回 list
    if isinstance(payload, list):
        st.caption(f"⚠️ 宏为旧版，返回裸 list，长度={len(payload)}")
        return payload

    st.error(f"宏返回类型异常：{type(payload)} -> {payload!r}")
    return []

def main_query(auto_text, manual_text):
    auto_numbers = [n.upper() for n in extract_tracking_numbers(auto_text)] if auto_text else []
    manual_numbers = [n.strip().upper() for n in manual_text.splitlines() if n.strip()] if manual_text else []
    all_numbers = list(dict.fromkeys(auto_numbers + manual_numbers))
    if not all_numbers:
        return [], []

    existing = get_existing_numbers()
    if not existing:
        return all_numbers, all_numbers  # 读不到就当全部未入库，UI 会显示全部

    # ✅ 规范化集合比对
    existing_set = {norm(x) for x in existing}
    missing = [n for n in all_numbers if norm(n) not in existing_set]
    return all_numbers, missing

# ------------------- UI -------------------
st.set_page_config(page_title="订单入库查询", layout="centered")
st.title("📦 订单入库状态查询")
st.markdown("---")

if "reset_flag" not in st.session_state:
    st.session_state.reset_flag = False

input_placeholder = st.empty()

def render_inputs():
    col1, col2 = st.columns(2)
    with col1:
        st.text_area(
            "📋 自动提取快递单号（SF/JD/YT/JT/ZT/DPK/DPL/ZTO/YTO/KD）",
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

with input_placeholder.container():
    render_inputs()

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🔍 开始查询", type="primary"):
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
        st.session_state.reset_flag = not st.session_state.reset_flag
        st.rerun()
