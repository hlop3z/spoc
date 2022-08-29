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
class Admin:
    """Framework Builder"""

    plugins = ["types"]


@spoc.project
class Project:
    """Framework"""

    def init(
        self,
        base_dir: typing.Any = None,
        mode: str = "cli",
    ):
        """Class __init__ Replacement"""
        print("Load Once")

        # BASE_DIR <Collect: Some-How>
        installed_apps = ["app_one", "app_two"]

        # Load
        self.admin = Admin(base_dir=base_dir, mode=mode, installed_apps=installed_apps)
