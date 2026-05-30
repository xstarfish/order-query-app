import streamlit as st
import requests
import re
import pandas as pd

# ------------------- 从 st.secrets 读取敏感配置 -------------------
FILE_ID = st.secrets["FILE_ID"]
SCRIPT_ID = st.secrets["SCRIPT_ID"]
TOKEN = st.secrets["TOKEN"]
# ---------------------------------------------------------------

def call_wps_script(func_name):
    url = f"https://www.kdocs.cn/api/v3/ide/file/{FILE_ID}/script/{SCRIPT_ID}/sync_task"
    headers = {
        "Content-Type": "application/json",
        "AirScript-Token": TOKEN
    }
    payload = {
        "Context": {
            "argv": {
                "funcName": func_name,
                "args": []
            }
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"API 调用失败：{resp.status_code}")
            return None
    except Exception as e:
        st.error(f"网络错误：{e}")
        return None

def extract_sf_numbers(text):
    pattern = r'\bSF[A-Z0-9]+\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return [m.upper() for m in matches]

def get_existing_numbers():
    """从WPS表格F列获取所有已有单号"""
    result = call_wps_script("get_all_tracking_numbers")
    if result and "data" in result and "result" in result["data"]:
        return result["data"]["result"]
    else:
        return []

def main_query(auto_text, manual_text):
    auto_numbers = extract_sf_numbers(auto_text) if auto_text else []
    manual_numbers = [n.strip().upper() for n in manual_text.splitlines() if n.strip()] if manual_text else []
    all_numbers = list(dict.fromkeys(auto_numbers + manual_numbers))
    if not all_numbers:
        return [], []
    existing = get_existing_numbers()
    missing = [n for n in all_numbers if n not in existing]
    return all_numbers, missing

# ------------------- Streamlit UI -------------------
st.set_page_config(page_title="订单入库查询", layout="centered")
st.title("📦 订单入库状态查询")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    auto_input = st.text_area("📋 从报单文本中自动提取 SF 单号", height=250,
                              placeholder="粘贴包含 SF 单号的报单文本...")
with col2:
    manual_input = st.text_area("✍️ 手动输入单号（换行分隔）", height=250,
                                placeholder="SF8888888888888\nYT6666666666666\n12345678")

if st.button("🔍 开始查询", type="primary"):
    if not auto_input and not manual_input:
        st.warning("请至少填写一个区域的单号")
    else:
        with st.spinner("正在查询，请稍候..."):
            all_nums, missing = main_query(auto_input, manual_input)
        if not all_nums:
            st.warning("未提取到任何有效单号")
        else:
            st.success(f"共查询 **{len(all_nums)}** 个单号，其中 **{len(missing)}** 个未入库")
            if missing:
                st.subheader("❌ 未入库单号列表")
                # 使用 code 块，自带复制按钮（右上角）
                st.code("\n".join(missing), language="text")
            else:
                st.balloons()
                st.info("🎉 所有单号均已入库！")
