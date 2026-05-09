# BotForge — Internal Architecture

## Overview

BotForge is a **transpiler pipeline**: it takes a controlled Python DSL as input and produces C++ code for embedded targets. The design is deliberately layered so that each stage can be understood, tested, and extended independently.

```
┌─────────────────────────────────────────────────────────────┐
│                     botforge build <file>                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                    ┌─────▼──────┐
                    │  Analyzer  │  ← AST validation (forbidden constructs)
                    └─────┬──────┘
                          │
                    ┌─────▼──────┐
                    │   Parser   │  ← AST → IR extraction
                    └─────┬──────┘
                          │
                    ┌─────▼──────┐
                    │     IR     │  ← BotProgram dataclasses (target-agnostic)
                    └─────┬──────┘
                          │
                    ┌─────▼──────┐
                    │ Generator  │  ← IR + Jinja2 templates → C++ files
                    └─────┬──────┘
                          │
               ┌──────────▼───────────┐
               │  output/<bot_name>/  │
               │  ├── main.cpp        │
               │  └── README.md       │
               └──────────────────────┘
```

---

## Stages

### 1. CLI (`botforge/cli.py`)

Entry point via Typer. Validates file existence, orchestrates the pipeline, and reports errors with Rich formatting.

### 2. Analyzer (`botforge/analyzer.py`)

Walks the raw Python AST and rejects any construct that is outside the BotForge DSL:
- `while`, `for`, `async`, `lambda`, `class` — all forbidden
- Only `from botforge import ...` is allowed
- No nested functions

This runs **before** the parser so users get clear error messages about unsupported code before any IR is constructed.

### 3. Parser (`botforge/parser.py`)

Extracts meaning from the AST and converts it into the IR. Responsible for:
- Finding `Bot("name")`
- Finding `bot.use(Wheels(...))`, `bot.use(Ultrasonic(...))`, etc.
- Finding the `@bot.loop` decorated function
- Converting `if/else` blocks and action calls into IR nodes

### 4. IR — Intermediate Representation (`botforge/ir.py`)

Pure Python dataclasses. Completely target-agnostic. All code generation reads from this, not from the original AST.

Key types:
- `BotProgram` — root node
- `HardwareComponent` — a physical sensor/actuator
- `LoopFunction` — the `@bot.loop` body
- `IfStatement`, `ActionCall`, `Condition` — statement nodes

### 5. Generator (`botforge/generator.py`)

Translates the IR into C++ using Jinja2 templates. Logic:
- Selects the correct template set based on `program.target`
- Translates DSL idioms (`front.distance` → `front.ping_cm()`)
- Translates `bot.forward(speed=80)` → `wheels.forward(80)`
- Renders `arduino_main.cpp.j2` and `README_GENERATED.md.j2`

### 6. Targets (`botforge/targets/`)

Metadata and configuration per target. Currently only `arduino.py`. New targets (ESP32, ROS 2) will be added here.

### 7. Templates (`botforge/templates/`)

Jinja2 `.j2` files that define the structure of the generated C++ code. Separating templates from logic makes it easy to change the output format without touching Python code.

---

## Adding a New Target

1. Create `botforge/targets/myplatform.py` with target metadata.
2. Create Jinja2 templates in `botforge/templates/myplatform_*.j2`.
3. Add a branch in `botforge/generator.py → BotForgeGenerator.generate()`.
4. Add target to `botforge/cli.py → targets()` command output.

## Adding a New Component

1. Add the DSL stub in `botforge/dsl/`.
2. Register it in `botforge/parser.py → COMPONENT_REGISTRY`.
3. Add translation logic in `botforge/generator.py`.
4. Update the Jinja2 template to render the component.
