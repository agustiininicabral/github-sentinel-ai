import json
from pathlib import Path


def test_n8n_workflow_export_is_valid_and_connected():
    path = Path(__file__).parents[1] / "n8n" / "github-sentinel-secure-intake.json"
    workflow = json.loads(path.read_text(encoding="utf-8"))
    names = {node["name"] for node in workflow["nodes"]}
    assert names == {
        "Poll Sentinel",
        "Fetch Pending Events",
        "Split Events",
        "Normalize Event",
        "Analyze Event",
        "Acknowledge Processed Event",
    }
    assert set(workflow["connections"]) == names - {"Acknowledge Processed Event"}
    expected_chain = [
        ("Poll Sentinel", "Fetch Pending Events"),
        ("Fetch Pending Events", "Split Events"),
        ("Split Events", "Normalize Event"),
        ("Normalize Event", "Analyze Event"),
        ("Analyze Event", "Acknowledge Processed Event"),
    ]
    for source, target in expected_chain:
        targets = [
            edge["node"]
            for output in workflow["connections"][source]["main"]
            for edge in output
        ]
        assert targets == [target]
    code = next(node for node in workflow["nodes"] if node["name"] == "Normalize Event")
    assert "\\n" not in code["parameters"]["jsCode"]
    assert "delivery_id" in code["parameters"]["jsCode"]
    assert "$input.all()" in code["parameters"]["jsCode"]
    assert "items.map" not in code["parameters"]["jsCode"]
    analyze = next(node for node in workflow["nodes"] if node["name"] == "Analyze Event")
    assert analyze["parameters"]["url"].endswith("/integrations/n8n/analyze")
    assert "delivery_id" in analyze["parameters"]["jsonBody"]
    assert "payload" not in analyze["parameters"]["jsonBody"]
    assert workflow["active"] is False


def test_n8n_workflow_does_not_embed_an_integration_secret():
    path = Path(__file__).parents[1] / "n8n" / "github-sentinel-secure-intake.json"
    workflow = json.loads(path.read_text(encoding="utf-8"))
    for node in workflow["nodes"]:
        if "credentials" in node:
            credential = node["credentials"]["httpHeaderAuth"]
            assert credential["name"] == "Sentinel API Bearer"
            assert credential["id"] == "REPLACE_WITH_CREDENTIAL_ID"
