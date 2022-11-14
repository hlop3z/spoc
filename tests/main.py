from framework import MyFramework

test = MyFramework()

print(test.env)

print(test.component.commands['demo.test'].object)

for method in test.extras['middleware']:
    print(method)
    

# print(test.plugin.commands.values())
