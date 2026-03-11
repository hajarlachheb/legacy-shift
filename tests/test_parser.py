"""Tests for the Tree-sitter Java parser."""

from legacy_shift.parser.ast_parser import JavaParser


SAMPLE_JAVA = """\
package com.example.demo;

import java.util.List;
import java.util.Map;

public class Calculator {

    private int memory;

    public Calculator() {
        this.memory = 0;
    }

    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }

    public void storeResult(int value) {
        this.memory = value;
    }

    public int getMemory() {
        return memory;
    }
}
"""


def test_parse_extracts_package():
    parser = JavaParser()
    result = parser.parse(SAMPLE_JAVA)
    assert result.package == "com.example.demo"


def test_parse_extracts_imports():
    parser = JavaParser()
    result = parser.parse(SAMPLE_JAVA)
    assert "java.util.List" in result.imports
    assert "java.util.Map" in result.imports
    assert len(result.imports) == 2


def test_parse_extracts_class_name():
    parser = JavaParser()
    result = parser.parse(SAMPLE_JAVA)
    assert len(result.classes) == 1
    assert result.classes[0].name == "Calculator"


def test_parse_extracts_methods():
    parser = JavaParser()
    result = parser.parse(SAMPLE_JAVA)
    cls = result.classes[0]
    method_names = [m.name for m in cls.methods]
    assert "add" in method_names
    assert "subtract" in method_names
    assert "storeResult" in method_names
    assert "getMemory" in method_names


def test_parse_extracts_fields():
    parser = JavaParser()
    result = parser.parse(SAMPLE_JAVA)
    cls = result.classes[0]
    assert len(cls.fields) >= 1
    assert any("memory" in f for f in cls.fields)


def test_parse_method_parameters():
    parser = JavaParser()
    result = parser.parse(SAMPLE_JAVA)
    cls = result.classes[0]
    add_method = next(m for m in cls.methods if m.name == "add")
    assert len(add_method.parameters) == 2


def test_summary_contains_class_info():
    parser = JavaParser()
    result = parser.parse(SAMPLE_JAVA)
    summary = result.summary()
    assert "Calculator" in summary
    assert "add" in summary
    assert "Package: com.example.demo" in summary


def test_parse_empty_source():
    parser = JavaParser()
    result = parser.parse("")
    assert result.classes == []
    assert result.imports == []
    assert result.package is None


def test_raw_source_preserved():
    parser = JavaParser()
    result = parser.parse(SAMPLE_JAVA)
    assert result.raw_source == SAMPLE_JAVA
