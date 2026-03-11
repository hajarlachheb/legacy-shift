from langchain.prompts import ChatPromptTemplate

TEST_GEN_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a test engineering expert. You write thorough, deterministic "
            "pytest test suites that verify behavioural equivalence between legacy "
            "Java code and its Python translation. Every test must be self-contained "
            "and runnable with `pytest` without extra fixtures.",
        ),
        (
            "human",
            "## Original Java Source\n```java\n{source_code}\n```\n\n"
            "## Plain-English Explanation\n{explanation}\n\n"
            "## Structural Summary\n{structure_summary}\n\n"
            "Generate a **comprehensive** pytest test suite for a Python module "
            "named `translated.py` that is the direct translation of the Java code "
            "above.\n\n"
            "Requirements:\n"
            "- Cover every public method.\n"
            "- Include happy-path tests, edge cases, boundary values, and error "
            "cases.\n"
            "- Use descriptive test names (test_<method>_<scenario>).\n"
            "- Add brief docstrings explaining what each test verifies.\n"
            "- The test file must be self-contained — no external test fixtures.\n"
            "- Import the translated module as `from translated import *`.\n\n"
            "Return ONLY the Python test code inside a single ```python``` block.",
        ),
    ]
)
