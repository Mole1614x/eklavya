"""Provision or rotate an administrator through a trusted local command."""

import argparse
import getpass
import os

from sqlalchemy import or_, select

from .auth import hash_password, normalize_email, normalize_username
from .database import Session
from .models import AuditLog, Profile, User
from .schemas_auth import RegisterRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision an EKLAVYA administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()
    password = os.environ.get("EKLAVYA_ADMIN_PASSWORD") or getpass.getpass("Administrator password: ")
    validated = RegisterRequest(
        email=args.email, username=args.username, display_name=args.display_name, password=password,
    )
    email = normalize_email(validated.email)
    username = normalize_username(validated.username)
    with Session() as db:
        user = db.scalar(select(User).where(or_(User.email == email, User.username == username)))
        if user is not None and (user.email != email or user.username != username):
            raise SystemExit("The email or username belongs to a different account")
        if user is None:
            user = User(
                email=email, username=username, password_hash=hash_password(password),
                role="admin", is_active=True,
                profile=Profile(display_name=validated.display_name.strip()),
            )
            db.add(user)
            db.flush()
            action = "admin.provision"
        else:
            user.role = "admin"
            user.is_active = True
            user.password_hash = hash_password(password)
            user.profile.display_name = validated.display_name.strip()
            action = "admin.rotate_credentials"
        db.add(AuditLog(
            actor_user_id=None, action=action, target_type="user", target_id=str(user.id),
            details={"username": user.username, "method": "trusted_cli"}, ip_address=None,
        ))
        db.commit()
        print(f"Administrator ready: {user.username}")


if __name__ == "__main__":
    main()
