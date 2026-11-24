from datetime import date

def evaluate_company(profile, certifications, projects, requirements):
    checks = []
    def add(name, status, detail, weight=1.0, page=None):
        checks.append({"requirement": name, "status": status, "detail": detail, "weight": weight, "source_page": page})
    turnover = float(profile.annual_turnover_inr) if profile.annual_turnover_inr is not None else None
    req = requirements
    if req.minimum_annual_turnover_inr is not None:
        required = req.minimum_annual_turnover_inr
        beneficiaries = [x.lower() for x in req.relaxation_beneficiaries]
        relax = bool((profile.udyam_number and "msme" in beneficiaries) or
                     (profile.dpiit_startup_number and "dpiit_startup" in beneficiaries)) and req.turnover_relaxation_permitted
        if turnover is None:
            add("Annual turnover", "MISSING_EVIDENCE", f"Provide audited turnover proof; requirement INR {required:,.2f}.", 2)
        elif turnover >= required:
            add("Annual turnover", "PASS", f"Reported INR {turnover:,.2f}; required INR {required:,.2f}.", 2)
        elif relax:
            add("Annual turnover", "NEEDS_VERIFICATION", f"Turnover is below INR {required:,.2f}; tender text permits a relaxation for a stated beneficiary. Verify DPIIT/Udyam proof and tender conditions.", 2)
        else:
            add("Annual turnover", "FAIL", f"Reported INR {turnover:,.2f} is below INR {required:,.2f}.", 2)
    if req.minimum_years_experience is not None:
        actual, required = profile.years_in_business, req.minimum_years_experience
        beneficiaries = [x.lower() for x in req.relaxation_beneficiaries]
        relax = bool((profile.udyam_number and "msme" in beneficiaries) or
                     (profile.dpiit_startup_number and "dpiit_startup" in beneficiaries)) and req.experience_relaxation_permitted
        if actual is None:
            add("Business experience", "MISSING_EVIDENCE", f"Provide experience evidence; requirement {required} years.", 2)
        elif actual >= required:
            add("Business experience", "PASS", f"Reported {actual} years; requirement {required}.", 2)
        elif relax:
            add("Business experience", "NEEDS_VERIFICATION", f"Experience is below {required} years; tender text permits a relaxation for a stated beneficiary. Verify recognition and tender conditions.", 2)
        else:
            add("Business experience", "FAIL", f"Reported {actual} years is below {required} years.", 2)
    if req.minimum_similar_work_value_inr is not None:
        values = [float(p.contract_value_inr) for p in projects if p.contract_value_inr is not None]
        if not values:
            add("Similar work value", "MISSING_EVIDENCE", "Add similar completed projects and supporting work orders.", 2)
        elif max(values) >= req.minimum_similar_work_value_inr:
            add("Similar work value", "NEEDS_VERIFICATION", f"Recorded project INR {max(values):,.2f}; verify similarity and completion evidence.", 2)
        else:
            add("Similar work value", "FAIL", f"Highest project value INR {max(values):,.2f} is below requirement INR {req.minimum_similar_work_value_inr:,.2f}.", 2)
    for cert in req.required_certifications:
        key = cert.lower()
        matching = [c for c in certifications if key in c.name.lower() or c.name.lower() in key]
        if "gst" in key:
            status = "PASS" if profile.gstin else "MISSING_EVIDENCE"
        elif "pan" in key:
            status = "PASS" if profile.pan_last_four else "MISSING_EVIDENCE"
        elif "udyam" in key or "msme" in key:
            status = "PASS" if profile.udyam_number else "MISSING_EVIDENCE"
        elif "dpiit" in key or "startup" in key:
            status = "PASS" if profile.dpiit_startup_number else "MISSING_EVIDENCE"
        else:
            valid = [c for c in matching if not c.valid_until or c.valid_until.date() >= date.today()]
            status = "PASS" if valid else "MISSING_EVIDENCE"
        add("Certification: " + cert, status, "Profile evidence recorded." if status == "PASS" else f"Add valid {cert} evidence.", 1)
    if req.emd_amount_inr is not None:
        beneficiaries = [x.lower() for x in req.relaxation_beneficiaries]
        exemption = bool((profile.udyam_number and "msme" in beneficiaries) or
                         (profile.dpiit_startup_number and "dpiit_startup" in beneficiaries)) and req.emd_exemption_permitted
        add("EMD / bid security", "NEEDS_VERIFICATION" if exemption else "MISSING_EVIDENCE",
            "Tender-specific MSME/DPIIT startup exemption is stated; verify applicability, recognition proof and tender conditions." if exemption else f"Arrange EMD INR {req.emd_amount_inr:,.2f} or verify an applicable exemption.", 1)
    if not checks:
        add("Tender requirements", "NEEDS_VERIFICATION", "No mandatory criteria extracted; manual tender review required.", 1)
    total = sum(x["weight"] for x in checks)
    score = round(100 * sum(x["weight"] for x in checks if x["status"] == "PASS") / total, 1) if total else 0
    fail = any(x["status"] == "FAIL" for x in checks)
    uncertain = any(x["status"] in ("MISSING_EVIDENCE", "NEEDS_VERIFICATION") for x in checks)
    return {"score": score, "recommendation": "NO_BID" if fail else ("REVIEW_REQUIRED" if uncertain else "BID_CANDIDATE"),
            "checks": checks, "checklist": [{"title": x["requirement"], "status": x["status"],
            "required_action": x["detail"], "source_page": x["source_page"], "is_completed": False}
            for x in checks if x["status"] != "PASS"],
            "limitations": ["Decision support only; not a legal or procurement eligibility guarantee.",
            "Government MSME/DPIIT benefits are not assumed. A relaxation is applied only where tender text explicitly permits it.",
            "Human verification of clauses, amendments and supporting evidence is required."]}
