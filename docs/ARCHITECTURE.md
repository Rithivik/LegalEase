# LegalEase Architecture

## Request flow
1. **Streamlit (`frontend/app.py`)** collects `document_type`, `parties`, `terms` (semicolon-separated), `dates`, plus the optional `jurisdiction` and `additional_instructions`.
2. It sends `POST /generate` with a JSON body to **FastAPI (`legalEaseAPI/routes.py`)**.
3. The `DocumentRequest` Pydantic model validates the input. Missing or blank fields return HTTP 422.
4. `GeminiDocumentGenerator.generate_document()` in `ai_core/gemini_generator.py`:
   - builds a structured prompt, with a system instruction that fixes the output format (`##` title, `###` sections, `-` bullets, a signature block),
   - calls `client.models.generate_content(model, contents, config)`,
   - falls back to other models on 404 or 5xx errors, and maps 401/403/429 to clear error messages,
   - returns a sample document instead when in mock mode (no API key, or `MOCK_MODE=true`).
5. The API returns `{document, document_type, model, mock}`.
6. The frontend sanitizes the text and renders it with `format_html_preview()`. You can edit it, and the downloads are built with `format_txt`, `format_docx` and `format_pdf`.

## Formatting pipeline (`ai_core/generator.py`)
`sanitize_text` → `parse_blocks` (title / heading / subheading / bullet / paragraph) → `inline_runs` (**bold**, *italic*).
Every output format uses the same parser, so the preview, DOCX and PDF always match.

- **DOCX**: logo, a centred title, Times New Roman 12 pt, navy headings, bullet lists, a "Schedule A" terms table built from the semicolon-separated input, a disclaimer, and a footer with company text and page numbers.
- **PDF**: a header with logo and title on every page, bold headings, bullet terms, and a footer showing `Page X/N`. It uses a Unicode TTF (Arial or DejaVu) when available and falls back to Helvetica otherwise.

## API endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Status, model name, mock mode |
| GET | `/document-types` | Suggested document types |
| POST | `/generate` | Generate a document |
| POST | `/export/{txt\|docx\|pdf}` | Convert text to a downloadable file |
