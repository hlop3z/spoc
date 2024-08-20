"""Main"""

from framework import MyFramework

import spoc

test = MyFramework()

print("DEBUG", spoc.settings.DEBUG)
print("MODE", spoc.settings.MODE)
print("SPOC", spoc.settings.SPOC)
print("ENV", spoc.settings.ENV)
print("CONFIG", spoc.settings.CONFIG)


print(test.components.__dict__.keys())
print(test.extras)
# print(test.components.commands)
# print(test.components.commands.get("demo.test").object)

for method in test.extras.get("middleware", []):
    print(method)


# print(test.plugin.commands.values())


class MyProcess(spoc.BaseProcess):  # spoc.BaseThread
    """Ignore"""

    def on_event(self, event_type):
        print(event_type)

    async def server(self):
        pass


class MyClass(spoc.BaseServer):
    """Ignore"""

    @classmethod
    def on_event(cls, event_type):
        print(event_type)


MyProcess()
MyClass.start(False)
