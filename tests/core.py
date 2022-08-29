intial_setup_fastberry = {
    "spoc": {
        "name": "my-project",
        "version": "0.1.0",
        "config": {"mode": "development", "docs": "mydocs.md"},
        "apps": {
            "production": [],
            "development": [],
            "staging": [],
        },
        "graphql": {"items_per_page": 50, "max_depth": 4, "generates": "graphql"},
        "fastapi": {
            "allowed_hosts": [],
            "middleware": [],
            "extensions": [],
            "permissions": [],
            "on_startup": [],
            "on_shutdown": [],
        },
    }
}


intial_setup_spoc = {
    "spoc": {
        "name": "my-project",
        "version": "0.1.0",
        "config": {"mode": "development", "docs": "mydocs.md"},
        "apps": {
            "production": [],
            "development": [],
            "staging": [],
        },
    }
}
