# Installation Guide

## Prerequisites

- **Python 3.8+** must be installed on your system.
- An **EGM-4 CO2 Gas Analyzer** connected via Serial/USB.

## Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/mmorgans/open-egm4.git
   cd open-egm4
   ```

2. **Create a Virtual Environment (Recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install textual pyserial
   ```
   *(Note: The `requirements.txt` file in the root directory contains the exact versions)*

## Running the Application

To start the TUI:

```bash
python main.py
```

## Connection Setup

1. Connect the EGM-4 to your computer.
2. Launch the application.
3. The **Connection Screen** will appear.
   - It will attempt to **Auto-Connect** to valid EGM-4 ports.
   - If auto-connect fails, you can select the port manually from the list.
4. Once connected, you will be taken to the **Monitor Screen**.
