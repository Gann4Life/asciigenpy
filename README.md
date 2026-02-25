# AsciigenPy

AsciigenPy is a Python program inspired by asciigen2. It generates ASCII art and offers a graphical interface for creating, viewing, and tuning your custom text-based generated art.

## Requirements

- Python 3.8+ (Make sure it's added to your PATH)

## How to use

Once the application is running, you can use the interactive User Interface to tweak the settings, load images to convert, and view the generated ASCII art in real-time. It supports customizing the character set, tweaking brightness, contrast, and scaling properties.

## Getting Started

First, clone the repository to your local machine:
```bash
git clone https://github.com/Gann4Life/asciigenpy.git
cd asciigenpy
```

You can run AsciigenPy in two ways: Manually using the terminal, or using the provided startup scripts `run.bat` (Windows) and `run.sh` (Linux/macOS).

### Using the startup scripts (Recommended)

The provided scripts automatically set up a local virtual environment (`.venv`), install dependencies, and run the program for you.

**Windows:**
Double-click `run.bat` or run it from the Command Prompt:
```cmd
run.bat
```

**Linux / macOS:**
Open a terminal, make the script executable, and run it:
```bash
chmod +x run.sh
./run.sh
```

### Manually

If you prefer to set it up yourself, you can install the dependencies and run it manually from the terminal.

1. Open a terminal and navigate to the project directory:
   ```bash
   cd asciigenpy
   ```
2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the program:
   ```bash
   python .
   ```
