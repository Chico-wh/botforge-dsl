# BotForge DSL Reference — V0.1

The BotForge DSL is a **controlled subset of Python**. It looks like Python and is parsed using Python's native `ast` module, but only a specific set of constructs is allowed.

---

## Allowed Constructs

### Imports

Only imports from `botforge` are allowed:

```python
from botforge import Bot, Wheels, Ultrasonic, Servo
```

### Bot instantiation

```python
bot = Bot("robot_name")
```

The name becomes the output directory name and appears in generated code comments.

### Hardware components

```python
bot.use(Wheels(left=(pin1, pin2), right=(pin3, pin4)))
sensor = bot.use(Ultrasonic("name", trigger=pin, echo=pin))
servo = bot.use(Servo("name", pin=pin))
```

### Main loop

```python
@bot.loop
def main():
    ...
```

Exactly one function decorated with `@bot.loop` is required.

### Conditionals

```python
if sensor.distance < 20:
    bot.turn_left(speed=50)
else:
    bot.forward(speed=80)
```

Supported operators: `<`, `>`, `<=`, `>=`, `==`, `!=`

### Bot actions

```python
bot.forward(speed=80)
bot.backward(speed=60)
bot.turn_left(speed=50)
bot.turn_right(speed=50)
bot.stop()
```

### Servo actions

```python
servo.write(angle=90)
```

---

## Complete Valid Example

```python
from botforge import Bot, Wheels, Ultrasonic

bot = Bot("mini_rover")

bot.use(Wheels(left=(5, 6), right=(9, 10)))
front = bot.use(Ultrasonic("front", trigger=7, echo=8))

@bot.loop
def main():
    if front.distance < 20:
        bot.turn_left(speed=50)
    else:
        bot.forward(speed=80)
```

---

## Forbidden Constructs

The following will raise an `AnalyzerError`:

```python
# ❌ while loops
while True:
    pass

# ❌ for loops
for i in range(10):
    pass

# ❌ class definitions
class MyRobot:
    pass

# ❌ lambda
f = lambda x: x

# ❌ async
async def foo():
    pass

# ❌ arbitrary imports
import os
from time import sleep

# ❌ nested functions
@bot.loop
def main():
    def helper():   # not allowed
        pass
```

---

## Sensor Attribute Map

| DSL attribute | C++ translation |
|---------------|----------------|
| `sensor.distance` | `sensor.ping_cm()` |

---

## Planned (V0.2+)

- Multiple sensors in one program
- `elif` chains
- Sensor read caching
- Line sensor (`LineSensor`)
- IR remote
