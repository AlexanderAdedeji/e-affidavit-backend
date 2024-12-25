from typing import Final

# Authentication & Authorization Errors
INCORRECT_LOGIN_INPUT: Final[str] = "Incorrect email or password"
UNVERIFIED_USER_ERROR: Final[str] = "This account is not verified"
INACTIVE_USER_ERROR: Final[str] = "This account is not active"
WRONG_TOKEN_PREFIX: Final[str] = "Unsupported authorization type"
UNAUTHORIZED_ACTION: Final[str] = "You cannot perform this action"
AUTHENTICATION_REQUIRED: Final[str] = "Authentication required"
MALFORMED_PAYLOAD: Final[str] = "Could not validate credentials"

# General Errors
ALREADY_EXISTS: Final[str] = "{} already exists"
NOT_FOUND: Final[str] = "Not found"
SERVER_ERROR: Final[str] = "An error occurred"
DOES_NOT_EXIST: Final[str] = "{} does not exist"
DEVICE_ID_REQUIRED_ERROR:Final[str] ="Device ID is required for commissioners."
