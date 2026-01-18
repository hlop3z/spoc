import asyncio
import time

from spoc.workers import ProcessWorker, Server, ThreadWorker


class Dummy:
    pass


class CountingAsyncWorker(ThreadWorker):
    async def main(self):
        count = 0
        while self.is_running:
            count += 1
            print(f"{self.name} Count: {count}")
            await asyncio.sleep(1)

    async def lifecycle(self, event_type, **data):
        print(self.context)
        print(f"{self.name} Event: {event_type}")


class CountingSyncWorker(ProcessWorker):
    def main(self):
        count = 0
        print(self.context)
        while self.is_running:
            count += 1
            print(f"{self.name} Count: {count}")
            time.sleep(1)

    def lifecycle(self, event_type, **data):
        match event_type:
            case "startup":
                self.context.app = Dummy()
            case "shutdown":
                print(self.context)
        print(f"{self.name} Event: {event_type}")


# --- Example Usage ---
if __name__ == "__main__":
    server = Server("UnifiedOrchestrator")
    server.add_worker(CountingAsyncWorker("Async-Counter"))
    server.add_worker(CountingSyncWorker("iSync-Counter"))

    try:
        server.run_forever()
    except KeyboardInterrupt:
        print("Main: Received KeyboardInterrupt, shutting down.")
