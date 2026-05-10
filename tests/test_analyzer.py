"""Tests for botforge.analyzer"""

import ast
import pytest
from botforge.analyzer import analyze_tree, BotForgeAnalyzer
from botforge.exceptions import AnalyzerError


def check(source: str) -> None:
    analyze_tree(ast.parse(source))

def expect_error(source: str, match: str | None = None) -> None:
    with pytest.raises(AnalyzerError, match=match):
        check(source)

VALID = """\
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

# --- Forbidden constructs ---

def test_rejects_while():
    expect_error("from botforge import Bot\nwhile True:\n    pass\n", "while")

def test_rejects_for():
    expect_error("from botforge import Bot\nfor i in range(10):\n    pass\n", "for")

def test_rejects_lambda():
    expect_error("from botforge import Bot\nf = lambda x: x\n", "lambda")

def test_rejects_class():
    expect_error("from botforge import Bot\nclass Foo:\n    pass\n", "class")

def test_rejects_async():
    expect_error("from botforge import Bot\nasync def f():\n    pass\n", "async")

def test_rejects_try_except():
    expect_error(
        "from botforge import Bot\nbot=Bot('x')\ntry:\n    pass\nexcept:\n    pass\n",
        "try",
    )

def test_rejects_with():
    expect_error(
        "from botforge import Bot\nwith open('x') as f:\n    pass\n",
        "with",
    )

def test_rejects_list_comprehension():
    expect_error(
        "from botforge import Bot\nx = [i for i in range(10)]\n",
        "comprehension",
    )

def test_rejects_dict_comprehension():
    expect_error(
        "from botforge import Bot\nx = {k:k for k in range(5)}\n",
        "comprehension",
    )

# --- Forbidden calls ---

def test_rejects_eval():
    expect_error("from botforge import Bot\neval('1+1')\n", "eval")

def test_rejects_exec():
    expect_error("from botforge import Bot\nexec('pass')\n", "exec")

def test_rejects_open():
    expect_error("from botforge import Bot\nopen('file.txt')\n", "open")

# --- Import validation ---

def test_rejects_plain_import():
    expect_error("import os\n", "import")

def test_rejects_foreign_from_import():
    expect_error("from os import path\n", "os")

def test_accepts_botforge_import():
    check("from botforge import Bot, Wheels, Ultrasonic\n")  # must not raise

# --- Nested functions ---

def test_rejects_nested_function():
    expect_error(
        "from botforge import Bot\ndef outer():\n    def inner():\n        pass\n",
        "Nested",
    )

# --- Unknown bot method ---

def test_rejects_unknown_bot_method():
    expect_error(
        "from botforge import Bot\nbot=Bot('x')\n@bot.loop\ndef main():\n    bot.fly(speed=1)\n",
        "fly",
    )

# --- Unknown component in bot.use() ---

def test_rejects_unknown_component():
    expect_error(
        "from botforge import Bot\nbot=Bot('x')\nbot.use(Rocket(thrust=9000))\n",
        "Rocket",
    )

# --- Valid DSL passes ---

def test_accepts_valid_dsl():
    check(VALID)
