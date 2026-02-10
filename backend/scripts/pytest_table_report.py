#!/usr/bin/env python3
"""Render pytest JUnit XML results as an aligned table."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


LINE_WIDTH = 160


def hr(char: str = "=") -> None:
    print(char * LINE_WIDTH)


def extract_failure_message(case: ET.Element) -> str:
    failure = case.find("failure")
    error = case.find("error")
    node = failure or error
    if node is None:
        return ""

    message = (node.attrib.get("message") or "").strip()
    if message:
        return message

    text = (node.text or "").strip()
    if not text:
        return ""

    return text.splitlines()[0].strip()


def parse_cases(xml_path: Path) -> tuple[list[dict], float]:
    root = ET.parse(xml_path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))

    cases: list[dict] = []
    total_time = 0.0

    for suite in suites:
        total_time += float(suite.attrib.get("time", 0.0))
        for case in suite.findall(".//testcase"):
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            test_id = f"{classname}::{name}" if classname else name
            duration = float(case.attrib.get("time", 0.0))

            status = "PASSED"
            if case.find("failure") is not None:
                status = "FAILED"
            elif case.find("error") is not None:
                status = "ERROR"
            elif case.find("skipped") is not None:
                status = "SKIPPED"

            cases.append(
                {
                    "id": test_id,
                    "status": status,
                    "duration": duration,
                    "message": extract_failure_message(case),
                }
            )

    return cases, total_time


def print_table(cases: list[dict], total_time: float) -> None:
    total = len(cases)
    passed = sum(1 for case in cases if case["status"] == "PASSED")
    failed = sum(1 for case in cases if case["status"] == "FAILED")
    errors = sum(1 for case in cases if case["status"] == "ERROR")
    skipped = sum(1 for case in cases if case["status"] == "SKIPPED")

    hr("=")
    print(f"{'#':>3} {'%':>6}  {'Estado':<7} {'Tiempo':>8}  Test")
    hr("=")

    for index, case in enumerate(cases, 1):
        pct = (index / total * 100.0) if total else 0.0
        print(
            f"{index:>3} {pct:>5.1f}%  {case['status']:<7} "
            f"{case['duration']:>7.3f}s  {case['id']}"
        )

    hr("=")
    print(
        f"Total: {total} | Passed: {passed} | Failed: {failed} | "
        f"Errors: {errors} | Skipped: {skipped} | Time: {total_time:.2f}s"
    )
    hr("=")

    failed_cases = [
        case
        for case in cases
        if case["status"] in {"FAILED", "ERROR"}
    ]
    if not failed_cases:
        return

    print("\nFallas y errores")
    hr("-")
    for case in failed_cases:
        print(f"- {case['status']}: {case['id']}")
        if case["message"]:
            print(f"  {case['message']}")
    hr("-")


def main() -> int:
    xml_arg = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pytest.xml"
    xml_path = Path(xml_arg)

    if not xml_path.exists():
        print(f"No se encontró el reporte JUnit XML: {xml_path}")
        return 0

    cases, total_time = parse_cases(xml_path)
    print_table(cases, total_time)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
