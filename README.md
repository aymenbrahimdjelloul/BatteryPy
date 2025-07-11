<!-- GitHub README.md -->

<a href="https://github.com/aymenbrahimdjelloul/BatteryPy/releases/latest">
    <img src="https://img.shields.io/github/v/release/aymenbrahimdjelloul/BatteryPy?color=green&label=Download&style=for-the-badge" alt="Download Latest Release">
</a>

# **BatteryPy**
BatteryPy is a lightweight, pure-Python library designed for Windows, allowing you to easily and quickly retrieve detailed battery information and status. Whether you're monitoring battery health, charge level, or power source, BatteryPy provides a fast and efficient way to access crucial battery data without relying on external dependencies.


<div align="center">
  <table>
    <tr>
      <td align="center">
        <img src="https://github.com/aymenbrahimdjelloul/BatteryPy/blob/main/images/screenshot_1.png" alt="Main Interface" width="350px"/>
        <br>
        <em>BatteryPy App</em>
      </td>
      <td align="center">
        <img src="https://github.com/aymenbrahimdjelloul/BatteryPy/blob/main/images/screenshot_2.png" alt="Scan in Progress" width="350px"/>
        <br>
        <em>BatteryPy About</em>
      </td>
    </tr>
  </table>
</div>

---

## **Features**

- [X]  Cross-platform (Windows, Linux; macOS support coming soon)

- [x] Easy & Fast !

- [x] Provide accurate inforamtions

- [x] Pure python (No need for external dependencies)

---

## **Get Started**

1. Clone the repo :
   ~~~bash
   git clone https://github.com/aymenbrahimdjelloul/BatteryPy.git
   ~~~
2. Navigate to the project folder :
   ~~~bash
   cd BatteryPy
   ~~~
3. Run it :
   ~~~bash
   python3 run.py
   ~~~
#### **Or Install via pip :**

~~~bash
pip install batterypy
~~~

   
--- 

## Usage

~~~python
# First import the Battery class object from the BatteryPy module
from batterypy import Battery

# Create battery class object
battery = Battery()

# Print out the battery percentage
print(battery.battery_percentage)

~~~

---

## **Thanks**

We would like to extend our sincere gratitude to the following:

- **The Python community** for creating such an incredible and versatile language.
- **The open-source contributors** whose tools and libraries inspired this project.
- **All the users and testers** who provided invaluable feedback and suggestions to make **BatteryPy** better.
- **GitHub** for providing a platform for collaboration and sharing this project with the world.

Your support and contributions help make open-source development a thriving and rewarding experience!

---

## **License**
### This project is published under MIT License

~~~
MIT License

Copyright (c) 2023-2025 Aymen Brahim Djelloul

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

~~~
