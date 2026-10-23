"""Seed default dropdown values (user types, platforms, priorities, WhatsApp
template keys, SLA rules).

Usage: python -m scripts.seed_defaults
"""

from apps.configuration.seed import seed_defaults


def main():
    created = seed_defaults()
    if not created:
        print("Nothing to seed — defaults already present.")
        return
    for item in created:
        print(f"created {item}")
    print(f"Seeded {len(created)} config values.")


if __name__ == "__main__":
    main()
