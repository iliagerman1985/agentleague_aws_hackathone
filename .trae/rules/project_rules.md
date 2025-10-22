## **LLM Code Assistant Instructions**

### **1. Core Directives**

* **Architecture:** Do not blindly agree with my ideas. If you detect a flaw, risk, inefficiency, or a better alternative, challenge my approach respectfully but directly. Prioritize correctness and clarity over politeness or affirmation.

* **Task Adherence:** Strictly adhere to the given task. If you identify necessary adjustments, fixes, or improvements outside the scope of the current task, you must explicitly ask for permission before implementing them.

* **Problem Simplification:** Do not simplify or remove features to solve complex problems. Workarounds are not acceptable unless you receive explicit permission.

* **Root Cause Analysis - Critical Rule:** Never apply patches, hacks, or bandaid solutions to problems. Always understand the problem thoroughly and solve the root cause, not the symptom. Quick fixes that hide issues with workarounds like `overflow-hidden`, temporary CSS patches, or conditional logic to bypass problems are strictly prohibited. Take the time to analyze the underlying architectural or logical issue and implement a proper solution that addresses the fundamental problem. **CRITICAL: You are NOT allowed to make any assumptions about anything. You MUST investigate each problem until you actually see the root cause through code inspection, testing, or debugging. No guessing, no assumptions - only verified facts.**

* **Clean Code:** Write clean, modular, and maintainable code. Functions should be short, clear, and single-purpose. Avoid using `any` or `Any` types; create specific classes, interfaces, or types.
* **Typed Classes:** A telltale sign that you need to use a typed class is if you start accessing hardcoded keys of a dict. That means you need to use a typed pydantic class instead, subclassing from JsonModel. Don't use dicts to pass around parameters, unless it is a generic param and you don't need to know its structure.

* **Type Safety - Critical Rule:** You are NOT allowed to use `any` type for cases where we have types declared already. Always use proper Python and TypeScript interfaces and types to ensure type safety and prevent casing mismatches between frontend and backend data.

* **Type Safety - Complex Objects Rule:** Using untyped "Any" or untyped dicts is strictly prohibited. For complex objects, you MUST create Pydantic classes that inherit from JsonModel to represent the data structure. Never use raw dictionaries or Any types for complex data structures.

* **Code Modularity:** Decompose code into small, reusable components. No single file should exceed 800 lines.

* **Class Instantiation Rules:**
  * **Data Classes Only:** Only data classes (Pydantic models, dataclasses, etc.) are allowed to be instantiated directly within methods.
  * **Service Injection:** All "service" type classes must be injected via the constructor (dependency injection) and never instantiated directly in methods.
  * **Purpose:** This enforces proper dependency injection, improves testability, and maintains clean architecture patterns.

* **Backwards Compatibility & Code Cleanup:** Leaving stale code "for backwards compatibility" is strictly disallowed. When deprecating or replacing functionality:
  * **Mandatory Migration:** Make every effort to update all usages of deprecated code to use the new implementation
  * **Complete Removal:** Delete the old code once all usages have been migrated
  * **No Dead Code:** Do not leave unused functions, classes, or modules "just in case" - they create maintenance burden and confusion
  * **Active Usage Verification:** Before claiming backwards compatibility necessity, verify the code is actually being used in production
  * **Migration Over Maintenance:** Prefer updating callers over maintaining multiple code paths

* **Code Discovery & Research:**

  * **Finding Examples:** Look for usages of a class or function by searching and viewing cross-references. This is crucial for understanding how to use an API correctly. Search the codebase for existing patterns and implementations before writing new code.

  * **Library Usage:** Before using a new library, ALWAYS search for existing examples of its use within the code to understand common patterns and required dependencies. Read at least one example file to understand the proper usage patterns and integration approaches. Check how existing code imports and initializes libraries to maintain consistency.

* **Agent Workflow for Edit/Fix Tasks:**

  * **Understand Phase:** Thoroughly analyze the request and requirements. Search code to find all relevant files, including models, services, routers, and tests. Read the code to understand the current implementation and architecture.

  * **Edit Code Phase:** Apply required changes to Python files (`.py` files) and TypeScript/React files (`.ts`, `.tsx` files) following project conventions. Maintain consistency with existing code patterns and architecture.

  * **Update Tests Phase:** Modify existing tests or add new ones to cover the changes. Unit tests are essential for all new functionality. Add integration tests for complex workflows.

  * **Clean & Fix Phase:** Run `ruff format` to ensure consistent code formatting. Run `ruff check` to catch style and potential issues. Run `pyright` for Python type checking. Run `npm run tsc` or `just tsc` for TypeScript checking.

  * **Simplification Review Phase:** After completing modifications, perform a "zoom out" review of the code to identify simplification opportunities. Look for:
    * **Condition Consolidation:** Multiple conditional statements that can be merged or simplified
    * **Redundant Logic:** Code paths that became unnecessary after the modifications
    * **Abstraction Opportunities:** Repeated patterns that can be extracted into reusable functions
    * **Dead Code Elimination:** Unused variables, functions, or imports that are no longer needed
    * **Logic Streamlining:** Complex nested conditions that can be flattened or simplified
    * **Pattern Recognition:** Similar code blocks that can be unified or refactored

* **Agent Debugging Protocol (Build/Test Failures):**

  * **Goal:** Avoid getting stuck in build/test failure loops.

  * **Debugging Steps:** (1) Analyze Error - carefully read compiler/test errors to identify root cause. (2) Search Code for Clues - if error is about library usage, search for other examples in codebase. (3) Re-read Definitions - double-check function signatures and class definitions. (4) Incremental Changes - comment out sections to isolate problems. (5) Test-Specific Debugging - add logging statements to trace execution flow. (6) Ask for Help - if stuck, explain what you've tried and present exact error messages.

  * **Verification Requirements:** Verify changes before declaring complete. Ensure code passes build/lint and tests. For Python: ensure `ruff check`, `ruff format`, and `pyright` all pass. For TypeScript: ensure `npm run tsc` and ESLint checks pass.

* **Git Workflow & Code Quality:**

  * **Change Review:** Run `git diff` to review local changes. Read the diff and original files to understand impact. Ensure all changes align with intended functionality.

  * **Testing Requirements:** Write comprehensive unit tests in corresponding test files. Build and test affected components until everything passes. Do not modify non-test code to make tests pass, and do not modify or remove existing test functions unless explicitly required.

  * **Quality Gates:** Always run `pyright` and `ruff check` after any Python code change. Always run `npm run tsc` and linting after any TypeScript code change. Ensure all tests pass before considering task complete.

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

* **Game Architecture - Critical Rule:**

  * **GameManager Must Remain Generic:** The `GameManager` class MUST be completely generic and game-agnostic. It cannot contain any game-specific logic, fields, methods, or hacky solutions like `getattr()` calls.

  * **Game-Specific Logic Placement:** All game-specific functionality must be handled within individual game environments (e.g., `texas_holdem_env.py`).

  * **Architectural Separation:** This separation is essential for maintaining a clean, extensible architecture that can support multiple game types without coupling the core game management system to specific game implementations.

  * **Violation Prevention:** Any attempt to add game-specific code to `GameManager` violates the architectural principles and must be rejected in favor of proper game environment implementations.

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

  * All CRUD methods must return a Pydantic object.

  * **Migration Management:** You are NOT allowed to create migrations manually. The ONLY way to create a migration is by running "just generate_migration". Never create migration files by hand or use alembic commands directly.

* **Pydantic Models:**

  * **Use JsonModel:** Use Pydantic classes, specifically `JsonModel` for all data models that need JSON serialization.

  * **Type Safety:** Leverage Pydantic's type validation and serialization capabilities.

  * Models that map to database tables must include `to()` and `from_()` methods for converting between the Pydantic object and the database model.

* **Type Hinting & Enums:**

  * Use `StrEnum` for string-based enumerations.

  * Prefer Enums over raw strings where applicable (e.g., for status fields, roles).

  * Use modern type hints: `| None` instead of `Optional[...]`, and `list` instead of `List`, `dict` instead of `Dict`, etc. (for Python 3.10+).

* **File Paths:**

  * Use the `pathlib.Path` object for path manipulations. Replace `os.path.splitext()` with `Path.suffix`, `Path.stem`, and `Path.parent`.

* **Error Handling & Logging:**

  * **Use AppError:** Raise errors using `AppError` for all application-level exceptions.

  * **Middleware Integration:** There is no need to catch errors and translate them to HTTP responses manually - this is handled by middleware. Ensure the error declares all required `status_code` and `details` fields.

  * **Async APIs:** Use async APIs wherever possible for better performance and scalability.

  * **Logging Service:** Use the shared logging service from `common.core.logging_service.get_logger(__name__)`

  * **Exception Handling:** Use `logger.exception()` within `except` blocks to capture stack traces. Avoid `logger.error()`.

  * **Structured Logging:** Use the logging service's structured logging capabilities with key-value pairs

  * **Log Consolidation:** Consolidate multiple consecutive log lines into a single, comprehensive log entry where possible.

* **Code Style:**

  * Use double quotes (`"`) for strings, not single quotes (`'`).

  * Use explicit type conversions (e.g., `str(value)` instead of relying on implicit coercion).

  * Start multi-line docstring summaries on the first line.

  * Place all `import` statements at the top of the file, not within functions or classes.
  * **Critical Import Rule:** Do not import inside methods, always add imports at the top of the file.

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

* **Design System - Rounded Corners:**

  * **Always use rounded corners** - never use `rounded-none` unless specifically required

  * **Standard values**: `rounded-lg` (16px) for cards/panels, `rounded-xl` (20px) for large containers, `rounded-md` (12px) for buttons/inputs

  * **Consistency rule**: Use the same radius size within related components

  * **Modern appearance**: Prefer larger radius values for a professional, modern look

* **Design System - Dialog Button Spacing:**

  * **Use standard DialogFooter** - never override with custom spacing classes like `space-x-2` or `gap-2`

  * **Mobile spacing**: DialogFooter automatically handles proper spacing on mobile with `gap-2`

  * **Consistent behavior**: All dialogs should have the same button spacing behavior

* **Design System - Color Scheme:**

  * **Bright theme**: App uses a bright, clean color scheme inspired by modern platforms

  * **Brand colors**: Use `brand-blue` for primary actions, `brand-yellow` for accents, `brand-mint` for success

  * **Consistent usage**: Stick to the defined color palette for consistency across the app

* **Code Style:**

  * Use `camelCase` for variable and function names.

* **Tooling Setups:**

  * **Tailwind CSS with Vite:** Follow the provided step-by-step guide for installation and configuration via the `@tailwindcss/vite` plugin.

  * **shadcn/ui Setup:** Follow the provided step-by-step guide for project creation, TypeScript configuration (`tsconfig.json`), Vite configuration (`vite.config.ts`), and `shadcn` initialization.

* The client runs on port 5888 and the server on port 9998. Assume they are both already running. Do not attempt to run them again. Do not kill the existing process if you see a port conflict.
* Previews must always be run on port 5888.

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

### **8. Workflow Commands**

* **Server Management:**

  * **Development Server Cleanup:** You must close any servers you open during development or debugging that were not open previously. If a server was already running before you started working, you must not bring it down. This ensures proper cleanup while preserving existing development environments.

  * **Background Process Awareness:** Always check for existing background processes before starting new servers to avoid conflicts and unnecessary resource usage.

* **Database Migrations:**

  * To generate a new development migration file: `just generate_migration`

  * To apply development migrations to the database: `just migrate`

* **Development Commands:**

  * **Start Backend:** `just run-backend` or `uv run --package backend uvicorn app.main:app --reload`

  * **Start Frontend:** `just run-client` or `cd client && npm start`

  * **Run Tests:** `just test` or `uv run pytest`

  * **Lint Code:** `just lint` or `uv run ruff check`

  * **Format Code:** `just format` or `uv run ruff format`

Always make sure ruff lint and pyright checks pass after your changes.
Do not disable lint rules, fix the code instead.
Only write imports at the top level of the file
Do not use # type: ignore, fix the type issue instead. And double check that its not because you wrote something incorrect.
Always make sure relevant tests pass after your changes.
Make sure you frontend code passes eslint and tsc by running "npm run tsc" or "just tsc" after writing it.
Use the existing design language and conventions that exist in the project already when adding or changes the UI.
You must test that your changes work before stopping and saying they work.
After updating the UI you must look at the preview to see that it corresponds to the task you were supposed to do.
Do not import inside methods, always add imports at the top of the file

When writing tests:
It should be player 1's turn to act by default
Only specify the number of players if it is significant to the test scenario, otherwise don't specify it.
Never write tests with conditional logic in them. Tests must always be explicit and know what the expected behavior is.
Write tests with STRONG assertions that don't leave room for errors. Prefer asserting full objects completely, not just parts of them.
When fixing a broken test you must first fully understand why its failing and whether the test is incorrect or it actually found a regression in the production code. Fully inspect the production code and fully understand what the test is trying to do, and then decide whether the test is incorrect or the production code is broken. If the test is incorrect, fix the test. If the production code is broken, fix the production code.
