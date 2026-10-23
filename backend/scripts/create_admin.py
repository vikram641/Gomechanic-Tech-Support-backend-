"""Bootstrap the first admin account (there's no Django ORM superuser here).

Usage: python -m scripts.create_admin --name "Admin" --email admin@gomechanic.in
"""

import argparse
import getpass
import sys

from apps.accounts import repository


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=False)
    args = parser.parse_args()

    password = args.password or getpass.getpass("Admin password: ")
    try:
        user = repository.create_user(name=args.name, email=args.email, password=password, role="admin")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Created admin '{user['email']}'.")


if __name__ == "__main__":
    main()
