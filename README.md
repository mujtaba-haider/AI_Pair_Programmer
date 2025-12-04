# AI Pair Engineer — Real-time Code Assistant

A **Streamlit** app powered by the **OpenAI API** that acts as a real-time AI pair programmer. The app analyzes your code, detects design flaws, proposes improvements, refactors, and suggests test cases — all while you type.

---

## Features

* **Real-time code analysis**: Detect design flaws and code smells.
* **Refactor suggestions**: Receive improved code snippets instantly.
* **Test case generation**: AI proposes edge and negative test cases.
* **Auto-suggestions**: Copilot-like cursor suggestions.
* **Multi-language support**: Python, JavaScript, TypeScript, Go, Java, C#.
* **Dark-themed code editor** with live updates.
* **Console output** for AI-generated tests and suggestions.

---

## Demo

A live demo can be deployed on [Streamlit Cloud](https://share.streamlit.io/).

---

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/ai-pair-engineer.git
cd ai-pair-engineer
```

2. **Create a virtual environment**

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set your OpenAI API Key**

* Using environment variable:

```bash
export OPENAI_API_KEY="sk-xxxx"      # macOS / Linux
setx OPENAI_API_KEY "sk-xxxx"        # Windows
```

* Or in `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "sk-xxxx"
```

---

## Usage

Run the Streamlit app:

```bash
streamlit run ai_pair_engineer_streamlit.py
```

* Write your code in the editor.
* Press **Suggest Improvement Now** or wait for **auto-suggestions**.
* View AI suggestions in the right panel and apply them to your code.
* Check the console for proposed test cases.

---

## Supported Languages

* Python
* JavaScript
* TypeScript
* Go
* Java
* C#

---

## Deployment

* **Streamlit Cloud** (Recommended)
* **Hugging Face Spaces**
* **VPS / Cloud VM**
* **Docker container**

---

## Contributing

Feel free to fork the repo, submit pull requests, or open issues for bugs/features.

---

## License

No License

---

## Acknowledgements

* [Streamlit](https://streamlit.io/)
* [OpenAI API](https://platform.openai.com/)
* Inspired by AI pair programming tools like GitHub Copilot.
