"""Main"""

import time
import asyncio
import os


from framework import MyFramework, components

import spoc

app = MyFramework()


def print_the_parts():
    print("DEBUG", spoc.settings.DEBUG)
    print("MODE", spoc.settings.MODE)
    # print("SPOC", dict(spoc.settings.SPOC))
    # print("ENV", spoc.settings.ENV)
    # print("CONFIG", spoc.settings.CONFIG)

    # print(app.plugins)
    # print(app.components)
    # print(components._components)

    # Print components groups
    print(app.components.__dict__.keys())

    # Print plugin groups
    print(app.plugins.keys())


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
    MyServer.start(False)
    print(MyServer.subprocess_force_stop())
    # time.sleep(3)
    MyServer.stop()


if __name__ == "__main__":
    """Run Tests"""
    # print(test.__core__.keys())
    test_server_workers()
    # print_the_parts()
    # execute_registered_command()
    # app.cli()
