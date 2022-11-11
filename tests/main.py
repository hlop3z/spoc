from framework import MyFramework
from components import command, COMPONENT

import spoc

@command
def test():
    print("Hello World")


print(spoc.is_component(test, COMPONENT["command"]))

