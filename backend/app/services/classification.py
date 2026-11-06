import re
from typing import Literal

from pydantic import BaseModel, Field

from app.config import settings


class EnquiryAnalysis(BaseModel):
    category: Literal["appointment", "services", "billing", "records", "general"]
    intent: str = Field(min_length=2, max_length=60)
    summary: str = Field(min_length=3, max_length=500)
    suggested_response: str = Field(min_length=3, max_length=1000)


_CATEGORY_KEYWORDS = {
    "appointment": ("appointment", "schedule", "booking", "reschedule", "cancel", "slot"),
    "services": ("service", "vaccination", "checkup", "wellness", "referral"),
    "billing": ("bill", "billing", "payment", "insurance", "cost", "charge"),
    "records": ("record", "document", "medical history", "prescription"),
}
_SUGGESTIONS = {
    "appointment": "Thank you for contacting us about scheduling. Clinic staff will review your request and follow up.",
    "services": "Thank you for your question about clinic services. Please contact clinic staff to confirm availability.",
    "billing": "Thank you for your billing question. Clinic staff will review it and follow up with you.",
    "records": "Thank you for contacting us about records. Clinic staff will review your request and follow up.",
    "general": "Thank you for contacting the clinic. Staff will review your enquiry and follow up.",
}


def _fallback_analysis(subject: str, message: str) -> EnquiryAnalysis:
    normalized = re.sub(r"\s+", " ", f"{subject.strip()}. {message.strip()}").strip()
    text = normalized.casefold()
    category = next(
        (
            name
            for name, words in _CATEGORY_KEYWORDS.items()
            if any(word in text for word in words)
        ),
        "general",
    )
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    summary = next((sentence for sentence in sentences if sentence.strip()), normalized)[:500]
    return EnquiryAnalysis(
        category=category,
        intent=category,
        summary=summary,
        suggested_response=_SUGGESTIONS[category],
    )


def analyze_enquiry(subject: str, message: str) -> EnquiryAnalysis:
    """Use validated structured AI output when configured; always fall back locally."""
    fallback = _fallback_analysis(subject, message)
    if not settings.openai_api_key:
        return fallback
    try:
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)
        analyzer = model.with_structured_output(EnquiryAnalysis)
        result = analyzer.invoke(
            "Classify this clinic administrative enquiry. Return a concise, faithful summary, a short "
            "administrative intent, one supported category, and a polite suggested response for clinic "
            "staff to review. Do not provide medical advice, diagnosis, treatment, or emergency triage. "
            "Do not claim that a request has been completed.\n"
            f"Subject: {subject[:200]}\nMessage: {message[:10000]}"
        )
        return EnquiryAnalysis.model_validate(result)
    except Exception:
        return fallback


def classify_enquiry(subject: str, message: str) -> str:
    return analyze_enquiry(subject, message).category
