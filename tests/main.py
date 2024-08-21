"""Main"""

from framework import MyFramework, components

import spoc

test = MyFramework()

print("DEBUG", spoc.settings.DEBUG)
print("MODE", spoc.settings.MODE)
# print("SPOC", spoc.settings.SPOC)
# print("ENV", spoc.settings.ENV)
# print("CONFIG", spoc.settings.CONFIG)
# print(test.components.__dict__.keys())
# print(test.extras)

for method in test.extras.get("middleware", []):
    print(method)


for component in test.components.commands.values():
    is_my_type = components.is_component("command", component)
    print(f"""Is the plugin of the <type> assigned? {is_my_type}""")
    print(component)


import time
import asyncio
import os


class AsyncProcess(spoc.BaseProcess):  # spoc.BaseThread
    async def on_event(self, event_type):
        print("Process:", event_type, os.getpid())

    async def server(self):
        while self.active:
            print("My Server", self.options.name)
            await asyncio.sleep(1)


class SyncProcess(spoc.BaseThread):  # spoc.BaseThread
    def on_event(self, event_type):
        print("Thread:", event_type, os.getpid())

    def server(self):
        while self.active:
            print("My Server", self.options.name)
            time.sleep(1)


class MyServer(spoc.BaseServer):
    @classmethod  # or staticmethod
    def on_event(cls, event_type):
        print("Server:", event_type)


if __name__ == "__main__":
    time.sleep(1)
    MyServer.add(SyncProcess(name="One"))
    MyServer.add(AsyncProcess(name="Two"))
    MyServer.start()
    # time.sleep(3)
    # MyServer.stop()
