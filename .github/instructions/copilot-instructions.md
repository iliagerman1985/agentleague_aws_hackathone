## **LLM Code Assistant Instructions**

### **1. Core Directives**

* **Architecture:** Do not blindly agree with my ideas. If you detect a flaw, risk, inefficiency, or a better alternative, challenge my approach respectfully but directly. Prioritize correctness and clarity over politeness or affirmation.


* **Task Adherence:** Strictly adhere to the given task. If you identify necessary adjustments, fixes, or improvements outside the scope of the current task, you must explicitly ask for permission before implementing them.
* **Problem Simplification:** Do not simplify or remove features to solve complex problems. Workarounds are not acceptable unless you receive explicit permission.
* **Clean Code:** Write clean, modular, and maintainable code. Functions should be short, clear, and single-purpose. Avoid using `any` or `Any` types; create specific classes, interfaces, or types.
* **Code Modularity:** Decompose code into small, reusable components. No single file should exceed 800 lines.

### **2. Tech Stack & Project Structure**

* **Backend:** FastAPI, PostgreSQL, Alembic
* **Frontend:** React, Vite, magic ui, Tailwind CSS
* **LLM Integration:** AWS Bedrock
* **Package Management:** uv (Python package manager and workspace management)
* **Project Structure:** Monorepo with shared libraries:
  * `backend/` - FastAPI application
  * `client/` - React frontend
  * `libs/common/` - Shared utilities, configuration, logging, LLM services
  * `libs/shared_db/` - Database models, migrations, and database utilities

### **3. Backend Development (`Gotchas & Style Guide`)**

* **Shared Libraries Usage:**
    * **Common Library (`libs/common/`):** Use shared utilities for configuration, logging, LLM services, JWT validation, and exceptions.
    * **Shared DB Library (`libs/shared_db/`):** Use shared database models, migrations, and database utilities.
    * **Import Pattern:** Always import from shared libraries: `from common.core.config_service import ConfigService`, `from shared_db.models.user import User`
* **Configuration Management:**
    * **Centralized Config:** All configuration files are located in `libs/common/` (`.env.*`, `secrets.yaml`)
    * **Config Service:** Use `ConfigService` from `common.core.config_service` for all configuration access
    * **Environment Variables:** Load from shared `.env` files in `libs/common/`
    * **Secrets:** Store sensitive data in `libs/common/secrets.yaml` (never commit this file)
* **Dependency Injection & Initialization:**
    * Use FastAPI's built-in dependency injection system to manage all dependencies, such as database sessions, services, and DAOs.
    * A central `dependencies.py` file must be used to create and configure these dependencies. This file will contain provider functions that initialize and `yield` instances.
    * **Database Session:** The `dependencies.py` file must include a `get_db` dependency that provides a database session for a single request and ensures it is properly closed after the request is complete.
    * **Services and DAOs:** Create specific dependency provider functions for each service and DAO (e.g., `get_user_service`). These functions will typically depend on other dependencies, like `get_db`.
    * **Usage:** Inject dependencies directly into API endpoint function signatures using `Depends`. Do not instantiate DAOs, services, or sessions manually within endpoint logic.
* **Database Access:**
    * Use the `BaseDAO` for all database operations. Do not use `CRUDBase`.
    * All CRUD methods must return a Pydantic object.
* **Pydantic Models:**
    * Models that map to database tables must include `to()` and `from_()` methods for converting between the Pydantic object and the database model.
* **Type Hinting & Enums:**
    * Use `StrEnum` for string-based enumerations.
    * Prefer Enums over raw strings where applicable (e.g., for status fields, roles).
    * Use modern type hints: `| None` instead of `Optional[...]`, and `list` instead of `List`, `dict` instead of `Dict`, etc. (for Python 3.10+).
* **File Paths:**
    * Use the `pathlib.Path` object for path manipulations. Replace `os.path.splitext()` with `Path.suffix`, `Path.stem`, and `Path.parent`.
* **Error Handling & Logging:**
    * **Logging Service:** Use the shared logging service from `common.core.logging_service.get_logger(__name__)`
    * **Exception Handling:** Use `logger.exception()` within `except` blocks to capture stack traces. Avoid `logger.error()`.
    * **Structured Logging:** Use the logging service's structured logging capabilities with key-value pairs
    * **Log Consolidation:** Consolidate multiple consecutive log lines into a single, comprehensive log entry where possible.
* **Code Style:**
    * Use double quotes (`"`) for strings, not single quotes (`'`).
    * Use explicit type conversions (e.g., `str(value)` instead of relying on implicit coercion).
    * Start multi-line docstring summaries on the first line.
    * Place all `import` statements at the top of the file, not within functions or classes.
    * Use `elif` to avoid nested `if` statements inside an `else` block.
    * Use `snake_case` for variable and function names.

### **4. Frontend Development (`Gotchas & Style Guide`)**

* **Responsive UI:** All UI components and layouts must be fully responsive, ensuring a seamless experience on both mobile and desktop screen sizes. Use Tailwind CSS's responsive design features (e.g., `md:`, `lg:`) to achieve this.
* **State & Error Handling (React Context):**
    * Centralize error handling for asynchronous operations within the React Context itself.
    * The context must expose an `error` state.
    * Async functions within the context must `catch` their own errors and update the `error` state. Do not re-throw errors from context functions.
    * Consuming components must read the `error` state to display error messages and should not contain their own `try/catch` blocks for context-provided functions.
* **Module Loading:**
    * Use dynamic `import()` for code-splitting or conditional module loading. `require()` is not available in the Vite browser environment.
* **UI Components:**
    * Use `magic ui` components whenever applicable, you have access to their MCP.
    * Before adding a new component with (This is just an example)`npx shadcn@latest add "https://magicui.design/r/globe.json"`, verify it is not already installed in the project.
* **Code Style:**
    * Use `camelCase` for variable and function names.
* **Tooling Setups:**
    * **Tailwind CSS with Vite:** Follow the provided step-by-step guide for installation and configuration via the `@tailwindcss/vite` plugin.
    * **shadcn/ui Setup:** Follow the provided step-by-step guide for project creation, TypeScript configuration (`tsconfig.json`), Vite configuration (`vite.config.ts`), and `shadcn` initialization.

### **5. API Design & Communication**

* **API Endpoints:** All API endpoints must follow RESTful principles. Use nouns for resource names (e.g., `/users`, `/documents`) and HTTP verbs for actions (`GET`, `POST`, `PUT`, `DELETE`).
* **API Responses:** Standardize API success and error responses.
    * **Success Example:** `{ "status": "success", "data": { ... } }`
    * **Error Example:** `{ "status": "error", "message": "A descriptive error message" }`
* **Environment Variables:** All sensitive information (API keys, database URLs, secrets) must be loaded from environment variables using Pydantic's `BaseSettings`, never hardcoded.

### **6. Testing**

* **General Mandate:** All new features must be accompanied by tests. When modifying existing code, update existing tests or add them if they are missing.
* **Backend Testing:**
    * **Unit Tests:** Test individual functions and classes in isolation.
    * **Integration Tests:** Test the interaction between different parts of the application, including database operations.
    * **Implementation:** Use real classes and functionalities from shared libraries. Create mock data tailored for each test case.
    * **Test Database:** Use shared database models from `libs/shared_db/` for consistent testing
    * **Test Commands:** Use `uv run pytest` or `just test` to run tests
* **Client (Frontend) Testing:**
    * **Unit Tests (Jest):** Write Jest tests for business logic, hooks, and utility functions.
    * **E2E / UI Tests (Playwright):**
        * Write tests to verify the UI and user interactions for both **desktop** and **mobile** viewports using **Chrome**.
        * Place tests in the `/tests` folder under the client directory.
        * **Test Suites:**
            * **Regression Suite:** Covers only the most critical, essential features to ensure core functionality is stable.
            * **Full Suite:** Includes regression tests plus detailed tests for edge cases and less critical interactions.
        * **Testability:** Add `data-testid` attributes to key interactive elements to create stable selectors for Playwright, making tests less brittle.

### **7. Package Management & Dependencies**

* **uv Workspace Management:**
    * **Install Dependencies:** Use `uv sync` to install all workspace dependencies
    * **Add Dependencies:** Use `uv add <package>` to add new dependencies to the current package
    * **Add Dev Dependencies:** Use `uv add --group dev <package>` for development dependencies
    * **Install Tools:** Use `uv tool install <tool>` for CLI tools like awscli-local
    * **Run Commands:** Use `uv run --package <package> <command>` to run commands in specific packages
* **Never Use pip Directly:**
    * Do not use `pip install` - always use uv commands
    * Do not manually edit `requirements.txt` files - use uv workspace management
    * Do not use `pip freeze` - uv manages dependencies through `pyproject.toml` and `uv.lock`

### **8. Workflow**

* **Database Migrations:**
    * To generate a new development migration file: `just generate_migration`
    * To apply development migrations to the database: `just migrate`
* **Development Commands:**
    * **Start Backend:** `just run-backend` or `uv run --package backend uvicorn app.main:app --reload`
    * **Start Frontend:** `just run-client` or `cd client && npm start`
    * **Run Tests:** `just test` or `uv run pytest`
    * **Lint Code:** `just lint` or `uv run ruff check`
    * **Format Code:** `just format` or `uv run ruff format`

***

### Clarifying Questions

To ensure the LLM assistant operates with perfect clarity, I recommend we define the following:

1.  **Shared Libraries Usage:**
    * **Import Patterns:** When should code import from `libs/common/` vs `libs/shared_db/` vs local modules? Are there any circular dependency concerns to be aware of?
2.  **Backend Testing Scope:**
    * **Unit vs. Integration:** Could you provide a clear example that distinguishes a "unit test" from an "integration test" in our monorepo context? For instance, is testing a `BaseDAO` method with shared database models an integration test, while testing a Pydantic model's `from_()` method is a unit test?
3.  **Frontend Testing Scope:**
    * **Regression vs. Full:** Can you define the boundary for the "Regression" suite? For example, for a login feature, would regression only be "successful login," while the "Full" suite would also test "invalid password," "user not found," and "empty fields"?
4.  **Configuration Management:**
    * **Environment-Specific Config:** How should environment-specific configurations be handled across the monorepo? Should each package have its own environment handling or rely entirely on the shared config service?
5.  **Permissions:**
    * What is the preferred communication channel for asking for permission to execute out-of-scope tasks? (e.g., a specific comment format in the code, a message in a chat, etc.)