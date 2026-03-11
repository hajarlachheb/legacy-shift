"""Tree-sitter based Java 8 parser.

Extracts structural information (classes, methods, fields, imports) from Java
source files so the LLM can receive rich context alongside raw source code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser


JAVA_LANGUAGE = Language(tsjava.language())


@dataclass
class MethodInfo:
    name: str
    return_type: str
    parameters: list[str]
    body: str
    start_line: int
    end_line: int


@dataclass
class ClassInfo:
    name: str
    superclass: str | None
    interfaces: list[str]
    fields: list[str]
    methods: list[MethodInfo]


@dataclass
class ParsedCode:
    """Structured representation of a Java source file."""

    raw_source: str
    package: str | None = None
    imports: list[str] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)

    def summary(self) -> str:
        """One-paragraph structural summary suitable for LLM context."""
        parts: list[str] = []
        if self.package:
            parts.append(f"Package: {self.package}")
        if self.imports:
            parts.append(f"Imports: {', '.join(self.imports)}")
        for cls in self.classes:
            meths = ", ".join(m.name for m in cls.methods)
            parts.append(
                f"Class `{cls.name}` "
                f"(extends {cls.superclass or 'Object'}, "
                f"implements [{', '.join(cls.interfaces)}]) "
                f"with fields [{', '.join(cls.fields)}] "
                f"and methods [{meths}]"
            )
        return "\n".join(parts)


class JavaParser:
    """Wraps Tree-sitter to parse Java source into structured data."""

    def __init__(self) -> None:
        self.parser = Parser(JAVA_LANGUAGE)

    def parse(self, source: str) -> ParsedCode:
        tree = self.parser.parse(bytes(source, "utf-8"))
        root = tree.root_node
        result = ParsedCode(raw_source=source)

        for child in root.children:
            node_type = child.type
            if node_type == "package_declaration":
                result.package = self._node_text(child, source).replace("package ", "").rstrip(";").strip()
            elif node_type == "import_declaration":
                result.imports.append(
                    self._node_text(child, source).replace("import ", "").rstrip(";").strip()
                )
            elif node_type == "class_declaration":
                result.classes.append(self._parse_class(child, source))

        return result

    def _parse_class(self, node, source: str) -> ClassInfo:
        name = ""
        superclass = None
        interfaces: list[str] = []
        fields: list[str] = []
        methods: list[MethodInfo] = []

        for child in node.children:
            if child.type == "identifier":
                name = self._node_text(child, source)
            elif child.type == "superclass":
                for sub in child.children:
                    if sub.type == "type_identifier":
                        superclass = self._node_text(sub, source)
            elif child.type == "super_interfaces":
                for sub in child.children:
                    if sub.type == "type_list":
                        interfaces = [
                            self._node_text(t, source)
                            for t in sub.children
                            if t.type == "type_identifier"
                        ]
            elif child.type == "class_body":
                for member in child.children:
                    if member.type == "field_declaration":
                        fields.append(self._node_text(member, source).rstrip(";").strip())
                    elif member.type == "method_declaration":
                        methods.append(self._parse_method(member, source))

        return ClassInfo(
            name=name,
            superclass=superclass,
            interfaces=interfaces,
            fields=fields,
            methods=methods,
        )

    def _parse_method(self, node, source: str) -> MethodInfo:
        name = ""
        return_type = "void"
        parameters: list[str] = []
        body = ""
        for child in node.children:
            if child.type == "identifier":
                name = self._node_text(child, source)
            elif child.type in ("type_identifier", "void_type", "integral_type", "boolean_type", "generic_type"):
                return_type = self._node_text(child, source)
            elif child.type == "formal_parameters":
                for param in child.children:
                    if param.type == "formal_parameter":
                        parameters.append(self._node_text(param, source))
            elif child.type == "block":
                body = self._node_text(child, source)

        return MethodInfo(
            name=name,
            return_type=return_type,
            parameters=parameters,
            body=body,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
        )

    @staticmethod
    def _node_text(node, source: str) -> str:
        return source[node.start_byte : node.end_byte]
