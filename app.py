import streamlit as st
import requests
import subprocess
import os
import sys
import io
import matplotlib.pyplot as plt

# ==========================================
# 1. 页面基础配置
# ==========================================
st.set_page_config(page_title="智能数据分析师", page_icon="🤖", layout="wide")

# ==========================================
# 2. 智能中文字体配置 (兼容本地和云端)
# ==========================================
# 本地 Windows 有 SimHei，云端 Linux 没有。
# 用 try-except 防止云端报错，同时用代码确保画出的图不显示方块。
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass

# ==========================================
# 3. 侧边栏配置 (用户输入 API Key)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/artificial-intelligence.png", width=80)
    st.title("环境配置")
    st.markdown("---")
    api_key = st.text_input("🔑 DeepSeek API Key", type="password", help="请填入你的 API Key")
    st.markdown("---")
    st.info("💡 **使用指南**\n1. 填入 API Key\n2. 输入 CSV 数据与需求\n3. 点击生成，Agent 将自动编写并执行代码。")

# ==========================================
# 4. 核心 Agent 函数 (调用硅基流动 API)
# ==========================================
def generate_code_from_llm(user_request: str, csv_data: str, api_key: str, previous_error: str = "") -> str:
    prompt = f"""
    你是一个专业的数据分析师。请使用 pandas 和 matplotlib 库编写一段 Python 代码。
    
    已知数据如下：
    {csv_data}
    
    要求：
    1. 请将数据直接写在代码里，使用 io.StringIO 读取，不要去读取外部文件。
    2. 数据中的列名严格照抄。
    3. 完成以下任务：{user_request}
    4. 将画好的图表保存为 'output_plot.png'。
    5. 不要输出任何 markdown 标记，只输出纯 Python 代码。
    6. **重要**：环境已经预设了 matplotlib 中文字体，代码中不要再设置 plt.rcParams 字体，直接画图即可。
    7. 如果 x 轴是日期，务必先转为字符串格式，再传给 plt.plot()。
    8. 请确保导入所有需要的库（import io, pandas as pd, matplotlib.pyplot as plt）。
    """
    if previous_error:
        prompt += f"\n\n注意：你上一次生成的代码报错了，报错信息如下：\n{previous_error}\n请修复这个错误，重新生成完整的代码。"

    if not api_key:
        return "错误：请在左侧输入 API Key"

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-flash", 
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        code = response.json()["choices"][0]["message"]["content"]
        return code.replace("```python", "").replace("```", "").strip()
    except Exception as e:
        return f"调用 API 失败: {e}"

def execute_generated_code(code: str):
    temp_file = "temp_analysis.py"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(code)
    
    result = subprocess.run([sys.executable, temp_file], capture_output=True, text=True, timeout=30)
    
    if os.path.exists(temp_file):
        os.remove(temp_file)
    return result

# ==========================================
# 5. 主界面布局
# ==========================================
st.title("🤖 智能数据分析师 Agent")
st.markdown("基于 **DeepSeek大模型** 的自动化数据洞察工具")
st.markdown("---")

col1, col2 = st.columns([1.2, 1])

with col1:
    st.subheader("📁 1. 数据输入")
    uploaded_file = st.file_uploader("上传 CSV 文件", type=["csv"])
    default_data = """Department,Q1_Budget,Q2_Budget
研发部,50000,65000
市场部,30000,45000
销售部,40000,35000
人事部,15000,18000"""
    csv_text = st.text_area("或直接粘贴 CSV 文本", value=default_data, height=200)

with col2:
    st.subheader("💬 2. 分析需求")
    user_request = st.text_area("告诉 Agent 你想怎么分析", value="帮我用柱状图对比一下各个部门的 Q1 和 Q2 预算。", height=130)
    st.write("")
    start_btn = st.button("🚀 开始分析与生成图表", type="primary")

# ==========================================
# 6. 执行逻辑与结果展示
# ==========================================
if start_btn:
    if not api_key:
        st.error("❌ 请先在左侧输入硅基流动 API Key！")
    elif not csv_text.strip() and uploaded_file is None:
        st.error("❌ 数据不能为空！")
    else:
        st.markdown("---")
        st.subheader("⚙️ Agent 运行过程")
        tab1, tab2, tab3 = st.tabs(["📝 运行日志", "💻 生成代码", "📈 图表结果"])
        
        csv_data = uploaded_file.getvalue().decode("utf-8") if uploaded_file else csv_text
        
        with tab1:
            log_placeholder = st.empty()
            logs = ""
            def add_log(msg):
                global logs
                logs += msg + "\n"
                log_placeholder.markdown(f"```text\n{logs}\n```")
            
            max_retries = 2
            error_msg = ""
            success = False
            
            for attempt in range(max_retries + 1):
                add_log(f"--- 第 {attempt + 1} 次尝试 ---")
                add_log("正在请求云端大模型生成代码...")
                
                generated_code = generate_code_from_llm(user_request, csv_data, api_key, error_msg)
                
                with tab2:
                    st.code(generated_code, language="python")
                
                add_log("正在执行代码...")
                result = execute_generated_code(generated_code)
                
                if result.returncode == 0:
                    add_log("🎉 代码执行成功！")
                    success = True
                    break
                else:
                    add_log("❌ 代码执行报错，Agent 正在尝试自我修复...")
                    add_log(result.stderr)
                    error_msg = result.stderr
            
            with tab3:
                if success and os.path.exists("output_plot.png"):
                    st.success("✅ 分析成功！")
                    st.image("output_plot.png", use_column_width=True)
                    with open("output_plot.png", "rb") as file:
                        st.download_button("📥 下载图表", data=file, file_name="result.png", mime="image/png")
                elif success:
                    st.warning("代码执行成功，但未生成图表。")
                else:
                    st.error("❌ 代码执行失败，请查看日志。")