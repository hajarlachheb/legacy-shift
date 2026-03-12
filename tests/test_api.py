"""Tests for the FastAPI endpoints (parse is the only one that doesn't need an LLM)."""

from fastapi.testclient import TestClient

from legacy_shift.api import app

client = TestClient(app)

SAMPLE_JAVA = """\
package com.example;

public class Greeter {
    private String name;

    public Greeter(String name) {
        this.name = name;
    }

    public String greet() {
        return "Hello, " + name + "!";
    }
}
"""


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_parse_endpoint():
    resp = client.post("/parse", json={"source_code": SAMPLE_JAVA})
    assert resp.status_code == 200
    data = resp.json()
    assert "Greeter" in data["summary"]
    assert data["class_count"] == 1
    assert data["method_count"] >= 1
    assert data["package"] == "com.example"


def test_parse_empty_source():
    resp = client.post("/parse", json={"source_code": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["class_count"] == 0


SAMPLE_COBOL = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. HELLOCALC.
       PROCEDURE DIVISION.
       MAIN-PARA.
           DISPLAY "Hello"
           STOP RUN."""


def test_parse_cobol():
    resp = client.post("/parse", json={"source_code": SAMPLE_COBOL, "source_language": "cobol"})
    assert resp.status_code == 200
    data = resp.json()
    assert "HELLOCALC" in data["summary"]
    assert data["class_count"] == 1
    assert data["method_count"] >= 1  # at least MAIN-PARA
    assert data["package"] == "HELLOCALC"


def test_stats_endpoint():
    resp = client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_runs" in data
    assert "success_rate" in data
    assert "avg_quality_score" in data


def test_migrations_endpoint():
    resp = client.get("/migrations?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert isinstance(data["runs"], list)
