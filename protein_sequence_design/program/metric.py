def normalize_score(score, baseline):
    if score >= 100:
        return 1e-10  # worst possible quality; avoids division by zero and log(0)
    return min(1, (100 - baseline) / (100 - score))