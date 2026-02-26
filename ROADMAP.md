# AsciigenPy Roadmap

This document outlines the planned future development for AsciigenPy.

## Phase 1: Architecture & Maintainability
- **Decoupling & File Splitting:** Break down the monolithic `__main__.py` into logical modules (e.g., UI, processing engine, components) for easier development.
- **Cleaner Code:** Refactor code applying SOLID, DRY, and KISS principles to increase readability and maintainability.
- **Advanced Project Setup:** Use standard python packaging (e.g., `pyproject.toml`, proper virtual environment documentation, linting/formatting tools).
- **Repository Setup:** Add CI/CD (e.g. GitHub Actions) for automated testing, issue templates, and standardizing the repo.
- **Changelog:** Adopt and maintain a `CHANGELOG.md` file standard.

## Phase 2: Quality of Life & Features
- **State Management:** Remember the last opened folder even after the program closes, ensuring file opening consistency for users.
- **Asciigen Features & Research:** 
  - Add changing font support for the ASCII renderer.
  - Implement easy exporting options (e.g. Export as Image, HTML, or raw Text Document).

## Phase 3: Distribution
- **Compilation Tools:** Integrate PyInstaller and automated scripts to construct portable AppImages for Linux and executables for Windows.
