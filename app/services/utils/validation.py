import re
from datetime import date, datetime
from typing import Any, Optional, Tuple, Union

# Regex patterns
RE_MOBILE_INDIAN = re.compile(r'^(?:\+91|0)?([6-9]\d{9})$')
RE_MOBILE_INTL = re.compile(r'^\+?[1-9]\d{6,14}$')
RE_EMAIL = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
RE_UPI_ID = re.compile(r'^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$')
RE_TRANSACTION_ID = re.compile(r'^[a-zA-Z0-9]{8,30}$')
RE_USERNAME = re.compile(r'^[a-zA-Z0-9_.-]{3,30}$')
RE_TIME_HHMM = re.compile(r'^(?:[01]\d|2[0-3]):[0-5]\d$')


def validate_name(name: Optional[str], min_len: int = 2, max_len: int = 80, field_name: str = "Name") -> Tuple[bool, Union[str, None]]:
    """Validate full name: non-empty, reasonable length, contains letters."""
    if not name:
        return False, f"{field_name} is required."
    cleaned = " ".join(name.strip().split())
    if len(cleaned) < min_len:
        return False, f"{field_name} must be at least {min_len} characters long."
    if len(cleaned) > max_len:
        return False, f"{field_name} cannot exceed {max_len} characters."
    if not any(c.isalpha() for c in cleaned):
        return False, f"{field_name} must contain letters."
    # Disallow script tags or HTML injection
    if '<' in cleaned or '>' in cleaned:
        return False, f"{field_name} contains invalid characters."
    return True, cleaned


def validate_mobile(mobile: Optional[str], required: bool = True, field_name: str = "Mobile Number") -> Tuple[bool, Union[str, None]]:
    """Validate phone number (accepts Indian 10-digit format or international format)."""
    if not mobile or not mobile.strip():
        if required:
            return False, f"{field_name} is required."
        return True, None

    cleaned = mobile.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Try Indian format first
    indian_match = RE_MOBILE_INDIAN.match(cleaned)
    if indian_match:
        return True, indian_match.group(1)  # Returns clean 10-digit number
    
    # Try International format
    if RE_MOBILE_INTL.match(cleaned):
        return True, cleaned

    return False, f"Please enter a valid 10-digit mobile number for {field_name} (e.g. 9876543210)."


def validate_email(email: Optional[str], required: bool = False, field_name: str = "Email Address") -> Tuple[bool, Union[str, None]]:
    """Validate email address format."""
    if not email or not email.strip():
        if required:
            return False, f"{field_name} is required."
        return True, None

    cleaned = email.strip().lower()
    if not RE_EMAIL.match(cleaned):
        return False, "Please enter a valid email address (e.g. user@example.com)."
    if len(cleaned) > 120:
        return False, f"{field_name} cannot exceed 120 characters."
    return True, cleaned


def validate_age(age_val: Any, min_age: int = 4, max_age: int = 100, field_name: str = "Age") -> Tuple[bool, Union[int, str]]:
    """Validate age within competitive bounds."""
    if age_val is None or (isinstance(age_val, str) and not age_val.strip()):
        return False, f"{field_name} is required."
    try:
        age_int = int(age_val)
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid number."

    if age_int < min_age or age_int > max_age:
        return False, f"{field_name} must be between {min_age} and {max_age}."
    return True, age_int


def validate_dob(dob_val: Any, min_age: int = 4, max_age: int = 100, field_name: str = "Date of Birth") -> Tuple[bool, Union[date, str]]:
    """Validate date of birth: must be in the past and result in valid age."""
    if not dob_val:
        return False, f"{field_name} is required."

    if isinstance(dob_val, str):
        try:
            parsed_date = datetime.strptime(dob_val.strip(), "%Y-%m-%d").date()
        except ValueError:
            return False, f"Invalid {field_name} format. Use YYYY-MM-DD."
    elif isinstance(dob_val, datetime):
        parsed_date = dob_val.date()
    elif isinstance(dob_val, date):
        parsed_date = dob_val
    else:
        return False, f"Invalid {field_name} format."

    today = date.today()
    if parsed_date >= today:
        return False, f"{field_name} cannot be today or in the future."

    calc_age = today.year - parsed_date.year - ((today.month, today.day) < (parsed_date.month, parsed_date.day))
    if calc_age < min_age:
        return False, f"Player must be at least {min_age} years old."
    if calc_age > max_age:
        return False, f"Player age cannot exceed {max_age} years."

    return True, parsed_date


def validate_upi_id(upi_id: Optional[str], required: bool = False) -> Tuple[bool, Union[str, None]]:
    """Validate Virtual Payment Address (UPI ID)."""
    if not upi_id or not upi_id.strip():
        if required:
            return False, "UPI ID is required."
        return True, None

    cleaned = upi_id.strip().lower()
    if not RE_UPI_ID.match(cleaned):
        return False, "Invalid UPI ID format. Must follow username@bank (e.g. tourney@okhdfcbank)."
    return True, cleaned


def validate_transaction_id(tx_id: Optional[str], required: bool = True) -> Tuple[bool, Union[str, None]]:
    """Validate payment reference / UPI 12-digit UTR."""
    if not tx_id or not tx_id.strip():
        if required:
            return False, "Transaction ID / UTR Number is required for paid registrations."
        return True, None

    cleaned = tx_id.strip().replace(" ", "").upper()
    
    # Reject common placeholder junk
    invalid_placeholders = {"NONE", "NA", "N/A", "NULL", "TEST", "0", "0000", "1234", "PAID", "DONE"}
    if cleaned in invalid_placeholders or len(cleaned) < 8 or len(cleaned) > 30:
        return False, "Please enter a valid 12-digit UTR or bank transaction reference number."

    if not RE_TRANSACTION_ID.match(cleaned):
        return False, "Transaction ID can only contain letters and numbers."

    return True, cleaned


def validate_tournament_dates(start_date: Optional[date], end_date: Optional[date], reg_deadline: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
    """Validate tournament schedule consistency."""
    if not start_date or not end_date:
        return False, "Tournament start date and end date are both required."

    if end_date < start_date:
        return False, "Tournament end date cannot be earlier than start date."

    if reg_deadline:
        deadline_date = reg_deadline.date() if isinstance(reg_deadline, datetime) else reg_deadline
        if deadline_date > end_date:
            return False, "Registration deadline cannot be after the tournament ends."

    return True, None


def validate_operating_hours(start_str: str, end_str: str, num_courts: int, avg_duration: int) -> Tuple[bool, Optional[str]]:
    """Validate court operating hours, court counts, and match duration."""
    if not RE_TIME_HHMM.match(start_str) or not RE_TIME_HHMM.match(end_str):
        return False, "Operating hours must be in valid HH:MM 24-hour format."

    if end_str <= start_str:
        return False, f"Daily closing time ({end_str}) must be later than opening time ({start_str})."

    if num_courts < 1 or num_courts > 100:
        return False, "Number of courts must be between 1 and 100."

    if avg_duration < 15 or avg_duration > 360:
        return False, "Average match duration must be between 15 and 360 minutes."

    return True, None


def validate_score_value(score_val: Any, min_val: int = 0, max_val: int = 200, field_name: str = "Score") -> Tuple[bool, Union[int, str]]:
    """Validate individual score or game value."""
    if score_val is None or (isinstance(score_val, str) and not score_val.strip()):
        return False, f"{field_name} is required."
    try:
        val_int = int(score_val)
    except (ValueError, TypeError):
        return False, f"{field_name} must be an integer."

    if val_int < min_val:
        return False, f"{field_name} cannot be negative (minimum is {min_val})."
    if val_int > max_val:
        return False, f"{field_name} cannot exceed {max_val}."
    return True, val_int


def validate_username(username: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate username for user account."""
    if not username or not username.strip():
        return False, "Username is required."
    cleaned = username.strip()
    if not RE_USERNAME.match(cleaned):
        return False, "Username must be 3-30 characters long and can only contain letters, numbers, hyphens, and underscores."
    return True, cleaned


def validate_password(password: Optional[str], min_length: int = 8) -> Tuple[bool, Optional[str]]:
    """Validate password complexity."""
    if not password:
        return False, "Password is required."
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long."
    if not any(c.isdigit() or not c.isalnum() for c in password):
        return False, "Password must include at least one number or special character."
    return True, password
