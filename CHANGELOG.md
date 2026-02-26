# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Created `ROADMAP.md` file to track future iterations and milestones.
- Persistent memory of the last opened image directory using `PyQt6.QtCore.QSettings`.
- Project packaged according to modern Python standards via `pyproject.toml`.
- Extracted visualization logic into a dedicated `AsciigenUI` class inside `layout.py` to adhere to the Single Responsibility principle.

### Fixed
- Fixed an issue where the image modifications UI caused severe performance lag. Added a 100ms debounce rendering timer.
- Replaced the platform-specific terminal output clipboard error in the text box with a `QMessageBox` pop-up window, keeping the UI clean.

### Changed
- Decoupled `__main__.py` monolith. The application is now structured as an `asciigenpy` package containing modular `ui/inspector.py` and `ui/main_window.py` files.
- Re-routed `run.sh` and `run.bat` to launch the application using `python -m asciigenpy`.

## [1.0.0] - 2026-02-25
### Added
- Initial UI release.
- Image importing, processing, and real-time ASCII generation capabilities.
- Character set ramp selection mapping.
- Adjustable image width and height matching character aspect ratios.
