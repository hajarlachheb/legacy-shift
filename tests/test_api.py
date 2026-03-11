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
