from framework import MyFramework
import spoc

test = MyFramework()

print(spoc.env)

print(test.component.commands["demo.test"].object)

for method in test.extras.get("middleware", []):
    print(method)


# print(test.plugin.commands.values())
print(spoc.settings)
