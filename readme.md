# ERPNext Code Analyzer (Terminal MVP)

A lightweight, terminal-based Python tool to analyze the **ERPNext codebase structure** using **AST (Abstract Syntax Tree)** parsing.

This project helps developers understand large Python codebases by extracting structural insights such as classes, functions, and function-call relationships — all without external dependencies.

---

## Features

- Detects **classes and their methods**
- Extracts **functions and their parameters**
- Builds **function call relationships**
- Identifies **most-called functions**
- Displays a clean **terminal summary**
- Automatically **exports analysis results to JSON**
- Fast, static analysis using Python AST
- Designed for learning ERPNext internals and large codebases
<img width="1366" height="768" alt="image" src="https://github.com/user-attachments/assets/72ddc62e-6324-48e4-863a-523253e557f2" />

<img width="559" height="455" alt="image" src="https://github.com/user-attachments/assets/310bf68c-33cc-4ef0-996f-aabbc8e546c2" />

<img width="531" height="647" alt="image" src="https://github.com/user-attachments/assets/15701d0a-f567-44fc-a258-401c50614533" />

<img width="530" height="604" alt="image" src="https://github.com/user-attachments/assets/48eb150d-9c4b-4b53-bdd4-17f993d1fc12" />

---

## Requirements

- Python **3.8+**
- No third-party libraries required

---

## Installation and Usage

### 1. Clone the Repository

```bash
git clone https://github.com/shiv4321/erpnext-code-analyzer.git
cd erpnext-code-analyzer

## Run the Analyzer

python analyzer.py

## Provide ERPNext Module Path

erpnext/accounts
erpnext/stock
erpnext/selling


**Sample Terminal Output**

═══════════════════════════════════════════════════════════════════
  ERPNext Code Analyzer - Terminal Edition
═══════════════════════════════════════════════════════════════════

Files analyzed:        45
Classes found:         12
Functions found:       328
Function calls:        891

Most called functions:
 - get_doc
 - validate
 - throw
