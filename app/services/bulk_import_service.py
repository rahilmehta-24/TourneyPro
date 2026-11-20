"""
Bulk CSV Import Service for Baseline Society Tournament Participants
Provides robust validation, duplicate detection, formula injection prevention,
idempotency, and transactional participant creation.
"""

import csv
import hashlib
import io
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from app.domain.models import db, Player, Participant, Registration, Category, Tournament, ParticipantImportBatch, User
from app.services.utils.audit import log_audit


MAX_CSV_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_CSV_ROWS = 1000

# Mapping of canonical fields to expected CSV column header variations
COLUMN_ALIASES = {
    "first_name": ["first name", "firstname", "first", "first_name"],
    "last_name": ["last name", "lastname", "last", "last_name"],
    "email": ["email", "e-mail", "email address", "email_address"],
    "phone": ["phone number", "phone", "mobile", "contact number", "contact", "phone_number"],
    "category": ["tournament category", "category", "category name", "event", "category_name"],
    "registration_type": ["registration type", "type", "event type", "registration_type"],
    "doubles_partner": [
        "doubles partner identifier or email",
        "doubles partner",
        "partner identifier",
        "partner",
        "partner email",
        "partner name",
        "partner_identifier",
        "doubles_partner"
    ],
    "player_level": ["player level", "level", "skill level", "skill_level", "player_level"],
    "notes": ["optional notes", "notes", "remarks", "comment", "comments"]
}


def sanitize_for_csv_injection(val: Any) -> str:
    """
    Mitigate CSV Formula Injection (CWE-1236) by prepending a single quote
    if cell value starts with '=', '+', '-', '@', tab, or carriage return.
    """
    if val is None:
        return ""
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


def generate_csv_template() -> str:
    """
    Generates a UTF-8 CSV template string with headers and sample rows.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "First Name",
        "Last Name",
        "Email",
        "Phone Number",
        "Tournament Category",
        "Registration Type",
        "Doubles Partner Identifier",
        "Player Level",
        "Notes"
    ]
    writer.writerow(headers)
    writer.writerow([
        "Roger", "Federer", "roger@example.com", "9876543210",
        "Men's Singles", "Singles", "", "Pro", "Seed 1"
    ])
    writer.writerow([
        "Rafael", "Nadal", "rafael@example.com", "9876543211",
        "Men's Doubles", "Doubles", "Carlos Alcaraz", "Pro", "Doubles pair"
    ])
    return output.getvalue()


def _normalize_header(header: str) -> str:
    return re.sub(r"[_\-\s]+", " ", header.strip().lower())


def _resolve_column_mapping(fieldnames: List[str]) -> Dict[str, str]:
    """
    Resolves CSV file headers to canonical column keys.
    """
    mapping = {}
    normalized_headers = {_normalize_header(h): h for h in fieldnames if h}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            norm_alias = _normalize_header(alias)
            if norm_alias in normalized_headers:
                mapping[canonical] = normalized_headers[norm_alias]
                break
    return mapping


def validate_and_parse_csv(
    tournament: Tournament,
    file_bytes: bytes,
    original_filename: str,
    organizer_id: int
) -> Dict[str, Any]:
    """
    Validates CSV file content, structure, categories, and rows.
    Detects intra-file and database duplicates.
    Creates a ParticipantImportBatch in status PENDING_CONFIRMATION.
    """
    if len(file_bytes) > MAX_CSV_FILE_SIZE:
        raise ValueError(f"File size exceeds the maximum limit of {MAX_CSV_FILE_SIZE // (1024*1024)}MB.")

    # Calculate SHA-256 for idempotency and tracking
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Decode content
    try:
        content_str = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content_str = file_bytes.decode("latin-1")
        except Exception:
            raise ValueError("Invalid file encoding. Please upload a valid UTF-8 CSV file.")

    csv_file = io.StringIO(content_str)
    # Check for empty file
    first_char = content_str.strip()
    if not first_char:
        raise ValueError("The uploaded CSV file is empty.")

    reader = csv.reader(csv_file)
    try:
        headers = next(reader)
    except StopIteration:
        raise ValueError("CSV file contains no headers.")

    mapping = _resolve_column_mapping(headers)
    required_cols = ["first_name", "last_name", "category"]
    missing = [col for col in required_cols if col not in mapping]
    if missing:
        readable_missing = [c.replace("_", " ").title() for c in missing]
        raise ValueError(f"Missing required CSV columns: {', '.join(readable_missing)}.")

    # Load categories for tournament (case-insensitive lookup)
    categories_by_name = {c.name.strip().lower(): c for c in tournament.categories}

    total_rows = 0
    valid_rows: List[Dict[str, Any]] = []
    invalid_rows: List[Dict[str, Any]] = []
    duplicate_rows: List[Dict[str, Any]] = []

    seen_intra_file = set()

    # Re-read with DictReader
    csv_file.seek(0)
    dict_reader = csv.DictReader(csv_file)

    for row_idx, row in enumerate(dict_reader, start=2):  # Row 1 is header
        total_rows += 1
        if total_rows > MAX_CSV_ROWS:
            raise ValueError(f"CSV row limit exceeded. Maximum {MAX_CSV_ROWS} rows permitted per import.")

        first_name = (row.get(mapping.get("first_name", "")) or "").strip()
        last_name = (row.get(mapping.get("last_name", "")) or "").strip()
        email = (row.get(mapping.get("email", "")) or "").strip()
        phone = (row.get(mapping.get("phone", "")) or "").strip()
        cat_name = (row.get(mapping.get("category", "")) or "").strip()
        reg_type = (row.get(mapping.get("registration_type", "")) or "").strip() or "Singles"
        partner = (row.get(mapping.get("doubles_partner", "")) or "").strip()
        level = (row.get(mapping.get("player_level", "")) or "").strip()
        notes = (row.get(mapping.get("notes", "")) or "").strip()

        row_data = {
            "row_number": row_idx,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}".strip(),
            "email": email.lower() if email else "",
            "phone": phone,
            "category_name": cat_name,
            "registration_type": reg_type,
            "doubles_partner": partner,
            "player_level": level,
            "notes": notes,
        }

        # 1. Required field checks
        if not first_name or not last_name:
            row_data["error"] = "First name and Last name are required."
            invalid_rows.append(row_data)
            continue

        if not cat_name:
            row_data["error"] = "Tournament category is required."
            invalid_rows.append(row_data)
            continue

        # 2. Email format validation if provided
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            row_data["error"] = f"Invalid email format: '{email}'."
            invalid_rows.append(row_data)
            continue

        # 3. Category existence & status check
        category = categories_by_name.get(cat_name.lower())
        if not category:
            row_data["error"] = f"Category '{cat_name}' does not exist in this tournament."
            invalid_rows.append(row_data)
            continue

        row_data["category_id"] = category.id

        if not category.is_registration_open or getattr(category, "registration_status", "OPEN") != "OPEN":
            row_data["error"] = f"Registration for category '{category.name}' is closed."
            invalid_rows.append(row_data)
            continue

        # 4. Check category participant limit
        if category.max_participants and category.max_participants > 0:
            current_count = len(category.participants)
            if current_count >= category.max_participants:
                row_data["error"] = f"Category '{category.name}' has reached its participant capacity ({category.max_participants})."
                invalid_rows.append(row_data)
                continue

        # 5. Doubles validation
        is_doubles = (
            "doubles" in reg_type.lower()
            or "doubles" in category.name.lower()
            or (category.format and "doubles" in category.format.lower())
        )
        if is_doubles:
            if not partner:
                row_data["error"] = "Doubles registrations require a partner identifier or name."
                invalid_rows.append(row_data)
                continue
            if partner.lower() == row_data["full_name"].lower() or (email and partner.lower() == email.lower()):
                row_data["error"] = "Doubles partner cannot be the same player."
                invalid_rows.append(row_data)
                continue

        # 6. Intra-file duplicate check
        file_key = (row_data["full_name"].lower(), email.lower() if email else phone, category.id)
        if file_key in seen_intra_file:
            row_data["error"] = "Duplicate registration within this CSV file."
            duplicate_rows.append(row_data)
            continue
        seen_intra_file.add(file_key)

        # 7. Database duplicate check
        # Look for existing participant in category with same name or email
        existing_participant = Participant.query.filter(
            Participant.tournament_id == tournament.id,
            Participant.category_id == category.id,
            (
                (Participant.name == row_data["full_name"])
                | ((Participant.email != "") & (Participant.email == email))
                | ((Participant.mobile != "") & (Participant.mobile == phone))
            )
        ).first()

        if existing_participant:
            row_data["error"] = f"Player '{row_data['full_name']}' is already registered/participating in '{category.name}'."
            duplicate_rows.append(row_data)
            continue

        valid_rows.append(row_data)

    # Compile error data for rejected rows (invalid + duplicate)
    all_errors = invalid_rows + duplicate_rows

    batch = ParticipantImportBatch(
        tournament_id=tournament.id,
        user_id=organizer_id,
        filename=original_filename,
        file_hash=file_hash,
        total_rows=total_rows,
        valid_rows=len(valid_rows),
        invalid_rows=len(invalid_rows),
        duplicate_rows=len(duplicate_rows),
        imported_rows=0,
        status="PENDING_CONFIRMATION",
        error_data=json.dumps({"errors": all_errors, "valid": valid_rows}),
        created_at=datetime.utcnow()
    )
    db.session.add(batch)
    db.session.commit()

    return {
        "batch_id": batch.id,
        "filename": original_filename,
        "total_rows": total_rows,
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "duplicate_count": len(duplicate_rows),
        "preview_valid": valid_rows[:10],
        "preview_errors": all_errors[:10],
        "valid_rows": valid_rows,  # full list for confirmation
    }


def execute_import_batch(batch_id: int, organizer_id: int, valid_rows: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, str, int]:
    """
    Executes and commits the valid rows for a pending import batch in a database transaction.
    Guarantees idempotency and prevents double-import.
    """
    batch = ParticipantImportBatch.query.get(batch_id)
    if not batch:
        return False, "Import batch not found.", 0

    if batch.status == "COMPLETED":
        return True, "Batch has already been imported.", batch.imported_rows

    tournament = batch.tournament
    if not tournament:
        return False, "Target tournament not found.", 0

    # If valid_rows not provided in arguments, reconstruct from cached batch data
    if not valid_rows and batch.error_data:
        try:
            cached_data = json.loads(batch.error_data)
            if isinstance(cached_data, dict):
                valid_rows = cached_data.get("valid", [])
        except Exception:
            valid_rows = []

    if valid_rows is None:
        valid_rows = []

    imported_count = 0

    try:
        with db.session.begin_nested():
            for row in valid_rows:
                cat_id = row.get("category_id")
                category = Category.query.get(cat_id)
                if not category or category.tournament_id != tournament.id:
                    continue

                full_name = row["full_name"]
                email = row.get("email") or ""
                phone = row.get("phone") or ""
                partner = row.get("doubles_partner") or None
                notes = row.get("notes") or ""
                level = row.get("player_level") or None

                # Find or create Player
                player = None
                if email:
                    player = Player.query.filter_by(email=email).first()
                if not player and phone:
                    player = Player.query.filter_by(contact_number=phone).first()
                if not player:
                    player = Player.query.filter_by(name=full_name).first()

                if not player:
                    # Match user if exists
                    user_match = User.query.filter_by(email=email).first() if email else None
                    player = Player(
                        user_id=user_match.id if user_match else None,
                        name=full_name,
                        email=email or None,
                        contact_number=phone or None,
                        skill_level=level,
                        bio=notes or None,
                        gender="Male" if "women" not in category.name.lower() and "girl" not in category.name.lower() else "Female"
                    )
                    db.session.add(player)
                    db.session.flush()

                # Build participant name
                participant_display_name = full_name
                if partner:
                    participant_display_name = f"{full_name} / {partner}"

                # Create Participant
                participant = Participant(
                    tournament_id=tournament.id,
                    category_id=category.id,
                    player_id=player.id,
                    name=participant_display_name,
                    email=email,
                    mobile=phone,
                    gender=player.gender,
                    partner_name=partner,
                    payment_status="paid",
                    payment_method="cash",
                )
                db.session.add(participant)

                # Create Registration record
                reg = Registration(
                    tournament_id=tournament.id,
                    category_id=category.id,
                    user_id=organizer_id,
                    player_id=player.id,
                    partner_name=partner,
                    status="approved",
                    payment_status="paid",
                    payment_method="cash",
                    transaction_id=f"CSV_BATCH_{batch.id}"
                )
                db.session.add(reg)
                imported_count += 1

            batch.imported_rows = imported_count
            batch.status = "COMPLETED" if imported_count == batch.valid_rows else "PARTIAL"
            batch.completed_at = datetime.utcnow()

        db.session.commit()

        # Audit Log
        log_audit(
            action_type="IMPORT_PARTICIPANTS_CSV",
            target_id=tournament.id,
            target_name=tournament.name,
            reason="Bulk CSV import committed",
            details={
                "batch_id": batch.id,
                "filename": batch.filename,
                "total_rows": batch.total_rows,
                "imported_rows": imported_count,
                "invalid_rows": batch.invalid_rows,
                "duplicate_rows": batch.duplicate_rows,
                "status": batch.status
            },
            user_id=organizer_id
        )

        return True, f"Successfully imported {imported_count} participant(s).", imported_count

    except Exception as e:
        db.session.rollback()
        batch.status = "FAILED"
        db.session.commit()
        return False, f"Import transaction failed: {str(e)}", 0


def generate_error_csv_report(batch: ParticipantImportBatch) -> str:
    """
    Generates a downloadable CSV containing all failed and duplicate rows with exact reasons,
    properly protected against CSV formula injection.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Row Number",
        "First Name",
        "Last Name",
        "Email",
        "Phone Number",
        "Category",
        "Registration Type",
        "Doubles Partner",
        "Error Reason"
    ])

    if batch.error_data:
        try:
            raw_data = json.loads(batch.error_data)
            if isinstance(raw_data, dict):
                errors = raw_data.get("errors", [])
            elif isinstance(raw_data, list):
                errors = raw_data
            else:
                errors = []
        except Exception:
            errors = []

        for item in errors:
            writer.writerow([
                sanitize_for_csv_injection(item.get("row_number", "")),
                sanitize_for_csv_injection(item.get("first_name", "")),
                sanitize_for_csv_injection(item.get("last_name", "")),
                sanitize_for_csv_injection(item.get("email", "")),
                sanitize_for_csv_injection(item.get("phone", "")),
                sanitize_for_csv_injection(item.get("category_name", "")),
                sanitize_for_csv_injection(item.get("registration_type", "")),
                sanitize_for_csv_injection(item.get("doubles_partner", "")),
                sanitize_for_csv_injection(item.get("error", "Unknown error")),
            ])

    return output.getvalue()
