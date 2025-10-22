/**
 * Test data constants for Playwright tests
 */

export const TEST_USERS = {
  ADMIN: {
    email: 'admin@admin.com',
    password: 'Cowabunga2@',
    role: 'ADMIN',
    fullName: 'Test Admin User'
  },
  USER: {
    email: 'user@test.com',
    password: 'TestPassword123!',
    role: 'USER',
    fullName: 'Test Regular User'
  }
} as const;

// Real Cognito user for integration testing
export const REAL_COGNITO_USER = {
  email: 'iliagerman@gmail.com',
  password: 'Cowabunga1!',
  role: 'USER',
  fullName: 'Ilia German'
} as const;

export const INVALID_CREDENTIALS = {
  email: 'invalid@example.com',
  password: 'wrongpassword'
} as const;

// Function to generate unique email for each test run
export function generateUniqueEmail(prefix: string): string {
  return `${prefix}.${Date.now()}.${Math.random().toString(36).substring(7)}@test.com`;
}

export const TEST_REGISTRATION_DATA = {
  VALID_USER: {
    firstName: 'John',
    lastName: 'Doe',
    get email() { return generateUniqueEmail('john.doe'); },
    password: 'TestPassword123!',
    confirmPassword: 'TestPassword123!'
  },
  EXISTING_USER: {
    firstName: 'Admin',
    lastName: 'User',
    email: 'admin@admin.com', // This user already exists
    password: 'TestPassword123!',
    confirmPassword: 'TestPassword123!'
  },
  INVALID_EMAIL: {
    firstName: 'Jane',
    lastName: 'Smith',
    email: 'invalid-email',
    password: 'TestPassword123!',
    confirmPassword: 'TestPassword123!'
  },
  WEAK_PASSWORD: {
    firstName: 'Bob',
    lastName: 'Wilson',
    get email() { return generateUniqueEmail('bob.wilson'); },
    password: '123',
    confirmPassword: '123'
  },
  MISMATCHED_PASSWORDS: {
    firstName: 'Alice',
    lastName: 'Johnson',
    get email() { return generateUniqueEmail('alice.johnson'); },
    password: 'TestPassword123!',
    confirmPassword: 'DifferentPassword123!'
  }
} as const;

export const TEST_URLS = {
  LOGIN: '/login',
  REGISTER: '/register',
  CONFIRM_SIGNUP: '/confirm-signup',
  DASHBOARD: '/games-management',
  HOME: '/'
} as const;

export const SELECTORS = {
  LOGIN: {
    EMAIL_INPUT: 'input#email',
    PASSWORD_INPUT: 'input#password',
    SUBMIT_BUTTON: 'button[type="submit"]',
    REMEMBER_ME: '#remember-me',
    REMEMBER_ME_LABEL: 'label[for="remember-me"]',
    ERROR_MESSAGE: '.text-destructive, [role="alert"], .error, .text-red-500, div:has-text("error"), div:has-text("Error")'
  },
  REGISTER: {
    FIRST_NAME_INPUT: 'input[name="firstName"], input#firstName, input[data-testid="first-name"]',
    LAST_NAME_INPUT: 'input[name="lastName"], input#lastName, input[data-testid="last-name"]',
    EMAIL_INPUT: 'input[name="email"], input#email, input[type="email"]',
    PASSWORD_INPUT: 'input[name="password"], input#password, input[type="password"]',
    CONFIRM_PASSWORD_INPUT: 'input[name="confirmPassword"], input#confirmPassword, input[name="password_confirmation"]',
    SUBMIT_BUTTON: 'button[type="submit"], button:has-text("Sign Up"), button:has-text("Register")',
    ERROR_MESSAGE: '.text-destructive, [role="alert"], .error, .text-red-500, div:has-text("error"), div:has-text("Error")',
    SUCCESS_MESSAGE: '.text-green-500, .text-success, .success, div:has-text("success"), div:has-text("Success")'
  },
  CONFIRM_SIGNUP: {
    CONFIRMATION_CODE_INPUT: 'input[name="confirmationCode"], input#confirmationCode, input[data-testid="confirmation-code"]',
    SUBMIT_BUTTON: 'button[type="submit"], button:has-text("Confirm"), button:has-text("Verify")',
    ERROR_MESSAGE: '.text-destructive, [role="alert"], .error, .text-red-500, div:has-text("error"), div:has-text("Error")',
    SUCCESS_MESSAGE: '.text-green-500, .text-success, .success, div:has-text("success"), div:has-text("Success")'
  },
  DASHBOARD: {
    TITLE: 'h1:has-text("Play")',
    USER_MENU: '[data-testid="user-menu"], .user-menu, button:has-text("menu"), [aria-label*="menu"]'
  }
} as const;
