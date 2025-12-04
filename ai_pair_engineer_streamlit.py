import os
import time
import re
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# ----------------------------
# Configuration & Secrets
# ----------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
if not OPENAI_API_KEY:
    st.error("⚠️ OPENAI_API_KEY missing. Add it as an environment variable or in .streamlit/secrets.toml and restart.")
    st.stop()

# Initialize OpenAI client (v1+)
client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# Optional: ACE editor availability
# ----------------------------
try:
    from streamlit_ace import st_ace
    ACE_AVAILABLE = True
except Exception:
    ACE_AVAILABLE = False

# ----------------------------
# App UI
# ----------------------------
st.set_page_config(page_title="AI Pair Engineer — Real-time", layout="wide")
st.title("🤖 AI Pair Engineer — Real-time Autocomplete & Refactor")

# Sidebar
with st.sidebar:
    st.header("Settings")
    language = st.selectbox("Programming language", ["python", "javascript", "typescript", "go", "java", "csharp"], index=0)
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-4o-realtime-preview", "gpt-4"], index=0)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.15)
    max_tokens = st.slider("Max response tokens", 128, 1500, 512)
    auto_mode = st.checkbox("Enable auto-suggest", value=True)
    idle_threshold = st.slider("Idle seconds before suggestion", 1, 6, 2)
    show_diff = st.checkbox("Show unified diff/patch", value=True)
    st.markdown("---")
    st.caption("Editor theme: dark. If streamlit-ace is not installed the app uses a fallback text area.")

# Sample starters
SAMPLES = {
    "python": """def fetch_users(db):
    users = db.query('SELECT * FROM users')
    for u in users:
        print(u.name)
""",
    "javascript": """async function getUsers(req, res) {
  const users = await db.find('users')
  res.send(users)
}
""",
    "typescript": """async function fetchData(url: string): Promise<any> {
  const res = await fetch(url)
  return res.json()
}
""",
    "go": """package main

func Sum(a int, b int) int {
    return a + b
}
""",
    "java": """public class Hello {
  public static void main(String[] args) {
    System.out.println("Hello World");
  }
}
""",
    "csharp": """using System;
class Program {
  static void Main() {
    Console.WriteLine("Hello World");
  }
}
""",
}

# Initialize session state keys safely
if "editor_content" not in st.session_state:
    st.session_state.editor_content = SAMPLES.get("python", "")
if "last_edit_ts" not in st.session_state:
    st.session_state.last_edit_ts = time.time()
if "manual_trigger" not in st.session_state:
    st.session_state.manual_trigger = False
if "last_suggested_code" not in st.session_state:
    st.session_state.last_suggested_code = None
if "suggestion_md" not in st.session_state:
    st.session_state.suggestion_md = None
if "suggested_refactor_code" not in st.session_state:
    st.session_state.suggested_refactor_code = None

# Layout: left editor, right suggestions + console
left_col, right_col = st.columns([1.3, 1])

with left_col:
    st.subheader("Editor — Dark theme")
    editor_height = 480

    # Controlled editor value: show session_state.editor_content (keeps Apply Suggestion working)
    initial_code = st.session_state.editor_content or SAMPLES.get(language, "")
    if ACE_AVAILABLE:
        code = st_ace(value=initial_code, language=language, theme="monokai", key="ace", height=editor_height)
    else:
        code = st.text_area("Code", value=initial_code, height=editor_height, key="fallback_editor")

    # If user changed language and editor was a sample, optionally replace content
    # (Don't override user's custom code if they've typed something)
    if st.session_state.editor_content == "" and SAMPLES.get(language):
        st.session_state.editor_content = SAMPLES[language]

    # Save to session state and detect edits
    if code != st.session_state.editor_content:
        st.session_state.editor_content = code
        st.session_state.last_edit_ts = time.time()

    # Editor actions
    col_apply, col_manual, col_clear = st.columns([1,1,1])
    if col_manual.button("Suggest now"):
        st.session_state.manual_trigger = True
    if col_apply.button("Apply suggestion"):
        suggested = st.session_state.get("suggested_refactor_code")
        if suggested:
            st.session_state.editor_content = suggested
            # keep last edit ts updated so autosuggest doesn't immediately retrigger
            st.session_state.last_edit_ts = time.time()
            st.experimental_rerun()
    if col_clear.button("Clear suggestion"):
        st.session_state.suggestion_md = None
        st.session_state.suggested_refactor_code = None

with right_col:
    st.subheader("AI Suggestions")
    suggestion_box = st.empty()
    st.subheader("Console / Proposed Tests")
    console_box = st.empty()

# Helpers
# regex to capture fenced code blocks with optional language
CODE_BLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]*)?\n([\s\S]*?)\n```")

def extract_code_block(md: str):
    if not md:
        return None
    m = CODE_BLOCK_RE.search(md)
    return m.group(1) if m else None

# Build system prompt
SYSTEM_PROMPT = (
    "You are The AI Pair Engineer — a senior software engineer assistant.\n"
    "For the provided code, return the following in Markdown:\n"
    "- Summary (1-2 lines).\n"
    "- 3-6 design flaws or code smells.\n"
    "- 3 actionable inline auto-suggestions (line-level, short).\n"
    "- 3-6 proposed test cases (including edge/negative cases).\n"
    "- Optional: a refactored version of the code wrapped in a fenced code block using the language.\n"
    "Also include small completion snippets where helpful (<= 10 lines). Be concise and practical."
)

# Call OpenAI
def call_pair_engineer(code_text: str, language: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Language: {language}\n\nCode:\n```{language}\n{code_text}\n```"},
    ]
    try:
        # show a small progress indicator to the user (not blocking)
        with st.spinner("Contacting OpenAI..."):
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=float(temperature),
                max_tokens=int(max_tokens),
            )
        # Newer OpenAI libs return content in .choices[0].message.content
        content = None
        try:
            content = resp.choices[0].message["content"]
        except Exception:
            # fallback for other response shapes
            content = getattr(resp.choices[0].message, "content", None) or resp.choices[0].text
        return content
    except Exception as e:
        return f"❌ OpenAI request failed:\n{e}"

# Improved test extraction that ignores fenced code blocks and finds the tests section robustly
def extract_test_cases_from_md(md: str, max_items: int = 10):
    """
    Strategy:
    1. Remove fenced code blocks so we don't accidentally capture bullets inside code.
    2. Look for headings that indicate tests (Proposed Test Cases / Test Cases / Tests).
    3. If found, extract bullet lines (starting with -, *, or numbered) underneath that heading up to next heading.
    4. If not found, fallback to any bullet line that contains the word 'test'.
    """
    if not md:
        return []

    # 1) Strip fenced code blocks (replace with empty string)
    md_no_code = CODE_BLOCK_RE.sub("", md)

    # 2) Split by headings for tests (case-insensitive)
    split_pattern = re.compile(r"(?i)(^|\n)\s*(#{1,6}\s*)?(proposed test cases|test cases|tests|proposed tests)\b", re.IGNORECASE)
    parts = split_pattern.split(md_no_code)
    tests = []

    if len(parts) > 1:
        # Find the part after the first match (parts is list where matched groups interleave)
        # We'll search for the first occurrence index that matches our key words
        # Simpler: find the index of the match using search
        match = split_pattern.search(md_no_code)
        if match:
            start = match.end()
            # take the substring from that point to next H2/H3 style marker or end
            following_text = md_no_code[start:]
            # stop at next significant heading (lines starting with # or '##' or '###' or another section label like '###')
            next_heading = re.search(r"\n\s*#{1,6}\s+", following_text)
            section = following_text[: next_heading.start()] if next_heading else following_text
            # extract bullets lines only
            for ln in section.splitlines():
                stripped = ln.strip()
                if stripped.startswith(("-", "*")) or re.match(r"^\d+\.", stripped):
                    # remove leading bullet markers and whitespace
                    cleaned = re.sub(r"^(\-|\*|\d+\.)\s*", "", stripped)
                    if cleaned:
                        tests.append(cleaned)
                    if len(tests) >= max_items:
                        break

    # Fallback: find any bullet lines outside code fences containing 'test'
    if not tests:
        for ln in md_no_code.splitlines():
            stripped = ln.strip()
            if (stripped.startswith(("-", "*")) or re.match(r"^\d+\.", stripped)) and "test" in stripped.lower():
                cleaned = re.sub(r"^(\-|\*|\d+\.)\s*", "", stripped)
                if cleaned:
                    tests.append(cleaned)
                if len(tests) >= max_items:
                    break

    return tests[:max_items]

# Generate suggestion and update UI
def generate_suggestion_and_update():
    current = st.session_state.editor_content
    # Prevent empty or unchanged calls
    if not current or st.session_state.get("last_suggested_code") == current:
        return

    suggestion_md = call_pair_engineer(current, language)
    # In case of error text, suggestion_md may be an error string; display it.
    st.session_state.suggestion_md = suggestion_md
    suggestion_box.markdown(suggestion_md if suggestion_md else "_No suggestion returned._")

    # extract refactored code block if provided
    ref = extract_code_block(suggestion_md) if suggestion_md else None
    if ref:
        st.session_state.suggested_refactor_code = ref

    # extract test cases
    tests = extract_test_cases_from_md(suggestion_md or "")
    console_text = "\n".join(f"- {t}" for t in tests) if tests else "(No explicit test cases found in suggestions.)"
    console_box.code(console_text)

    # update last suggested content marker
    st.session_state.last_suggested_code = current

# Triggers: manual or auto
manual = st.session_state.get("manual_trigger", False)
if manual:
    st.session_state.manual_trigger = False
    generate_suggestion_and_update()

# Auto-mode: check idle time and don't spam
if auto_mode:
    last_edit = st.session_state.get("last_edit_ts", None)
    if last_edit:
        idle = time.time() - last_edit
        # Only trigger if idle threshold reached and content changed since last suggestion
        if idle >= idle_threshold and st.session_state.get("last_suggested_code") != st.session_state.editor_content:
            generate_suggestion_and_update()

# Ghost preview: show first few lines of refactor snippet
if st.session_state.get("suggestion_md"):
    ghost = extract_code_block(st.session_state.suggestion_md) or ""
    ghost_preview = "\n".join(ghost.splitlines()[:6]) if ghost else ""
    if ghost_preview:
        st.info("Ghost suggestion (preview):")
        st.code(ghost_preview, language=language)

# Debug
with st.expander("Debug / State"):
    st.write("Model:", model)
    st.write("Language:", language)
    st.write("Last edit ts:", st.session_state.get("last_edit_ts"))
    st.write("Last suggested code present:", bool(st.session_state.get("last_suggested_code")))
    st.write("Suggestion present:", bool(st.session_state.get("suggestion_md")))
    st.write("Refactor snippet present:", bool(st.session_state.get("suggested_refactor_code")))

# End of app - lightweight instructions
st.markdown("---")
st.caption("How it works: edit code -> pause typing (idle) or press 'Suggest now' -> the AI will analyze code, show design flaws, propose tests, and provide refactor suggestions. Use 'Apply suggestion' to replace the editor with the refactored code.")
