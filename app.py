
import streamlit as st
from dotenv import load_dotenv
from agent import SupportAgent

load_dotenv()

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="AI Customer Support Agent",
    page_icon="🛟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top left, #dbeafe 0%, transparent 35%),
        radial-gradient(circle at bottom right, #ede9fe 0%, transparent 35%),
        linear-gradient(135deg, #f8fafc, #eef2ff);
}

/* Main content */
.block-container {
    max-width: 1100px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Header */
.hero {
    background: linear-gradient(120deg, #4338ca, #7c3aed, #db2777);
    padding: 30px;
    border-radius: 22px;
    color: white;
    text-align: center;
    box-shadow: 0 12px 35px rgba(79, 70, 229, 0.25);
    margin-bottom: 25px;
}

.hero h1 {
    color: white;
    font-size: 34px;
    font-weight: 800;
    margin-bottom: 8px;
}

.hero p {
    color: #f3e8ff;
    font-size: 15px;
    margin: 0;
}

/* Status card */
.status-card {
    background: white;
    padding: 15px 20px;
    border-radius: 15px;
    border-left: 5px solid #10b981;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    margin-bottom: 20px;
    color: #334155;
    font-weight: 600;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    padding: 15px;
    box-shadow: 0 5px 15px rgba(15, 23, 42, 0.04);
    margin-bottom: 12px;
}

/* Chat input */
[data-testid="stChatInput"] {
    border: 2px solid #c4b5fd;
    border-radius: 18px;
    background: white;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #eef2ff, #fdf2f8);
}

.sidebar-title {
    color: #4338ca;
    font-size: 23px;
    font-weight: 800;
}

.sidebar-card {
    background: white;
    padding: 15px;
    border-radius: 14px;
    margin: 12px 0;
    border: 1px solid #ddd6fe;
    color: #334155;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #4f46e5, #9333ea);
    color: white;
    font-weight: 700;
    border: none;
    border-radius: 12px;
    padding: 10px 18px;
    transition: 0.2s;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #3730a3, #7e22ce);
    color: white;
    transform: translateY(-2px);
}

/* Tool expander */
[data-testid="stExpander"] {
    background: #f5f3ff;
    border: 1px solid #c4b5fd;
    border-radius: 14px;
}

/* Captions */
.small-caption {
    color: #64748b;
    font-size: 12px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown('<div class="sidebar-title">🛟 Support Hub</div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div class="sidebar-card">
        <h4>✨ Your AI Assistant</h4>
        <p>Get quick answers, track orders, explore FAQs and create support tickets.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 💡 Try asking")

    examples = [
        "📦 Where is order ORD-1001?",
        "↩️ What is your return policy?",
        "🛠️ My keyboard arrived broken",
        "🎫 Create a support ticket"
    ]

    for example in examples:
        st.markdown(f"- {example}")

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.history = []
        st.session_state.display = []
        st.rerun()

    st.markdown("""
    <div class="small-caption">
        Powered by Python + Groq LLM<br>
        AI Customer Support System
    </div>
    """, unsafe_allow_html=True)


# ---------------- HEADER ----------------
st.markdown("""
<div class="hero">
    <h1>🛟 AI Customer Support Agent</h1>
    <p><b>Smart Support. Instant Answers. Better Experience.</b></p>
    <p>Ask questions, track orders and resolve customer issues with AI.</p>
</div>
""", unsafe_allow_html=True)


# ---------------- STATUS ----------------
st.markdown("""
<div class="status-card">
    🟢 &nbsp; AI Assistant Ready &nbsp; | &nbsp;
    ⚡ Instant Responses &nbsp; | &nbsp;
    🔐 Customer Support
</div>
""", unsafe_allow_html=True)


# ---------------- SESSION STATE ----------------
if "agent" not in st.session_state:
    st.session_state.agent = SupportAgent()

if "history" not in st.session_state:
    st.session_state.history = []

if "display" not in st.session_state:
    st.session_state.display = []


# ---------------- DISPLAY CHAT ----------------
for item in st.session_state.display:
    with st.chat_message(item["role"]):
        st.markdown(item["text"])

        if item.get("tool_calls"):
            with st.expander(
                f"🔧 {len(item['tool_calls'])} tool call(s)"
            ):
                for call in item["tool_calls"]:
                    st.markdown(f"**🧰 Tool:** `{call['tool']}`")
                    st.code(
                        f"{call['tool']}({call['arguments']})",
                        language="python"
                    )
                    st.markdown("**📋 Tool Result**")
                    st.json(call["result"])


# ---------------- CHAT INPUT ----------------
prompt = st.chat_input(
    "💬 Type your question here..."
)

if prompt:
    st.session_state.display.append({
        "role": "user",
        "text": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("✨ AI is thinking..."):
            try:
                result = st.session_state.agent.run(
                    prompt,
                    st.session_state.history
                )

                st.session_state.history = result.messages

                st.markdown(result.answer)

                if result.tool_calls:
                    with st.expander(
                        f"🔧 {len(result.tool_calls)} tool call(s)"
                    ):
                        for call in result.tool_calls:
                            st.markdown(f"**🧰 Tool:** `{call['tool']}`")
                            st.code(
                                f"{call['tool']}({call['arguments']})",
                                language="python"
                            )
                            st.markdown("**📋 Tool Result**")
                            st.json(call["result"])

                st.session_state.display.append({
                    "role": "assistant",
                    "text": result.answer,
                    "tool_calls": result.tool_calls
                })

            except Exception as e:
                st.error(f"⚠️ Something went wrong: {e}")


# ---------------- FOOTER ----------------
st.markdown("""
<br>
<div class="small-caption">
    Built with ❤️ using Streamlit, Python and Groq
</div>
""", unsafe_allow_html=True)
