# BotForge → C++ Library Mapping

## V0.1 Mapping Table

| BotForge DSL | IR Node | C++ Library | Generated C++ |
|---|---|---|---|
| `Bot("mini_rover")` | `BotProgram` | `Arduino.h` | `void setup()` / `void loop()` |
| `Wheels(left=(5,6), right=(9,10))` | `HardwareComponent(type="Wheels")` | custom class | `class Wheels { ... }; Wheels wheels(5,6,9,10);` |
| `Ultrasonic("front", trigger=7, echo=8)` | `HardwareComponent(type="Ultrasonic")` | `NewPing.h` | `NewPing front(7, 8, 200);` |
| `Servo("arm", pin=3)` | `HardwareComponent(type="Servo")` | `Servo.h` | `Servo arm; arm.attach(3);` |
| `front.distance` | `Condition(left="front.distance")` | `NewPing.h` | `front.ping_cm()` |
| `bot.forward(speed=80)` | `ActionCall(method="forward")` | custom Wheels | `wheels.forward(80)` |
| `bot.backward(speed=60)` | `ActionCall(method="backward")` | custom Wheels | `wheels.backward(60)` |
| `bot.turn_left(speed=50)` | `ActionCall(method="turn_left")` | custom Wheels | `wheels.turnLeft(50)` |
| `bot.turn_right(speed=50)` | `ActionCall(method="turn_right")` | custom Wheels | `wheels.turnRight(50)` |
| `bot.stop()` | `ActionCall(method="stop")` | custom Wheels | `wheels.stop()` |
| `servo.write(angle=90)` | `ActionCall(method="write")` | `Servo.h` | `arm.write(90)` |

---

## Why These Libraries?

### `Arduino.h`
The foundation of all Arduino sketches. Provides `setup()`, `loop()`, `analogWrite()`, `digitalWrite()`, `Serial`, and all standard Arduino functions.

### `NewPing.h`
The most popular Arduino library for HC-SR04 ultrasonic sensors. Chosen because:
- Clean API: `ping_cm()` returns distance in centimeters directly
- Handles timing, non-blocking pings, and noise filtering
- Well maintained and widely available via Arduino Library Manager

### `Servo.h`
The official Arduino servo library. Built-in, no installation required. Supports standard 180° PWM servos via `attach()` and `write()`.

---

## Future Libraries (Planned)

| Target | Library | Purpose |
|--------|---------|---------|
| Arduino | `AccelStepper.h` | Stepper motor control with acceleration |
| Arduino | `Wire.h` | I2C communication for sensors like MPU-6050 |
| Arduino | `Adafruit_BNO055.h` | IMU / orientation sensor |
| ESP32 | `WiFi.h` | Wi-Fi connectivity |
| ESP32 | `esp_now.h` | Peer-to-peer wireless |
| ROS 2 | `rclcpp` | ROS 2 C++ client library |
| ROS 2 | `geometry_msgs` | Twist messages for velocity commands |
| ROS 2 | `sensor_msgs` | LaserScan, Image, Range messages |
| ROS 2 + MCU | `micro_ros_arduino` | micro-ROS on Arduino/ESP32 |
| Vision | `opencv2/opencv.hpp` | Computer vision on companion computers |

---

## Why Not Translate All Python to C++?

Python and C++ have fundamentally different memory models, type systems, and runtime behaviors. A full Python-to-C++ transpiler would need to:

- Implement Python's garbage collector in C++
- Handle dynamic typing at runtime
- Implement Python's exception model
- Bundle the Python standard library

This is exactly what tools like Cython or Nuitka do — and they are enormously complex.

BotForge takes a different approach: instead of translating Python, it uses a **controlled DSL** where each construct has a known, safe C++ equivalent. The mapping is explicit, predictable, and generates clean idiomatic C++.
