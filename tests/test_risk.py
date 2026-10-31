from sentinel_api.risk import assess_pull_request


def test_low_risk_default():
    result = assess_pull_request({"pull_request": {"title": "docs update"}})
    assert result.level == "low"
    assert result.score == 0


def test_high_risk_uses_real_github_nested_pr_fields():
    result = assess_pull_request({
        "pull_request": {
            "title": "Security auth migration",
            "body": "production breaking change",
            "labels": [{"name": "urgent"}],
            "changed_files": 50,
            "additions": 900,
            "deletions": 500,
        }
    })
    assert result.score == 95
    assert result.level == "high"
    assert len(result.factors) == 6


def test_untrusted_shapes_do_not_crash():
    result = assess_pull_request({"pull_request": {"title": None, "labels": [None, "bad"]}})
    assert result.score == 0
