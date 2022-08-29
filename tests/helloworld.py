"""
Project Config
"""

import pathlib

import spoc

"""
_________                        ________                .__               
\_   ___ \  ___________   ____   \______ \   ____   _____|__| ____   ____  
/    \  \/ /  _ \_  __ \_/ __ \   |    |  \_/ __ \ /  ___/  |/ ___\ /    \ 
\     \___(  <_> )  | \/\  ___/   |    `   \  ___/ \___ \|  / /_/  >   |  \
 \______  /\____/|__|    \___  > /_______  /\___  >____  >__\___  /|___|  /
        \/                   \/          \/     \/     \/  /_____/      \/ 
"""
# Core
CORE_MODULES = ["types", "graphql"]

# Init
Project = spoc.Spoc("ProjectName", CORE_MODULES)


"""
__________               __________                   __               __   
\______   \ ___________  \______   \_______  ____    |__| ____   _____/  |_ 
 |     ___// __ \_  __ \  |     ___/\_  __ \/  _ \   |  |/ __ \_/ ___\   __\
 |    |   \  ___/|  | \/  |    |     |  | \(  <_> )  |  \  ___/\  \___|  |  
 |____|    \___  >__|     |____|     |__|   \____/\__|  |\___  >\___  >__|  
               \/                                \______|    \/     \/      
"""

# Custom
BASE_DIR = pathlib.Path(__file__).resolve().parents[0]
INSTALLED_APPS = ["app_one", "app_two"]

# Config
Config = Project(base_dir=BASE_DIR, mode="api")

# Load Apps
Config.load_apps(installed_apps=INSTALLED_APPS)

"""
___________              __   
\__    ___/___   _______/  |_ 
  |    |_/ __ \ /  ___/\   __\
  |    |\  ___/ \___ \  |  |  
  |____| \___  >____  > |__|  
             \/     \/        
"""
# Test
test = Project()

print(test.mode, end="\n\n")
print(test.keys, end="\n\n")
print(test.schema["types"].keys())
print(test.schema["graphql"].keys())
