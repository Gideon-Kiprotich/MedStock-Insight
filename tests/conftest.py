"""Isolated test configuration; never use a developer database or signing key."""
import os
from secrets import token_urlsafe

os.environ["DEBUG"] = "false"
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = token_urlsafe(48)
