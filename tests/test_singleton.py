import pytest
import threading
import time
from typing import Any

from spoc.core.singleton import SingletonMeta, singleton


class TestSingleton:
    """Tests for the singleton module."""

    def test_singleton_meta(self):
        """Test the SingletonMeta metaclass."""

        # Define a class with the SingletonMeta metaclass
        class TestClass(metaclass=SingletonMeta):
            def __init__(self, value=None):
                self.value = value or "default"

        # Create multiple instances
        instance1 = TestClass()
        instance2 = TestClass("modified")
        instance3 = TestClass()

        # Verify all instances are the same object
        assert instance1 is instance2
        assert instance2 is instance3

        # Verify the value was only set once (by the first initialization)
        assert instance1.value == "default"
        assert instance2.value == "default"
        assert instance3.value == "default"

    def test_singleton_decorator(self):
        """Test the singleton decorator."""

        # Define classes with the singleton decorator
        @singleton
        class Service1:
            def __init__(self):
                self.name = "Service1"
                self.initialized = True

        @singleton
        class Service2:
            def __init__(self, value=None):
                self.name = "Service2"
                self.value = value or "default"

        # Create multiple instances
        service1_a = Service1()
        service1_b = Service1()

        service2_a = Service2()
        service2_b = Service2("modified")
        service2_c = Service2()

        # Verify instances of the same class are identical
        assert service1_a is service1_b
        assert service2_a is service2_b
        assert service2_b is service2_c

        # Verify different classes have different instances
        assert service1_a is not service2_a

        # Verify values are only set on first initialization
        assert service2_a.value == "default"
        assert service2_b.value == "default"
        assert service2_c.value == "default"

    def test_singleton_state_preservation(self):
        """Test that singleton instances preserve state between access."""

        @singleton
        class Counter:
            def __init__(self):
                self.count = 0

            def increment(self):
                self.count += 1
                return self.count

        # Create instance and modify state
        counter1 = Counter()
        assert counter1.count == 0

        counter1.increment()
        assert counter1.count == 1

        # Get another reference and verify state is preserved
        counter2 = Counter()
        assert counter2.count == 1
        assert counter1 is counter2

        counter2.increment()
        assert counter1.count == 2
        assert counter2.count == 2

    def test_singleton_meta_reset(self):
        """Test the reset functionality of SingletonMeta."""

        class TestClass(metaclass=SingletonMeta):
            def __init__(self):
                self.value = "initial"

        # Create first instance
        instance1 = TestClass()
        instance1.value = "modified"

        # Reset specific class
        SingletonMeta.reset(TestClass)

        # Create second instance after reset
        instance2 = TestClass()

        # Verify instances are different
        assert instance1 is not instance2
        assert instance1.value == "modified"
        assert instance2.value == "initial"

        # Reset all instances
        SingletonMeta.reset()

        # Create third instance after reset all
        instance3 = TestClass()

        # Verify it's a new instance
        assert instance2 is not instance3
        assert instance3.value == "initial"

    def test_singleton_decorator_reset(self):
        """Test the reset functionality of singleton decorator."""

        @singleton
        class ResetTest:
            def __init__(self):
                self.value = "initial"

        # Create first instance
        instance1 = ResetTest()
        instance1.value = "modified"

        # Reset the singleton
        ResetTest.reset()  # type: ignore

        # Create second instance after reset
        instance2 = ResetTest()

        # Verify instances are different
        assert instance1 is not instance2
        assert instance1.value == "modified"
        assert instance2.value == "initial"

    @pytest.mark.parametrize(
        "singleton_implementation,cls_name",
        [(SingletonMeta, "MetaClass"), (singleton, "DecoratorClass")],
    )
    def test_singleton_implementations(
        self, singleton_implementation: Any, cls_name: str
    ):
        """Parameterized test to verify both singleton implementations behave the same."""

        if singleton_implementation is SingletonMeta:
            # Create a class with the metaclass properly defined
            class TestClass(metaclass=SingletonMeta):
                pass

            # Set the class name to match the parameter
            TestClass.__name__ = cls_name
            cls = TestClass
        else:
            # Create class and apply decorator
            cls = type(cls_name, (), {"__module__": __name__})
            cls = singleton_implementation(cls)

        # Create instances
        instance1 = cls()
        instance2 = cls()

        # Verify they are the same object
        assert instance1 is instance2

    def test_thread_safety(self):
        """Test that singletons are thread-safe."""
        # This test uses a counter to verify that the singleton
        # is properly protected against race conditions

        results = []
        creation_count = 0

        # Since we're defining the ThreadTest class inside this method,
        # we need to make sure it's cleaned up before and after the test
        SingletonMeta.reset()

        # Use a barrier to make threads attempt to create the singleton at the same time
        thread_count = 10
        barrier = threading.Barrier(thread_count)

        # Define a class with singleton metaclass
        class ThreadTest(metaclass=SingletonMeta):
            def __init__(self):
                nonlocal creation_count
                # Simulate some initialization work
                time.sleep(0.01)
                creation_count += 1
                self.id = creation_count

        def create_and_check():
            # Wait for all threads to reach this point
            barrier.wait()
            # Now all threads will try to create instances almost simultaneously
            instance = ThreadTest()
            results.append(instance.id)
            return instance

        # Create instances simultaneously in multiple threads
        instances = []
        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(
                target=lambda: instances.append(create_and_check())
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all instances are the same
        first = instances[0]
        for instance in instances[1:]:
            assert instance is first

        # Verify constructor was called exactly once
        assert creation_count == 1

        # Verify all threads got the same instance ID
        assert all(r == 1 for r in results)

        # Reset for other tests
        SingletonMeta.reset()

    def test_inheritance(self):
        """Test singleton behavior with inheritance."""

        class BaseSingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.base_value = "base"

        class ChildSingleton(BaseSingleton):
            def __init__(self):
                super().__init__()
                self.child_value = "child"

        # Create instances of base and child
        base1 = BaseSingleton()
        base2 = BaseSingleton()
        child1 = ChildSingleton()
        child2 = ChildSingleton()

        # Verify each class has its own singleton
        assert base1 is base2
        assert child1 is child2
        assert base1 is not child1

        # Verify values are preserved
        assert base1.base_value == "base"
        assert child1.base_value == "base"
        assert child1.child_value == "child"
