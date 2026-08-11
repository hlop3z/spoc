from pathlib import Path

from framework import framework

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

    # Cross-namespace at runtime: orders reaches catalog through the registry
    summary = framework.resolve("views:orders.order_summary").object()
    print("Order total:", summary["total_cents"], "cents")

    # A view reaches the live resource mid-call (opened by the kind's hook)
    hit = framework.resolve("views:catalog.find_product").object("mouse")
    print("Search hit:", hit["product"]["name"])

    # Enumerate the whole registry (deterministic order)
    for component in framework.registry:
        print(" -", component.identifier)

    framework.shutdown()
