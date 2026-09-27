# ⚖️ LegalEase: AI-Powered Legal Document Generator

LegalEase generates legal documents (NDAs, employment contracts, lease agreements and more) with **Google Gemini**. You enter the document type, parties, terms and effective date. It drafts the document, shows a styled preview, lets you edit it, and exports **.TXT / .DOCX / .PDF** files with your logo and footer.

| Layer | Technology | File(s) |
|---|---|---|
| Frontend | Streamlit | `frontend/app.py` |
| Backend | FastAPI + Uvicorn | `legalEaseAPI/main.py`, `legalEaseAPI/routes.py` |
| AI core | Google Gemini (`google-genai` SDK) | `ai_core/gemini_generator.py` |
| Formatting | python-docx, fpdf2, Pillow | `ai_core/generator.py` |
| Config | python-dotenv | `config.py`, `.env` |

```
Streamlit UI ──POST /generate──▶ FastAPI ──▶ GeminiDocumentGenerator ──▶ Gemini API
     ▲                                                                     │
     └──────── document text ◀─────────────────────────────────────────────┘
     └─▶ preview / edit ─▶ format_txt / format_docx / format_pdf ─▶ downloads
```

## Project structure

```
LegalEase/
├── ai_core/
│   ├── __init__.py
│   ├── gemini_generator.py   # Gemini prompt + API call (+ offline mock mode)
│   └── generator.py          # sanitize_text, format_docx, format_pdf, format_html_preview, format_txt
├── docs/ARCHITECTURE.md
├── frontend/app.py           # Streamlit UI
├── Image/
│   ├── Logo.png              # dark logo (DOCX / PDF)
│   └── inverseLogo.png       # light logo (web UI, dark theme)
├── legalEaseAPI/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, CORS, "/" route
│   └── routes.py             # /generate, /export/{fmt}, /health, /document-types
├── tests/                    # pytest suite (runs without an API key)
├── .streamlit/config.toml    # dark theme
├── .vscode/                  # launch configs (run/debug both servers), settings
├── .env / .env.example       # your settings (API key goes here)
├── config.py
├── requirements.txt
├── run.sh / run.bat          # start everything with one command
├── Procfile, Dockerfile, docker-compose.yml
└── README.md
```

---

## 1. Setup in VS Code (one time)

**You need:** Python 3.10 or newer ([python.org](https://www.python.org/downloads/); on Windows tick **"Add Python to PATH"**), VS Code with the **Python** extension (VS Code will suggest it when you open the folder), and a free Gemini API key from **https://aistudio.google.com/apikey**.

1. **Open the project:** unzip `LegalEase.zip`, then in VS Code go to **File → Open Folder… → LegalEase**.
2. **Open a terminal:** **Terminal → New Terminal**.
3. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```
4. **Activate it** (you will see `(venv)` at the start of the prompt):
   - Windows PowerShell: `venv\Scripts\activate`
     *If you get "running scripts is disabled", run once:* `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
   - Windows CMD: `venv\Scripts\activate.bat`
   - macOS / Linux: `source venv/bin/activate`
5. **Select the interpreter:** press `Ctrl+Shift+P`, choose **Python: Select Interpreter**, and pick the one inside `venv`.
6. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   > If you previously installed the old `fpdf` package, remove it first (`pip uninstall fpdf`), because it clashes with `fpdf2`.
7. **Add your API key:** open `.env` and paste your key:
   ```
   GEMINI_API_KEY=AIza...your-key...
   ```
   *No key yet?* The app still runs in **mock mode**. It returns a sample document so you can test the whole flow.

## 2. Run the application

You need **two terminals**, both with the venv activated, both opened in the `LegalEase` folder. Use the **+** button in the VS Code terminal panel to open the second one.

**Terminal 1: backend (FastAPI)**
```bash
uvicorn legalEaseAPI.main:app --reload
```
Wait for `Application startup complete`. The API runs at http://127.0.0.1:8000 and the interactive docs at **http://127.0.0.1:8000/docs**.

**Terminal 2: frontend (Streamlit)**
```bash
streamlit run frontend/app.py
```
Your browser opens **http://localhost:8501**.

**Shortcuts:**
- **VS Code:** open the **Run and Debug** panel (`Ctrl+Shift+D`), choose **"LegalEase: Backend + Frontend"**, and press ▶ (F5). This starts both servers, with breakpoints.
- **Windows:** double-click `run.bat`.
- **macOS / Linux / Git Bash:** `./run.sh`

## 3. Use it

1. Click **✨ Load example** to fill in sample data, or enter your own:
   - **Document Type**: e.g. *Freelance Work Contract*. Choose "Other" to type any type.
   - **Parties Involved**: e.g. `Jane Doe (Service Provider), TechNova Inc. (Client)`
   - **Terms & Conditions**: separate the terms with semicolons, e.g. `Payment within 30 days of invoice; Confidentiality at all times`
   - **Effective Date**: e.g. `April 15, 2025`. **Jurisdiction** is optional.
2. Click **Generate Document**. Gemini usually takes 10–60 seconds.
3. Read the dark-themed preview. Click **✏️ Click to Edit Document** to change the text. The preview and downloads update when you click outside the box or press Ctrl+Enter.
4. Download the document as **.TXT**, **.DOCX** (logo, Times New Roman, terms table, page-numbered footer) or **.PDF** (logo and title on every page, footer with page numbers).
5. Optional: in the sidebar, upload your own company logo and set the company name and email used in the footer.

## 4. Testing

**Automated tests.** These need no API key, because they force mock mode:
```bash
pytest
```
You should see all tests pass: the formatters, the prompt building, the API endpoints, and the TXT/DOCX/PDF exports. In VS Code you can also use the **Testing** panel (flask icon).

**Manual API tests.** Open http://127.0.0.1:8000/docs, expand **POST /generate**, click **Try it out**, then **Execute**. Or use curl:
```bash
curl -X POST http://127.0.0.1:8000/generate -H "Content-Type: application/json" -d "{\"document_type\":\"NDA\",\"parties\":\"Alice (Discloser), Bob (Recipient)\",\"terms\":\"Keep secrets; 2 years\",\"dates\":\"May 1, 2025\"}"
```
**Check your Gemini key**: http://127.0.0.1:8000/health should show `"mock_mode": false`.

**Test Gemini on its own**: `python ai_core/gemini_generator.py`

**Suggested manual checks** (from the project brief): try different combinations of inputs (NDA, lease, employment contract), a very long terms list, and special characters (₹, “smart quotes”). In every download, check the logo, the footer, the bullet formatting and that your terms appear.

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| Sidebar says **Backend not reachable** | Start Terminal 1 (`uvicorn ...`) first, then click **🔄 Recheck backend**. |
| `ModuleNotFoundError: No module named 'config'` / `'ai_core'` | Run the commands from the **LegalEase** root folder, not from inside `frontend/` or `legalEaseAPI/`. |
| `ModuleNotFoundError` for fastapi / streamlit / fpdf | The venv is not active, or the dependencies aren't installed. Activate it and rerun `pip install -r requirements.txt`. |
| Error 401 "Gemini rejected the API key" | Check `GEMINI_API_KEY` in `.env` (no quotes or spaces), then restart the backend. |
| Error 429 | You hit the free-tier rate limit. Wait a minute and try again. |
| "No Gemini model was available" | Set `GEMINI_MODEL` in `.env` to a model your key can use (e.g. `gemini-2.5-flash`), then restart the backend. |
| Document always says "MOCK MODE" | No key was found, or `MOCK_MODE=true`. Fix `.env` and restart the backend. |
| Port already in use | Use `uvicorn legalEaseAPI.main:app --port 8001` and set `BACKEND_URL=http://127.0.0.1:8001` in `.env`. |

## 6. Deployment (free public link)

**Streamlit Community Cloud** runs the app in *standalone mode*, where the Streamlit app calls Gemini directly and no separate backend is needed.

1. Push the latest code to GitHub.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app → Deploy a public app from GitHub**.
4. Fill in the form:
   - **Repository:** `Rithivik/LegalEase`
   - **Branch:** `main`
   - **Main file path:** `frontend/app.py`
   - **App URL:** pick a name, e.g. `legalease-ai`
5. Open **Advanced settings**, set **Python version** to **3.12**, and paste the following into **Secrets**:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   GEMINI_MODEL = "gemini-flash-latest"
   APP_MODE = "standalone"
   ```
6. Click **Deploy**. The first build takes a few minutes, and then you get a public link.

The backend can also be deployed separately (Render/Railway via `Procfile`, or `docker compose up --build`). If you do that, set `APP_MODE="api"` and `BACKEND_URL` to the backend's address in the Streamlit secrets.

## Notes on changes from the project document

- **Model:** the brief selected `gemini-1.5-pro`, which Google has retired. The default is now `gemini-flash-latest`, an alias that always points to Google's current Flash model. You can change it in `.env`, and fallback models are tried automatically.
- **SDK:** `google-generativeai` is deprecated, so this project uses its official replacement, **`google-genai`**. The flow is the same: build a prompt, call `generate_content`, read `response.text`.
- **PDF library:** the maintained `fpdf2` package is used. It is imported as `fpdf`, like the brief shows.
- **Extras beyond the brief:** a mock mode, an `/export/{fmt}` API, a `/health` check, an optional jurisdiction field, custom logo upload, a "Load example" button and a pytest suite.

> ⚠️ LegalEase output is AI-generated and is not legal advice. Have important documents reviewed by a qualified lawyer.
