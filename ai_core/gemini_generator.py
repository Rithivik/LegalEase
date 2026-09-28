"""
gemini_generator.py - Gemini integration for LegalEase.

GeminiDocumentGenerator builds a structured prompt from the user's inputs
(document type, parties, terms, dates) and sends it to Google Gemini via
generate_content. It returns the generated legal document as text.

Uses the official Google Gen AI SDK (package: google-genai). The older
"google-generativeai" package shown in the project document is deprecated,
but the call pattern is the same: create a client/model, call
generate_content(prompt), read response.text.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Make the project root importable when this file is run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402

logger = logging.getLogger("legalease.gemini")


class GenerationError(Exception):
    """Raised when the document cannot be generated. `status_code` maps to HTTP."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


SYSTEM_INSTRUCTION = """You are LegalEase, an expert legal drafting assistant.
You draft clear, professional, well-structured legal documents.

Formatting rules (follow exactly):
- Start with the document title on the first line as a Markdown level-2 heading: "## <Title>".
- Use "### <number>. <Section Name>" for every numbered section heading.
- Use "**bold**" only for defined terms and party labels.
- Use "- " for bullet points.
- Do NOT wrap the output in code fences. Do NOT add commentary before or after the document.
- Where a detail was not supplied (addresses, amounts, registration numbers),
  insert a clear placeholder in square brackets, e.g. [Client Address].
- End with an execution / signature block for every party, with lines for
  Signature, Name, Title and Date.
"""


class GeminiDocumentGenerator:
    """Generates legal documents with Google Gemini (or a local mock)."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None,
                 mock: bool | None = None):
        self.api_key = api_key if api_key is not None else config.GEMINI_API_KEY
        self.model_name = model_name or config.GEMINI_MODEL
        # Mock mode: explicit flag, MOCK_MODE in .env, or no API key available
        self.mock = config.MOCK_MODE if mock is None else mock
        if not self.api_key:
            self.mock = True
        self.client = None

        if not self.mock:
            try:
                from google import genai  # google-genai package
            except ImportError as exc:  # pragma: no cover - depends on install
                raise GenerationError(
                    "The 'google-genai' package is not installed. "
                    "Run: pip install -r requirements.txt", 500
                ) from exc
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Gemini client ready (model=%s)", self.model_name)
        else:
            logger.warning("MOCK MODE: no Gemini calls will be made "
                           "(set GEMINI_API_KEY in .env to use real AI).")

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------
    @staticmethod
    def build_prompt(document_type: str, parties: str, terms: str, dates: str,
                     jurisdiction: str = "", additional_instructions: str = "") -> str:
        """Create the structured prompt sent to Gemini."""
        term_list = [t.strip() for t in terms.split(";") if t.strip()]
        terms_block = "\n".join(f"- {t}" for t in term_list) if term_list else "- (none specified)"

        prompt = (
            f"Generate a comprehensive legal document titled '{document_type}'.\n\n"
            f"Involved parties: {parties}\n"
            f"Effective Date: {dates}\n"
        )
        if jurisdiction:
            prompt += f"Governing law / jurisdiction: {jurisdiction}\n"
        prompt += (
            f"\nKey terms and conditions that MUST be included (expand each into "
            f"proper legal clauses):\n{terms_block}\n\n"
            "Ensure a formal legal structure with multiple sections and legal clauses, "
            "including: recitals/background, definitions (if useful), the obligations "
            "of each party, payment or consideration (if relevant), term and "
            "termination, confidentiality, dispute resolution, governing law, "
            "miscellaneous/boilerplate clauses, and a signature block."
        )
        if additional_instructions:
            prompt += f"\n\nAdditional instructions from the user: {additional_instructions}"
        return prompt

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def generate_document(self, document_type: str, parties: str, terms: str, dates: str,
                          jurisdiction: str = "", additional_instructions: str = "") -> str:
        """Generate the legal document and return it as (Markdown-style) text."""
        prompt = self.build_prompt(document_type, parties, terms, dates,
                                   jurisdiction, additional_instructions)
        if self.mock:
            return self._mock_document(document_type, parties, terms, dates, jurisdiction)
        return self._call_gemini(prompt)

    def _call_gemini(self, prompt: str) -> str:
        from google.genai import errors, types

        gen_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=config.GEMINI_TEMPERATURE,
            max_output_tokens=config.GEMINI_MAX_OUTPUT_TOKENS,
        )

        # Try the main model first, then the fallbacks
        models = [self.model_name] + [m for m in config.GEMINI_FALLBACK_MODELS
                                      if m != self.model_name]
        failures: dict[str, str] = {}   # model -> short reason, shown to the user
        rate_limited: list[str] = []

        for model in models:
            try:
                logger.info("Calling Gemini model %s", model)
                response = self.client.models.generate_content(
                    model=model, contents=prompt, config=gen_config
                )
                text = (response.text or "").strip()
                if not text:
                    raise GenerationError(
                        "Gemini returned an empty response (it may have been blocked "
                        "by safety filters). Try rephrasing your inputs.", 502)
                return self._clean_output(text)

            except errors.ClientError as exc:  # 4xx errors
                code = getattr(exc, "code", 400)
                if code == 404:
                    failures[model] = "not available for this API key (404)"
                    logger.warning("Model %s not found, trying next model", model)
                    continue
                if code in (401, 403) or "API key" in str(exc):
                    raise GenerationError(
                        "Gemini rejected the API key. Check GEMINI_API_KEY in your "
                        ".env file / Streamlit secrets.", 401) from exc
                if code == 429:
                    failures[model] = "free-tier quota / rate limit reached (429)"
                    rate_limited.append(model)
                    logger.warning("Quota reached for %s, trying next model", model)
                    continue
                raise GenerationError(f"Gemini request error ({model}): {exc}", 400) from exc

            except errors.ServerError as exc:  # 5xx errors
                failures[model] = f"Google server busy/error ({getattr(exc, 'code', 500)})"
                logger.warning("Gemini server error on %s: %s", model, exc)
                continue

            except GenerationError:
                raise

            except Exception as exc:  # network problems etc.
                raise GenerationError(f"Could not reach Gemini: {exc}", 503) from exc

        details = "; ".join(f"{m}: {r}" for m, r in failures.items())
        if rate_limited and len(rate_limited) == len(models):
            raise GenerationError(
                "Gemini free-tier quota reached for every model tried. Wait a minute "
                "and try again; if it keeps happening, the daily limit is used up "
                f"(it resets around 12:30 pm IST). Details - {details}", 429)
        if rate_limited:
            raise GenerationError(
                "Gemini quota reached for your model and no fallback model worked. "
                f"Wait a minute and try again. Details - {details}", 429)
        raise GenerationError(
            "No Gemini model was available. Set GEMINI_MODEL to a model your key can "
            f"use (check the model list in Google AI Studio). Details - {details}", 502)

    @staticmethod
    def _clean_output(text: str) -> str:
        """Remove code fences the model sometimes adds around the document."""
        lines = text.strip().splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Mock document (offline testing)
    # ------------------------------------------------------------------
    @staticmethod
    def _mock_document(document_type: str, parties: str, terms: str, dates: str,
                       jurisdiction: str = "") -> str:
        party_list = [p.strip() for p in parties.replace("\n", ",").split(",") if p.strip()]
        if len(party_list) < 2:
            party_list = (party_list + ["[Party A]", "[Party B]"])[:2]
        term_list = [t.strip() for t in terms.split(";") if t.strip()]
        law = jurisdiction or "[Jurisdiction]"

        parts = [
            f"## {document_type}",
            "",
            f"This {document_type} (the **\"Agreement\"**) is entered into and made "
            f"effective as of {dates} (the **\"Effective Date\"**).",
            "",
            "### 1. Parties",
            "",
        ]
        for i, p in enumerate(party_list, 1):
            parts.append(f"- **Party {i}:** {p}, with its address at [Address of Party {i}]")
        parts += [
            "",
            "### 2. Background",
            "",
            "WHEREAS, the Parties wish to set out the terms on which they will work together; "
            "and WHEREAS, each Party has the authority to enter into this Agreement;",
            "",
            "NOW, THEREFORE, in consideration of the mutual covenants contained herein, "
            "the Parties agree as follows:",
            "",
            "### 3. Key Terms and Conditions",
            "",
        ]
        if term_list:
            parts += [f"- {t}" for t in term_list]
        else:
            parts.append("- [Key terms to be agreed by the Parties]")
        parts += [
            "",
            "### 4. Confidentiality",
            "",
            "Each Party shall keep confidential all non-public information received from the "
            "other Party and shall not disclose it to any third party without prior written consent.",
            "",
            "### 5. Term and Termination",
            "",
            "This Agreement begins on the Effective Date and continues until terminated. "
            "Either Party may terminate this Agreement by giving [Number] days' written notice.",
            "",
            "### 6. Governing Law and Dispute Resolution",
            "",
            f"This Agreement shall be governed by the laws of {law}. Any dispute shall first be "
            "resolved through good-faith negotiation, failing which by the competent courts.",
            "",
            "### 7. Entire Agreement",
            "",
            "This Agreement constitutes the entire agreement between the Parties and supersedes "
            "all prior discussions. Any amendment must be in writing and signed by both Parties.",
            "",
            "### 8. Signatures",
            "",
            "IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.",
            "",
        ]
        for p in party_list:
            parts += [
                f"**{p}**",
                "Signature: ______________________",
                "Name: [Name]",
                "Title: [Title]",
                "Date: [Date]",
                "",
            ]
        parts.append("*(Sample generated in MOCK MODE - add a GEMINI_API_KEY for AI drafting.)*")
        return "\n".join(parts).strip()


if __name__ == "__main__":
    # Quick manual test:  python ai_core/gemini_generator.py
    logging.basicConfig(level=logging.INFO)
    gen = GeminiDocumentGenerator()
    print(gen.generate_document(
        "Non-Disclosure Agreement",
        "Jane Doe (Freelancer), TechNova Inc. (Client)",
        "Confidential information includes source code; Obligations last 2 years",
        "April 15, 2025",
    ))
