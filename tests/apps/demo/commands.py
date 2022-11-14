from framework import commands, components

import spoc

@commands
def test():
    print("Hello World")


is_my_type = spoc.is_component(test, components["command"])

print(f"""
Hello From 'apps/demo/commands.py'
is the plugin of the <type> I designed? {is_my_type}      
""")
