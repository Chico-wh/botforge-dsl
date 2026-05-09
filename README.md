# BotForge

> \*\*Write robot behavior in a Python-inspired DSL. Generate Arduino C++.\*\*  
> \*\*Escreva o comportamento do robô em uma DSL inspirada em Python. Gere C++ para Arduino.\*\*  
>
> A Python DSL compiler for Arduino, ESP32, and ROS 2 — focused on robotics.  
> Um compilador de DSL Python para Arduino, ESP32 e ROS 2 — focado em robótica.

[!\[Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[!\[License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
\[!\[Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

> \*\*Experimental project.\*\* BotForge is in active development. The DSL and IR may change between versions.  
> \*\*Projeto experimental.\*\* O BotForge está em desenvolvimento ativo. A DSL e a IR podem mudar entre versões.

\---

## What is BotForge? / O que é o BotForge?

BotForge is a **mini-framework and CLI** that lets you write robot logic in a Python-inspired DSL and compile it to idiomatic C++ for embedded targets, starting with Arduino.

O BotForge é um **mini-framework e CLI** que permite escrever lógica de robôs em uma DSL inspirada em Python e compilá-la para C++ idiomático para plataformas embarcadas, começando pelo Arduino.

You write this:

Você escreve isto:

```python
from botforge import Bot, Wheels, Ultrasonic

bot = Bot("mini\_rover")

bot.use(Wheels(left=(5, 6), right=(9, 10)))
front = bot.use(Ultrasonic("front", trigger=7, echo=8))

@bot.loop
def main():
    if front.distance < 20:
        bot.turn\_left(speed=50)
    else:
        bot.forward(speed=80)
```

BotForge generates this:

O BotForge gera isto:

```cpp
#include <Arduino.h>
#include <NewPing.h>

#define MAX\_DISTANCE 200

NewPing front(7, 8, MAX\_DISTANCE);

class Wheels {
public:
    Wheels(int leftPin1, int leftPin2, int rightPin1, int rightPin2)
        : leftPin1(leftPin1), leftPin2(leftPin2),
          rightPin1(rightPin1), rightPin2(rightPin2) {}

    void forward(int speed) { ... }
    void turnLeft(int speed) { ... }
    void stop() { ... }

private:
    int leftPin1, leftPin2, rightPin1, rightPin2;
};

Wheels wheels(5, 6, 9, 10);

void setup() {}

void loop() {
    if (front.ping\_cm() < 20) {
        wheels.turnLeft(50);
    } else {
        wheels.forward(80);
    }
}
```

\---

## The Problem / O Problema

Writing Arduino C++ for robots is repetitive and error-prone:

Escrever C++ Arduino para robôs é repetitivo e propenso a erros:

* You manually manage pin numbers scattered across the file  
Você gerencia manualmente números de pinos espalhados pelo arquivo
* Every project re-implements the same `Wheels` class  
Todo projeto reimplementa a mesma classe `Wheels`
* Sensor API differences (`ping\_cm()` vs `analogRead()`) leak into your logic  
Diferenças entre APIs de sensores (`ping\_cm()` vs `analogRead()`) vazam para a lógica do robô
* There's no abstraction layer — hardware details and behavior are mixed  
Não há camada de abstração — detalhes de hardware e comportamento ficam misturados

\---

## The Solution / A Solução

BotForge separates **what the robot does** from **how the hardware works**:

O BotForge separa **o que o robô faz** de **como o hardware funciona**:

* You describe behavior in a clean Python-inspired DSL  
Você descreve o comportamento em uma DSL limpa inspirada em Python
* BotForge maps abstractions to real C++ libraries  
O BotForge mapeia abstrações para bibliotecas C++ reais
* Generated code uses `NewPing`, `Servo.h`, and other proven libraries  
O código gerado usa `NewPing`, `Servo.h` e outras bibliotecas consolidadas
* You get clean, readable, idiomatic C++ output  
Você recebe uma saída C++ limpa, legível e idiomática

\---

## What BotForge IS / O que o BotForge É

* A **DSL compiler** for a controlled subset of Python  
Um **compilador de DSL** para um subconjunto controlado de Python
* A **code generator** that produces idiomatic C++ using real libraries  
Um **gerador de código** que produz C++ idiomático usando bibliotecas reais
* A **hardware abstraction layer** for robotics  
Uma **camada de abstração de hardware** para robótica
* An **extensible framework** for adding new targets and components  
Um **framework extensível** para adicionar novos targets e componentes

\---

## What BotForge is NOT / O que o BotForge NÃO é

* ❌ A Python-to-C++ translator. It does not translate arbitrary Python.  
❌ Um tradutor Python-para-C++. Ele não traduz Python arbitrário.
* ❌ A Python runtime on Arduino  
❌ Um runtime Python no Arduino
* ❌ Cython, Nuitka, or MicroPython  
❌ Cython, Nuitka ou MicroPython
* ❌ A general-purpose transpiler  
❌ Um transpiler de propósito geral

\---

## Why Not Translate All Python? / Por que não traduzir Python inteiro?

A full Python-to-C++ transpiler would need to:

Um transpiler completo de Python para C++ precisaria:

* Implement Python's garbage collector in C++  
Implementar o garbage collector do Python em C++
* Handle dynamic typing, introspection, and the full standard library  
Lidar com tipagem dinâmica, introspecção e toda a biblioteca padrão
* Bundle the Python runtime  
Embutir o runtime do Python

This is what Nuitka and Cython do — and they are enormous, complex tools.

É isso que Nuitka e Cython fazem — e eles são ferramentas enormes e complexas.

BotForge takes the opposite approach: **a small, explicit DSL where every construct has a known C++ equivalent**. The mapping is intentional, documented, and produces clean output.

O BotForge segue o caminho oposto: **uma DSL pequena e explícita em que cada construção tem um equivalente C++ conhecido**. O mapeamento é intencional, documentado e produz uma saída limpa.

\---

## How It Works — Architecture / Como funciona — Arquitetura

```text
Python DSL (.py)
      │
      ▼
  Analyzer          ← Validates: rejects while, for, lambda, class, etc.
      │                Valida: rejeita while, for, lambda, class etc.
      ▼
   Parser           ← Walks the AST, extracts bot config, components, loop
      │                Percorre a AST, extrai configuração, componentes e loop
      ▼
     IR             ← BotProgram dataclasses (target-agnostic)
      │                Dataclasses BotProgram independentes de target
      ▼
  Generator         ← Translates IR + Jinja2 templates → C++
      │                Traduz IR + templates Jinja2 → C++
      ▼
Target: Arduino     ← Knows about Arduino.h, NewPing.h, Servo.h
      │                Conhece Arduino.h, NewPing.h, Servo.h
      ▼
  main.cpp          ← Ready to flash
                       Pronto para gravar na placa
```

### Compilation Pipeline / Pipeline de Compilação

|Stage / Etapa|Input / Entrada|Output / Saída|File / Arquivo|
|-|-|-|-|
|Analyzer / Analisador|`.py` source / código `.py`|✅ or AnalyzerError / ✅ ou AnalyzerError|`analyzer.py`|
|Parser|`.py` AST|`BotProgram` IR|`parser.py`|
|IR|—|dataclasses|`ir.py`|
|Generator / Gerador|`BotProgram`|`main.cpp` + `README.md`|`generator.py`|
|Target|template context / contexto do template|rendered C++ / C++ renderizado|`targets/arduino.py`|

\---

## DSL → IR → C++ Mapping / Mapeamento DSL → IR → C++

|BotForge DSL|IR Node|C++ Library / Biblioteca C++|Generated C++ / C++ gerado|
|-|-|-|-|
|`Bot("mini\_rover")`|`BotProgram`|`Arduino.h`|`setup()` / `loop()`|
|`Wheels(left=(5,6), right=(9,10))`|`HardwareComponent`|custom class / classe customizada|`class Wheels {...}`|
|`Ultrasonic("front", trigger=7, echo=8)`|`HardwareComponent`|`NewPing.h`|`NewPing front(7,8,200)`|
|`Servo("arm", pin=3)`|`HardwareComponent`|`Servo.h`|`Servo arm; arm.attach(3)`|
|`front.distance`|`Condition.left`|`NewPing.h`|`front.ping\_cm()`|
|`bot.forward(speed=80)`|`ActionCall`|custom Wheels / Wheels customizado|`wheels.forward(80)`|
|`bot.turn\_left(speed=50)`|`ActionCall`|custom Wheels / Wheels customizado|`wheels.turnLeft(50)`|
|`bot.stop()`|`ActionCall`|custom Wheels / Wheels customizado|`wheels.stop()`|
|`servo.write(angle=90)`|`ActionCall`|`Servo.h`|`arm.write(90)`|

\---

## Installation / Instalação

```bash
# Clone the repo
# Clone o repositório
git clone https://github.com/yourname/botforge
cd botforge

# Install in editable mode with dev dependencies
# Instale em modo editável com dependências de desenvolvimento
pip install -e ".\[dev]"
```

\---

## Usage / Uso

### Build a robot / Gerar um robô

```bash
botforge build examples/obstacle\_avoidance.py --target arduino
```

Output / Saída:

```text
output/mini\_rover/
├── main.cpp
└── README\_GENERATED.md
```

### List targets / Listar targets

```bash
botforge targets
```

\---

## DSL Reference (V0.1) / Referência da DSL (V0.1)

### Allowed / Permitido

```python
from botforge import Bot, Wheels, Ultrasonic, Servo

bot = Bot("robot\_name")

bot.use(Wheels(left=(pin1, pin2), right=(pin3, pin4)))
sensor = bot.use(Ultrasonic("name", trigger=pin, echo=pin))
servo = bot.use(Servo("name", pin=pin))

@bot.loop
def main():
    if sensor.distance < 20:
        bot.turn\_left(speed=50)
    else:
        bot.forward(speed=80)
```

### Forbidden / Proibido

```python
while True: ...          # ❌ loops not allowed / loops não são permitidos
for i in range(10): ...  # ❌
class MyBot: ...         # ❌ no custom classes / sem classes customizadas
import os                # ❌ no arbitrary imports / sem imports arbitrários
lambda x: x              # ❌ no lambdas / sem lambdas
async def foo(): ...     # ❌ no async / sem async
```

\---

## Adding a New Target / Adicionando um Novo Target

1. Create `botforge/targets/myplatform.py` with target metadata  
Crie `botforge/targets/myplatform.py` com metadados do target
2. Add Jinja2 templates in `botforge/templates/myplatform\_\*.j2`  
Adicione templates Jinja2 em `botforge/templates/myplatform\_\*.j2`
3. Add a branch in `generator.py → BotForgeGenerator.generate()`  
Adicione uma ramificação em `generator.py → BotForgeGenerator.generate()`
4. Register in `cli.py → targets()`  
Registre em `cli.py → targets()`

\---

## Adding a New Sensor / Adicionando um Novo Sensor

1. Add DSL stub in `botforge/dsl/sensors.py`  
Adicione o stub da DSL em `botforge/dsl/sensors.py`
2. Register in `parser.py → COMPONENT\_REGISTRY`  
Registre em `parser.py → COMPONENT\_REGISTRY`
3. Add C++ translation in `generator.py → translate\_condition\_left()`  
Adicione a tradução C++ em `generator.py → translate\_condition\_left()`
4. Update the template  
Atualize o template

\---

## Adding a New Action / Adicionando uma Nova Ação

1. Add translation in `generator.py → translate\_action()`  
Adicione a tradução em `generator.py → translate\_action()`
2. Add a movement mapping in `BOT\_TO\_WHEELS\_MAP` or handle the new target directly  
Adicione um mapeamento de movimento em `BOT\_TO\_WHEELS\_MAP` ou trate o novo target diretamente

\---

## Running Tests / Rodando os Testes

```bash
pytest
pytest --cov=botforge
```

\---

## Architecture in Layers / Arquitetura em Camadas

```text
┌─────────────────────────────────────┐
│         User DSL (.py file)         │  ← High-level, Python-like
│         DSL do usuário (.py)        │    Alto nível, estilo Python
├─────────────────────────────────────┤
│    Analyzer + Parser (AST layer)    │  ← Validation + extraction
│    Analyzer + Parser (camada AST)   │    Validação + extração
├─────────────────────────────────────┤
│  Intermediate Representation (IR)   │  ← Target-agnostic data model
│  Representação Intermediária (IR)   │    Modelo independente de target
├─────────────────────────────────────┤
│   Generator + Templates (Jinja2)    │  ← Target-specific rendering
│   Gerador + Templates (Jinja2)      │    Renderização específica por target
├─────────────────────────────────────┤
│      C++ Output (main.cpp)          │  ← Low-level, idiomatic C++
│      Saída C++ (main.cpp)           │    Baixo nível, C++ idiomático
└─────────────────────────────────────┘
```

### High Level vs Low Level / Alto Nível vs Baixo Nível

|Concept / Conceito|High Level (DSL) / Alto Nível (DSL)|Low Level (C++) / Baixo Nível (C++)|
|-|-|-|
|Distance check / Verificação de distância|`front.distance < 20`|`front.ping\_cm() < 20`|
|Turn left / Virar à esquerda|`bot.turn\_left(speed=50)`|`wheels.turnLeft(50)`|
|Move forward / Avançar|`bot.forward(speed=80)`|`wheels.forward(80)`|
|Sensor init / Inicialização de sensor|`Ultrasonic("front", trigger=7, echo=8)`|`NewPing front(7, 8, 200)`|

### Why AST + IR + Templates? / Por que AST + IR + Templates?

* **AST** — Python's native `ast` module gives us a structured tree without writing a parser from scratch  
**AST** — o módulo nativo `ast` do Python fornece uma árvore estruturada sem precisar escrever um parser do zero
* **IR** — decoupling parsing from generation means the same IR can target Arduino, ESP32, and ROS 2  
**IR** — separar parsing de geração permite que a mesma IR gere código para Arduino, ESP32 e ROS 2
* **Templates** — Jinja2 templates separate C++ structure from Python logic; changing the output format doesn't require touching the compiler  
**Templates** — templates Jinja2 separam a estrutura C++ da lógica Python; mudar o formato de saída não exige alterar o compilador

\---

## Limitations (V0.1) / Limitações (V0.1)

* Only `if/else`, no `elif`  
Apenas `if/else`, sem `elif`
* Only one `@bot.loop` function  
Apenas uma função `@bot.loop`
* No variables inside the loop  
Sem variáveis dentro do loop
* No arithmetic expressions  
Sem expressões aritméticas
* Only keyword arguments in actions, such as `speed=80`  
Apenas argumentos nomeados nas ações, como `speed=80`
* Only Arduino target  
Apenas target Arduino

\---

## Roadmap

|Version / Versão|Features / Recursos|
|-|-|
|V0.1|Arduino, Wheels, Ultrasonic, if/else ✅|
|V0.2|Servo, multiple sensors, better errors / Servo, múltiplos sensores, erros melhores|
|V0.3|ESP32 target, Wi-Fi / target ESP32, Wi-Fi|
|V0.4|AccelStepper, I2C sensors / AccelStepper, sensores I2C|
|V0.5|ROS 2 target, rclcpp nodes / target ROS 2, nodes rclcpp|
|V0.6|OpenCV C++ target / target OpenCV C++|
|V1.0|Stable DSL, full docs, real examples / DSL estável, documentação completa, exemplos reais|

Full roadmap / Roadmap completo: [docs/roadmap.md](docs/roadmap.md)

\---

## Next Steps: ESP32, ROS 2, OpenCV / Próximos Passos: ESP32, ROS 2, OpenCV

### ESP32 (V0.3)

The ESP32 target will generate code using `ledcWrite()` for PWM instead of `analogWrite()`, and optionally include Wi-Fi boilerplate. PlatformIO `platformio.ini` will also be generated.

O target ESP32 vai gerar código usando `ledcWrite()` para PWM em vez de `analogWrite()`, e opcionalmente incluir boilerplate de Wi-Fi. Um `platformio.ini` também será gerado.

### ROS 2 (V0.5)

The ROS 2 target will generate a complete `rclcpp` node with `CMakeLists.txt` and `package.xml`. The `@bot.loop` function becomes a timer callback. `bot.forward()` publishes a `geometry\_msgs::Twist` message.

O target ROS 2 vai gerar um node `rclcpp` completo com `CMakeLists.txt` e `package.xml`. A função `@bot.loop` vira um callback de timer. `bot.forward()` publica uma mensagem `geometry\_msgs::Twist`.

### OpenCV (V0.6)

The vision target generates C++ for companion computers such as Raspberry Pi and Jetson Nano. Camera components map to `cv::VideoCapture`, and detection actions map to OpenCV processing pipelines.

O target de visão gera C++ para computadores auxiliares, como Raspberry Pi e Jetson Nano. Componentes de câmera mapeiam para `cv::VideoCapture`, e ações de detecção mapeiam para pipelines de processamento com OpenCV.

\---

## Contributing / Contribuindo

BotForge is designed to be hackable. The codebase is small and each module has a single clear responsibility. See [docs/architecture.md](docs/architecture.md) to understand the internals.

O BotForge foi projetado para ser fácil de modificar. A base de código é pequena e cada módulo tem uma responsabilidade clara. Veja [docs/architecture.md](docs/architecture.md) para entender o funcionamento interno.

\---

## License / Licença

MIT — see [LICENSE](LICENSE).  
MIT — veja [LICENSE](LICENSE).

