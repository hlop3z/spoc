"""

___________                            __      __             __    
\_   _____/___________    _____   ____/  \    /  \___________|  | __
 |    __) \_  __ \__  \  /     \_/ __ \   \/\/   /  _ \_  __ \  |/ /
 |     \   |  | \// __ \|  Y Y  \  ___/\        (  <_> )  | \/    < 
 \___  /   |__|  (____  /__|_|  /\___  >\__/\  / \____/|__|  |__|_ \
     \/               \/      \/     \/      \/                   \/

"""

import typing

import spoc


@spoc.framework
class Framework:
    """Framework Builder"""

    plugins = ["types", "graphql", "router", "commands"]


@spoc.singleton
class Project:
    """Framework"""

    def init(
        self,
        mode: str = "cli",
    ):
        """Class __init__ Replacement"""

        # Create Framework
        Framework(app=self)
        
        # Do Something before initialization of { Singleton }
        print(mode)

        # Finally: Collect { Keys }
        self.keys = [x for x in spoc.get_fields(self) if x not in ["init"]]
