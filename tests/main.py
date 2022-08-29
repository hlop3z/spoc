"""
__________               __________                   __               __   
\______   \ ___________  \______   \_______  ____    |__| ____   _____/  |_ 
 |     ___// __ \_  __ \  |     ___/\_  __ \/  _ \   |  |/ __ \_/ ___\   __\
 |    |   \  ___/|  | \/  |    |     |  | \(  <_> )  |  \  ___/\  \___|  |  
 |____|    \___  >__|     |____|     |__|   \____/\__|  |\___  >\___  >__|  
               \/                                \______|    \/     \/      
"""


from framework import Project

import spoc

# Custom
BASE_DIR = spoc.root(__file__)[0]

# Config
App = Project(base_dir=BASE_DIR, mode="cli")

"""
___________              __   
\__    ___/___   _______/  |_ 
  |    |_/ __ \ /  ___/\   __\
  |    |\  ___/ \___ \  |  |  
  |____| \___  >____  > |__|  
             \/     \/        
"""

print(App.admin.keys)

print(App.admin.modules["types.app_two.mytype"])

# print(Project().admin.plugins)
print(Project().admin.schema)
# print(Project().admin.schema.types["app_two.mytype"])
