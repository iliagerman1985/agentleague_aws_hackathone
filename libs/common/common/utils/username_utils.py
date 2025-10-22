"""Email validation and normalization utilities.
Since our Cognito User Pool is configured with `username-attributes email`,
email addresses are used directly as usernames.
"""

import re


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False

    # More strict email validation regex that doesn't allow consecutive dots
    # Local part: alphanumeric, dots (not consecutive), underscores, percent, plus, hyphens
    # Domain part: alphanumeric, dots, hyphens, must end with 2+ letter TLD
    email_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9._+%-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$"

    # Additional check: no consecutive dots
    if ".." in email:
        return False

    return re.match(email_pattern, email) is not None


def normalize_email(email: str) -> str:
    """Normalize email address (lowercase, strip whitespace)."""
    if not email:
        return email

    return email.strip().lower()


def validate_and_normalize_email(email: str) -> str:
    """Validate and normalize email address.

    Returns:
        str: normalized email address

    Raises:
        ValueError: If email is invalid
    """
    if not email:
        raise ValueError("Email is required")

    # Normalize email
    normalized_email = normalize_email(email)

    # Validate email format
    if not is_valid_email(normalized_email):
        raise ValueError("Invalid email format")

    return normalized_email


# Example usage
if __name__ == "__main__":
    # Test cases
    test_emails = [
        "iliagerman@gmail.com",
        "user.name@example.org",
        "test+tag@domain.co.uk",
        "simple@test.com",
        "iliag@sela.co.il",
    ]

    print("Testing email validation and normalization:")
    for email in test_emails:
        try:
            normalized = validate_and_normalize_email(email)
            print(f"Original: {email}")
            print(f"Normalized: {normalized}")
            print(f"Valid: {is_valid_email(email)}")
            print("-" * 40)
        except ValueError as e:
            print(f"Error with {email}: {e}")
            print("-" * 40)
