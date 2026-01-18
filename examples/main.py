# Standard Library
from pprint import pprint

from framework import App


if __name__ == "__main__":
    app = App()
    app.startup()
    # pprint(app.config)
    # print("\n")
    print(app.get_components("models"))
    # print(app.get_component("models", "auth.UserAccount"))
    # Later...
    # loader.shutdown()

    # app.shutdown()
