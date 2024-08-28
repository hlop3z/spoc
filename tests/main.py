"""Main"""

from framework import MyFramework, components

import spoc

app = MyFramework()

print(spoc.settings.CONFIG)


def print_the_parts():
    print("DEBUG", spoc.settings.DEBUG)
    print("MODE", spoc.settings.MODE)
    # print("SPOC", spoc.settings.SPOC)
    # print("ENV", spoc.settings.ENV)
    # print("CONFIG", spoc.settings.CONFIG)
    # print(test.components.__dict__.keys())
    # print(test.extras)

    print(app.plugins)
    print(app.components)
    # Print components groups
    print(app.components.__dict__.keys())

    # Print plugin groups
    print(app.plugins.keys())


def execute_registered_command():
    # Execute the registered command
    app.components.commands["demo.hello_world"].object()


'''
for method in test.plugins.get("middleware", []):
    print(method)


for component in test.components.commands.values():
    is_my_type = components.is_component("command", component)
    print(f"""Is the component of the <type> assigned? {is_my_type}""")
    print(component)
'''

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


def test_server_workers():
    time.sleep(1)
    MyServer.add(SyncProcess(name="One"))
    MyServer.add(AsyncProcess(name="Two"))
    MyServer.start()
    # time.sleep(3)
    # MyServer.stop()


if __name__ == "__main__":
    """Run Tests"""
    # print(test.__core__.keys())
    # test_server_workers()
    # print_the_parts()
    # execute_registered_command()
    app.cli()
