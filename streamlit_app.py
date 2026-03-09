import streamlit as st
import requests
import json
import time

# ==========================================
# 🛑 导演请注意：这里需要换成你【创意SOP】应用专属的 API Key
# ==========================================
DIFY_IDEA_API_KEY = "app-L13a4R0HM4ngFqs2jdYDqQ5X"
DIFY_WORKFLOW_URL = "https://api.dify.ai/v1/workflows/run"
DIFY_UPLOAD_URL = "https://api.dify.ai/v1/files/upload"

# 页面外观设置
st.set_page_config(page_title="AI短剧创意提案引擎", page_icon="💡", layout="wide")

# --- 记忆芯片初始化 ---
keys_to_init = ["idea_result", "theme_input", "extra_req", "ref_link"]
for key in keys_to_init:
    if key not in st.session_state:
        st.session_state[key] = ""
if "file_key" not in st.session_state:
    st.session_state.file_key = 0 # 专门用来重置文件上传框的变量

# 🧹 一键清空回调函数（瞬间清空所有框，包括文件）
def clear_form():
    for key in keys_to_init:
        st.session_state[key] = ""
    st.session_state.file_key += 1 # 强行改变上传框的ID，让它瞬间重置

# ================= UI 布局与标题 =================
col_title, col_btn = st.columns([5, 1])
with col_title:
    st.title("💡 AI短剧创意与三幕剧提案引擎【V-Team】")
    st.markdown("⚠️ **机密系统：仅供TT-909 WORK项目组内部使用，请勿外传。**")
with col_btn:
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    st.button("🗑️ 一键清空", on_click=clear_form, use_container_width=True, key="top_clear_btn")

st.subheader("📥 请输入创意物料 (多项目选填，给得越多创意越准)")

col1, col2 = st.columns([2, 1])

with col1:
    # 完美绑定 session_state
    theme_input = st.text_area("🎬 题材/灵感方向 (theme_input):", key="theme_input", placeholder="例如：帮我写一个吸血鬼霸总和狼人保镖的故事，要有强烈的权力反转...", height=100)
    extra_requirements = st.text_area("📝 附加需求 (extra_requirements):", key="extra_req", placeholder="例如：结局必须是悲剧，男主要有病娇属性。", height=100)

with col2:
    reference_link = st.text_input("🔗 对标视频链接 (reference_link):", key="ref_link", placeholder="例如：https://www.tiktok.com/...")
    # 文件上传框的 key 是动态的，清空时数字+1，旧文件瞬间被顶号
    uploaded_file = st.file_uploader("📂 上传参考视频/文件 (file_upload):", key=f"uploader_{st.session_state.file_key}", type=["mp4", "mov", "avi", "pdf", "docx", "txt"])

generate_btn = st.button("🚀 三幕式短剧创意开启生成！")

# 提取区占位
top_extraction_area = st.empty()

if generate_btn:
    # 校验：至少得给点东西
    if not any([theme_input.strip(), reference_link.strip(), extra_requirements.strip(), uploaded_file is not None]):
        st.warning("导演，好歹给点题材、链接或者传个视频呀！不能空手套白狼！")
    else:
        st.session_state.idea_result = ""
        top_extraction_area.empty() 
        
        file_payload = None
        
        # ==========================================
        # 🌟 第一步：如果传了视频/文件，先把它发射到 Dify 服务器换取 ID
        # ==========================================
        if uploaded_file is not None:
            with st.spinner("⏳ 正在高速上传视频/文件至云端分析引擎..."):
                upload_headers = {"Authorization": f"Bearer {DIFY_IDEA_API_KEY}"}
                files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {'user': 'Vanessa-Idea-Team'}
                
                upload_res = requests.post(DIFY_UPLOAD_URL, headers=upload_headers, files=files, data=data)
                
                if upload_res.status_code in [200, 201]:
                    file_id = upload_res.json().get('id')
                    # 智能识别文件类型
                    file_type = "document"
                    if "video" in uploaded_file.type: file_type = "video"
                    elif "image" in uploaded_file.type: file_type = "image"
                    elif "audio" in uploaded_file.type: file_type = "audio"
                    
                    # 组装 Dify 需要的特殊文件格式
                    file_payload = {
                        "transfer_method": "local_file",
                        "upload_file_id": file_id,
                        "type": file_type
                    }
                    st.success("✅ 视频/文件上传成功！正在进入创意推演...")
                else:
                    st.error(f"❌ 文件上传失败，请检查网络或 API Key: {upload_res.text}")
                    st.stop() # 传文件失败就立即停止

        # ==========================================
        # 🌟 第二步：带着文件 ID 和文字需求，启动大模型工作流
        # ==========================================
        with st.spinner("🧠 创意大脑已全面接管，正在疯狂生成S级提案中..."):
            workflow_headers = {
                "Authorization": f"Bearer {DIFY_IDEA_API_KEY}",
                "Content-Type": "application/json"
            }
            
            inputs_data = {
                "theme_input": theme_input,
                "reference_link": reference_link,
                "extra_requirements": extra_requirements
            }
            
            if file_payload:
                inputs_data["file_upload"] = file_payload
                
            payload = {
                "inputs": inputs_data,
                "response_mode": "streaming",
                "user": "Vanessa-Idea-Team" 
            }
            
            try:
                # 4小时超长超时保护
                response = requests.post(DIFY_WORKFLOW_URL, headers=workflow_headers, json=payload, stream=True, timeout=(300, 14400))
                response.raise_for_status()
                
                st.markdown("### 📜 提案实时生成中...")
                st.divider()
                
                result_box = st.empty()
                heartbeat_box = st.empty() 
                full_result = ""
                workflow_finished_normally = False
                
                # ⏱️ 渲染节流阀时间戳 (防网页假死核心)
                last_update_time = time.time()
                
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data:'):
                            data_str = decoded_line[5:].strip()
                            try:
                                json_data = json.loads(data_str)
                                event_type = json_data.get('event')
                                
                                # 📡 节点雷达
                                if event_type == 'node_started':
                                    node_title = json_data.get('data', {}).get('title', '未知节点')
                                    heartbeat_box.info(f"⚙️ Dify 底层节点运转中: 【{node_title}】... [时间: {time.strftime('%H:%M:%S')}]")
                                    continue
                                
                                # 💓 心跳防断网起搏器
                                elif event_type == 'ping':
                                    heartbeat_box.caption(f"💓 视频解析与推演中... [最近心跳: {time.strftime('%H:%M:%S')}]")
                                    continue
                                    
                                # 📝 文本块输出 (加入神级节流阀)
                                elif event_type == 'text_chunk':
                                    chunk = json_data.get('data', {}).get('text', '')
                                    full_result += chunk
                                    
                                    # 每隔 0.5 秒才刷新一次前端 UI，保护浏览器不崩溃！
                                    if time.time() - last_update_time > 0.5:
                                        result_box.markdown(full_result + " ▌")
                                        last_update_time = time.time()
                                
                                # ❌ 捕获后台报错
                                elif event_type == 'error':
                                    error_msg = json_data.get('message', '未知错误')
                                    st.error(f"❌ Dify 后台发生错误: {error_msg}")
                                    workflow_finished_normally = True
                                    break
                                    
                                # ✅ 完美结束
                                elif event_type == 'workflow_finished':
                                    heartbeat_box.empty() 
                                    result_box.markdown(full_result) # 结束时做一次完整的最终渲染
                                    st.session_state.idea_result = full_result
                                    workflow_finished_normally = True
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                                
                # 🚨 防静默断连报警
                if not workflow_finished_normally:
                    st.error("⚠️ 警告：连接被网络运营商或路由器异常切断！")
                    st.info("👉 Dify 后台可能仍在继续生成。请稍后前往 Dify 后台日志提取结果。")
                    if full_result:
                        st.session_state.idea_result = full_result
            
            # 🚨 专门捕获反向代理强制断开数据流的错误
            except requests.exceptions.ChunkedEncodingError:
                st.error("⚠️ 警告：数据流被服务器强制掐断！(通常是由于生成时间过长，代理断开了连接)。请去 Dify 后台拿结果！")
                if full_result:
                    st.session_state.idea_result = full_result
            except Exception as e:
                st.error(f"连接失败，可能是视频太大或请求超时: {e}")

# --- 完美一键复制区 ---
if st.session_state.idea_result:
    with top_extraction_area.container():
        st.success("✅ 创意提案已生成！直接点击下方代码框右上角的【两张纸】图标，一键复制进飞书吧！")
        st.markdown("👇 **Markdown 表格提取区**")
        st.code(st.session_state.idea_result, language="markdown")
        
        # 🌟 底部追加的“一键清空”按钮
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🗑️ 复制完毕？一键清空并准备下一次生成", on_click=clear_form, use_container_width=True, key="bottom_clear_btn")