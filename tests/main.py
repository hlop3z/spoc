from framework import MyFramework
import spoc

test = MyFramework()

print(spoc.env)

print(test.component.commands["demo.test"].object)

for method in test.extras.get("middleware", []):
    print(method)


# print(test.plugin.commands.values())
print(spoc.settings)


class MyProcess(spoc.BaseProcess):  # spoc.BaseThread
    """Ignore"""

    def on_event(self, event_type):
        print(event_type)

    async def server():
        pass


class MyClass(spoc.BaseServer):
    """Ignore"""

    @classmethod
    def on_event(cls, event_type):
        print(event_type)


MyProcess()
MyClass.start(False)
