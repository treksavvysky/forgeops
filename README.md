# Forge Ops - Issue Tracking System

Forge Ops is a command-line application designed to help developers manage software development issues and track associated repositories. It provides a simple interface for creating, viewing, and listing issues, as well as managing a list of repositories.

## Features

*   **Issue Management:**
    *   Create new issues with a title, description, and associated repository.
    *   List all existing issues.
    *   Filter issues by repository.
    *   View detailed information for a specific issue.
*   **Repository Management:**
    *   Maintain a list of known repositories.
    *   Add new repositories to the system.
*   **Command-Line Interface:** Easy-to-use CLI for all functionalities.

## Setup and Installation

Follow these steps to set up the Forge Ops Issue Tracker on your local machine:

1.  **Clone the Repository:**
    Open your terminal and clone the repository using Git:
    ```bash
    git clone <repository-url> # Replace <repository-url> with the actual URL
    cd forge-ops-issue-tracker # Or the actual directory name after cloning
    ```

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment to manage project dependencies. Create and activate one using Python's built-in `venv` module:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
    ```

3.  **Install Dependencies with UV:**
    This project uses `uv` for package management. Install the dependencies using:
    ```bash
    uv pip sync
    ```
    *This command will install dependencies based on `uv.lock` if present, or `pyproject.toml`.*

## Usage

To use the Forge Ops Issue Tracker, you can run the `main.py` script using `uv` (if you followed the setup instructions) or directly with Python.

### General Syntax

You can run commands using `uv` or Python directly:

**Using UV:**
```bash
uv run python main.py <command> [options]
```

**Using Python directly:**
```bash
python main.py <command> [options]
```
*(Ensure your virtual environment is activated if running Python directly).*

### Available Commands

**Issue Management:**

*   **Create a new issue:**
    ```bash
    # Using UV
    uv run python main.py create-issue
    # Or using Python directly
    python main.py create-issue
    ```
    *This command will guide you through an interactive process to create a new issue.*

*   **List all issues:**
    ```bash
    # Using UV
    uv run python main.py list-issues
    # Or using Python directly
    python main.py list-issues
    ```

*   **List issues for a specific repository:**
    ```bash
    # Using UV
    uv run python main.py list-issues --repo <repository-name>
    # Or using Python directly
    python main.py list-issues --repo <repository-name>
    ```
    *Example:*
    ```bash
    # Using UV
    uv run python main.py list-issues --repo forge-ops
    # Or using Python directly
    python main.py list-issues --repo forge-ops
    ```

*   **View detailed issue information:**
    ```bash
    # Using UV
    uv run python main.py view-issue <ISSUE-ID>
    # Or using Python directly
    python main.py view-issue <ISSUE-ID>
    ```
    *Example:*
    ```bash
    # Using UV
    uv run python main.py view-issue ISSUE-001
    # Or using Python directly
    python main.py view-issue ISSUE-001
    ```

**Repository Management:**

*   **List all registered repositories:**
    ```bash
    # Using UV
    uv run python main.py list-repos
    # Or using Python directly
    python main.py list-repos
    ```

*   **Add a new repository to the registry:**
    ```bash
    # Using UV
    uv run python main.py add-repo <repository-name>
    # Or using Python directly
    python main.py add-repo <repository-name>
    ```
    *Example:*
    ```bash
    # Using UV
    uv run python main.py add-repo my-new-project
    # Or using Python directly
    python main.py add-repo my-new-project
    ```

**Help:**

*   **Show help information:**
    ```bash
    # Using UV
    uv run python main.py help
    # Or using Python directly
    python main.py help
    ```
    *(Also available via `python main.py --help` or `python main.py -h`)*

## Project Structure

The project is organized as follows:

*   `main.py`: The main entry point for the command-line interface. It parses arguments and calls the appropriate command handlers.
*   `commands/`: Contains modules for each CLI command (e.g., `create_issue.py`, `list_issues.py`).
*   `core/`: Houses the core logic of the application:
    *   `issue_tracker.py`: Manages issue creation, validation, and interaction logic.
    *   `repository_manager.py`: Handles operations related to repositories, including loading and saving from `repos.json`.
    *   `file_manager.py`: Manages the storage and retrieval of issue data from individual files.
*   `utils/`: Includes utility modules, such as input validators (`validators.py`).
*   `issues/`: This directory stores the individual issue files, typically in JSON format. Each file represents a single issue.
*   `repos.json`: A JSON file that acts as a registry for known repository names.
*   `.gitignore`: Specifies intentionally untracked files that Git should ignore.
*   `pyproject.toml`: Project metadata and build system configuration (PEP 518).
*   `uv.lock`: Lock file for the `uv` Python package installer and resolver.
*   `README.md`: This file, providing an overview and guide to the project.

## Contributing

Contributions are welcome! If you have suggestions for improvements, new features, or bug fixes, please feel free to:

1.  Open an issue to discuss the change.
2.  Fork the repository and create a new branch for your work.
3.  Make your changes and commit them with clear messages.
4.  Submit a pull request for review.

## License

The license for this project is yet to be determined.
