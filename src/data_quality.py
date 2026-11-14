def evaluate_dataset_quality(studies: list) -> dict:
    """
    Evaluates scientific metadata completeness across core NASA PSI identifiers
    and primary investigation objectives (study_id, title, objective).
    """
    if not studies:
        return {"score": 0.0, "total_records": 0}

    core_fields = ["study_id", "title", "objective"]
    total_checks = len(studies) * len(core_fields)
    passed_checks = 0

    for s in studies:
        for field in core_fields:
            val = s.get(field)
            if val is not None and str(val).strip() != "":
                passed_checks += 1

    score = round((passed_checks / total_checks) * 100, 1)
    return {
        "score": score,
        "total_records": len(studies)
    }