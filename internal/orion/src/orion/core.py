import sys

def assert_python():
    if sys.version_info < (3, 11):
        raise EnvironmentError("Python 3.11+ is required for Orion")

assert_python()

class OrionRuntime:
    def __init__(self):
        self.status = "initialized"

    def run(self):
        print("🚀 Orion Runtime Started")
        print("💡 Status:", self.status)