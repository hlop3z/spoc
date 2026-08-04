from framework.framework import framework

if __name__ == "__main__":
    print("Installed apps:", framework.installed_apps)

    # Resolve one component by its canonical identifier
    record = framework.resolve("models:auth.user_account")
    print("Resolved:", record.identifier, "->", record.object)

    # Enumerate the whole registry (deterministic order)
    for component in framework.registry:
        print(" -", component.identifier)

    framework.shutdown()
