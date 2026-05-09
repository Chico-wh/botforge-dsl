# BotForge Roadmap

## V0.1 — Arduino Foundation ✅ (current)

- [x] Python DSL with `Bot`, `Wheels`, `Ultrasonic`
- [x] AST analyzer with forbidden construct detection
- [x] IR dataclasses (`BotProgram`, `HardwareComponent`, `IfStatement`, `ActionCall`)
- [x] Jinja2 template-based C++ generation
- [x] `main.cpp` + `README_GENERATED.md` output
- [x] `botforge build` CLI command
- [x] Pytest test suite

---

## V0.2 — Better Sensors & Errors

- [ ] `Servo` component (partially done in V0.1)
- [ ] Multiple sensors of the same type (e.g., two Ultrasonics)
- [ ] `elif` chain support
- [ ] Better error messages with line numbers and code snippets
- [ ] `LineSensor` component (digital IR line sensor)
- [ ] `botforge validate` command (lint without generating)

---

## V0.3 — ESP32 Target

- [ ] ESP32 target (`--target esp32`)
- [ ] PWM channels via `ledcWrite()`
- [ ] Optional Wi-Fi boilerplate
- [ ] `Servo` via ESP32 LEDC instead of `Servo.h`
- [ ] PlatformIO `platformio.ini` generation

---

## V0.4 — Stepper Motors

- [ ] `StepperMotor` component using `AccelStepper.h`
- [ ] `motor.move(steps=100, speed=200)` DSL
- [ ] I2C sensor support (`Wire.h`)
- [ ] IMU component (`MPU6050`)

---

## V0.5 — ROS 2 Target

- [ ] ROS 2 target (`--target ros2`)
- [ ] Generate a full C++ ROS 2 node using `rclcpp`
- [ ] `bot.publish(topic, msg)` DSL
- [ ] `bot.subscribe(topic)` DSL
- [ ] `CMakeLists.txt` + `package.xml` generation
- [ ] `geometry_msgs::Twist` for velocity commands
- [ ] `sensor_msgs::Range` for ultrasonic

---

## V0.6 — OpenCV / Vision

- [ ] Computer vision target for companion computers (Raspberry Pi, Jetson)
- [ ] `Camera` component
- [ ] `bot.detect_color()`, `bot.detect_edge()` DSL actions
- [ ] OpenCV C++ code generation

---

## V1.0 — Stable Release

- [ ] Stable DSL (no breaking changes)
- [ ] All V0.x targets supported
- [ ] Complete documentation site
- [ ] Real-world example library
- [ ] VS Code extension for DSL syntax highlighting
- [ ] Web playground (Monaco + WASM)
