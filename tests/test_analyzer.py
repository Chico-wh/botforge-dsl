"""Tests for botforge.analyzer — DSL validation."""

import ast
import pytest

from botforge.analyzer import analyze_tree, BotForgeAnalyzer
from botforge.exceptions import AnalyzerError


def check(source: str) -> None:
    """Parse and analyze a source string."""
    tree = ast.parse(source)
    analyze_tree(tree)


def expect_error(source: str, match: str | None = None) -> None:
    with pytest.raises(AnalyzerError, match=match):
        check(source)


# ---------------------------------------------------------------------------
# Forbidden constructs
# ---------------------------------------------------------------------------

def test_analyzer_rejects_while():
    expect_error(
        "from botforge import Bot\nwhile True:\n    pass\n",
        match="while loops",
    )


def test_analyzer_rejects_for():
    expect_error(
        "from botforge import Bot\nfor i in range(10):\n    pass\n",
        match="for loops",
    )


def test_analyzer_rejects_lambda():
    expect_error(
        "from botforge import Bot\nf = lambda x: x\n",
        match="lambda",
    )


def test_analyzer_rejects_class():
    expect_error(
        "from botforge import Bot\nclass MyRobot:\n    pass\n",
        match="class definitions",
    )


def test_analyzer_rejects_async_function():
    expect_error(
        "from botforge import Bot\nasync def foo():\n    pass\n",
        match="async functions",
    )


# ---------------------------------------------------------------------------
# Import validation
# ---------------------------------------------------------------------------

def test_analyzer_rejects_plain_import():
    expect_error(
        "import os\n",
        match="Plain 'import'",
    )


def test_analyzer_rejects_foreign_from_import():
    expect_error(
        "from os import path\n",
        match="Importing from 'os'",
    )


def test_analyzer_accepts_botforge_import():
    # Should not raise
    check("from botforge import Bot, Wheels, Ultrasonic\n")


# ---------------------------------------------------------------------------
# Nested functions
# ---------------------------------------------------------------------------

def test_analyzer_rejects_nested_function():
    source = """\
from botforge import Bot
def outer():
    def inner():
        pass
"""
    expect_error(source, match="Nested function")


# ---------------------------------------------------------------------------
# Valid DSL passes analyzer
# ---------------------------------------------------------------------------

def test_analyzer_accepts_valid_dsl():
    source = """\
from botforge import Bot, Wheels, Ultrasonic

bot = Bot("rover")
bot.use(Wheels(left=(5, 6), right=(9, 10)))
front = bot.use(Ultrasonic("front", trigger=7, echo=8))

@bot.loop
def main():
    if front.distance < 20:
        bot.turn_left(speed=50)
    else:
        bot.forward(speed=80)
"""
    check(source)  # must not raise
