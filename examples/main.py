from pathlib import Path

from framework.framework import framework

BASE_DIR = Path(__file__).resolve().parent


@framework.on_ready
def announce(registry):
    print(f"Ready: {len(registry)} components registered")


if __name__ == "__main__":
    framework.start(BASE_DIR)
    print("Installed apps:", framework.installed_apps)

    # Resolve one component by its canonical identifier
    record = framework.resolve("models:auth.user_account")
    print("Resolved:", record.identifier, "->", record.object)

    # Enumerate the whole registry (deterministic order)
    for component in framework.registry:
        print(" -", component.identifier)

    framework.shutdown()
