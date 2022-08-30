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


@spoc.project
class Project:
    """Framework"""

    def init(
        self,
        base_dir: typing.Any = None,
        mode: str = "cli",
    ):
        """Class __init__ Replacement"""

        # Step[1]: INIT { Admin }
        Framework(base_dir=base_dir, mode=mode, app=self)

        # Finally: Collect { Keys }
        self.keys = [x for x in spoc.get_fields(self) if x not in ["init"]]
