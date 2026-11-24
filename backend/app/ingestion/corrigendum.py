import re
from difflib import SequenceMatcher

PATTERNS = {
    "deadline": re.compile(r"(?:bid|tender|submission|closing)\s*(?:submission\s*)?(?:date|deadline|due date)\s*[:\-]?\s*([^\n;]{3,100})", re.I),
    "emd": re.compile(r"(?:earnest money deposit|\bEMD\b)\s*(?:amount)?\s*[:\-]?\s*(?:of|is)?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)", re.I),
    "turnover": re.compile(r"(?:annual\s+)?turnover[^\n.]{0,100}", re.I),
    "experience": re.compile(r"(?:similar\s+work|experience|completed\s+works)[^\n.]{0,140}", re.I),
    "eligibility": re.compile(r"(?:eligibility|qualification|technical criteria)[^\n.]{0,180}", re.I),
}
def _matches(text):
    return {key: [str(v).strip() for v in pattern.findall(text)[:10]]
            for key, pattern in PATTERNS.items() if pattern.findall(text)}
def compare_documents(original_text, revised_text):
    old, new = _matches(original_text), _matches(revised_text)
    changes = []
    for key in PATTERNS:
        before, after = old.get(key, []), new.get(key, [])
        if before != after and (before or after):
            changes.append({"change_type": key, "old_value": " | ".join(before) or None,
                            "new_value": " | ".join(after) or None,
                            "explanation": f"Potential {key} change detected. Verify against the exact clauses and page citations."})
    ratio = SequenceMatcher(None, original_text[:50000], revised_text[:50000]).ratio()
    if ratio < .995 and not changes:
        changes.append({"change_type": "text_revision", "old_value": None, "new_value": None,
                        "explanation": f"Text differs (similarity {ratio:.3f}); manual review is required."})
    return changes
