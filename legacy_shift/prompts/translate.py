from langchain_core.prompts import ChatPromptTemplate

TRANSLATE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert polyglot programmer who translates legacy Java 8 "
            "code into clean, idiomatic Python 3.12+. You preserve exact business "
            "logic — every branch, every edge case — while using Pythonic idioms "
            "(dataclasses, type hints, properties, context managers, etc.).",
        ),
        (
            "human",
            "## Original Java Source\n```java\n{source_code}\n```\n\n"
            "## Plain-English Explanation\n{explanation}\n\n"
            "## Structural Summary\n{structure_summary}\n\n"
            "{few_shot_section}"
            "{feedback_section}"
            "Translate the Java code into a single Python module. Rules:\n"
            "- Preserve ALL public method signatures (Pythonised names: camelCase → snake_case).\n"
            "- Preserve all business logic, validations, and edge-case handling.\n"
            "- Use dataclasses or plain classes as appropriate.\n"
            "- Add Python type hints everywhere.\n"
            "- Do NOT add behaviour that isn't in the original code.\n\n"
            "Return ONLY the Python code inside a single ```python``` block.",
        ),
    ]
)

TRANSLATE_FEEDBACK_SECTION = (
    "## Previous Translation Attempt\n```python\n{previous_translation}\n```\n\n"
    "## Test Failures From Previous Attempt\n```\n{test_errors}\n```\n\n"
    "Fix the translation so that ALL tests pass. "
    "Only change what is necessary to fix the failures.\n\n"
)
