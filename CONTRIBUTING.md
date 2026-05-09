Contributing to BotForge
Thank you for your interest in contributing to BotForge.
BotForge is an experimental Python-inspired robotics DSL compiler that generates Arduino C++ code. The project is still in its early stages, so contributions are especially valuable when they improve correctness, documentation, tests, or the clarity of the DSL.
Before contributing, please read this guide so changes stay consistent with the project's goals and architecture.
---
Project Philosophy
BotForge is not a general Python-to-C++ transpiler.
It is a small, explicit DSL where every supported construct has a known C++ equivalent. Contributions should preserve that principle:
Keep the DSL intentionally limited and predictable
Prefer explicit mappings over magical behavior
Keep parsing, validation, IR, and code generation separate
Generate clean, idiomatic C++ using real embedded libraries
Avoid adding features that make BotForge behave like full Python
If a feature makes the DSL significantly more dynamic or harder to validate statically, it probably does not belong in the current version.
---
Ways to Contribute
You can help by:
Reporting bugs
Improving documentation
Adding tests
Improving error messages
Adding examples
Extending the DSL carefully
Adding support for new sensors or actions
Working on future targets such as ESP32 or ROS 2
For larger changes, please open an issue first so the design can be discussed before implementation begins. Humanity has already produced enough code that nobody asked for.
---
Development Setup
1. Fork and clone the repository
```bash
git clone https://github.com/chico-wh/botforge.git
cd botforge
```
2. Create a virtual environment
```bash
python -m venv .venv
```
Activate it:
Linux / macOS
```bash
source .venv/bin/activate
```
Windows PowerShell
```powershell
.venv\Scripts\Activate.ps1
```
3. Install the project in editable mode
```bash
pip install -e ".[dev]"
```
4. Run the test suite
```bash
pytest
```
You can also run coverage:
```bash
pytest --cov=botforge
```
---
Recommended Workflow
1. Create a branch
Use a descriptive branch name:
```bash
git checkout -b feat/add-servo-example
```
Examples:
```text
feat/add-servo-support
fix/reject-invalid-imports
docs/improve-dsl-reference
test/add-generator-coverage
```
2. Make your changes
Keep changes focused. A pull request should solve one clear problem whenever possible.
3. Run tests before committing
```bash
pytest
```
If your change affects code generation, also verify the build command manually:
```bash
botforge build examples/obstacle_avoidance.py --target arduino
```
4. Commit with a clear message
Examples:
```text
feat: add servo action translation
fix: reject unsupported loop syntax
docs: clarify DSL limitations
test: add analyzer coverage for invalid imports
```
5. Open a pull request
Your pull request should explain:
What changed
Why it changed
How it was tested
Whether it affects the DSL, IR, generated C++, or documentation
---
Contribution Rules
Keep the Architecture Clean
BotForge is organized around a compilation pipeline:
```text
Python DSL
   ↓
Analyzer
   ↓
Parser
   ↓
IR
   ↓
Generator
   ↓
Target-specific C++ output
```
Please keep responsibilities separated:
Module	Responsibility
`analyzer.py`	Reject unsupported syntax before parsing
`parser.py`	Walk the AST and build the IR
`ir.py`	Define target-agnostic dataclasses
`generator.py`	Coordinate code generation
`targets/`	Store target-specific behavior
`templates/`	Store Jinja2 output templates
`dsl/`	Define the public DSL surface
Avoid placing target-specific rendering logic inside the parser or analyzer.
---
DSL Guidelines
The current DSL is intentionally small.
Currently Supported
`Bot(...)`
`Wheels(...)`
`Ultrasonic(...)`
`Servo(...)`
`@bot.loop`
`if/else`
simple sensor comparisons
robot actions such as:
`bot.forward(...)`
`bot.backward(...)`
`bot.turn_left(...)`
`bot.turn_right(...)`
`bot.stop()`
Currently Unsupported
arbitrary Python execution
`while`
`for`
`elif`
nested functions
custom classes
dynamic imports
list comprehensions
lambdas
`async`
`try/except`
unrestricted expressions
When adding new syntax, make sure:
The syntax can be statically validated
It has a clear IR representation
It maps predictably to generated C++
It is documented
It is covered by tests
---
Adding a New Sensor
When adding support for a new sensor:
Add or extend the DSL stub in `botforge/dsl/`
Register the component in the parser
Add an IR representation if necessary
Add target-specific translation logic
Update the Jinja2 template
Add tests
Update the documentation and DSL mapping table
A new sensor should not be added only at the template level. If the IR does not understand it, the architecture is being bypassed, and that road leads to sadness.
---
Adding a New Action
When adding a new action:
Define the supported DSL form
Validate it in the analyzer or parser as appropriate
Represent it in the IR
Translate it in the generator or target implementation
Add generated C++ coverage in tests
Update the README and DSL reference
---
Adding a New Target
When adding a new target such as ESP32 or ROS 2:
Create a target module in `botforge/targets/`
Add target-specific templates
Register the target in the CLI
Reuse the existing IR whenever possible
Keep target-specific assumptions out of the parser
Add dedicated tests
Document the target, supported features, and limitations
The same DSL should ideally be able to produce different outputs without requiring a separate parser for each platform.
---
Testing Requirements
Please add or update tests when changing behavior.
At minimum, tests should cover:
valid parsing
invalid syntax rejection
correct IR generation
generated C++ output
CLI behavior when relevant
Useful test areas include:
```text
tests/test_parser.py
tests/test_analyzer.py
tests/test_generator.py
tests/test_examples.py
```
If a bug is fixed, add a regression test when practical.
---
Documentation Requirements
If your contribution changes behavior, update the relevant documentation:
`README.md`
`docs/architecture.md`
`docs/dsl-reference.md`
`docs/cplusplus-libraries-map.md`
`docs/roadmap.md`
Documentation matters here because BotForge is partly about making mappings explicit:
```text
DSL → IR → C++ library → generated C++
```
If the mapping changes, the docs should change too.
---
Pull Request Checklist
Before opening a pull request, please confirm:
[ ] The change is focused and clearly scoped
[ ] Tests were added or updated when necessary
[ ] `pytest` passes locally
[ ] Generated C++ was checked when relevant
[ ] Documentation was updated when behavior changed
[ ] The change preserves the controlled DSL philosophy
[ ] The pull request description explains what changed and why
---
Reporting Bugs
When opening a bug report, please include:
A short description of the issue
The DSL input file that triggered it
The expected behavior
The actual behavior
Any traceback or generated C++ output
Your Python version
Your operating system
Minimal reproducible examples are deeply appreciated. They save everyone from decoding half a novel to find one missing comma.
---
Feature Requests
Feature requests are welcome, especially when they include:
The problem being solved
A proposed DSL syntax
The expected IR shape, if relevant
The expected generated C++ output
Why the feature fits BotForge's scope
Please avoid requests that require BotForge to become a full Python interpreter or a general-purpose transpiler. Those projects already exist, and they are enormous for reasons best respected from a safe distance.
---
Code Style
Use clear, descriptive names
Prefer small, focused functions
Keep modules single-purpose
Use type hints where they improve clarity
Prefer dataclasses for IR nodes
Avoid unnecessary cleverness
Write comments when they explain intent, not when they repeat obvious code
---
License
By contributing to BotForge, you agree that your contributions will be licensed under the same terms as the project: the MIT License.
---
Questions and Discussion
For design questions, larger proposals, or uncertain changes, open an issue before starting implementation.
That keeps the project coherent, reduces duplicated effort, and prevents all of us from learning the same painful lesson through different branches.