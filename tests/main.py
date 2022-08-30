"""
__________               __________                   __               __   
\______   \ ___________  \______   \_______  ____    |__| ____   _____/  |_ 
 |     ___// __ \_  __ \  |     ___/\_  __ \/  _ \   |  |/ __ \_/ ___\   __\
 |    |   \  ___/|  | \/  |    |     |  | \(  <_> )  |  \  ___/\  \___|  |  
 |____|    \___  >__|     |____|     |__|   \____/\__|  |\___  >\___  >__|  
               \/                                \______|    \/     \/      
"""


from fastberry import Project

import spoc

# Base Directory
BASE_DIR = spoc.root(__file__)[0]

# App
App = Project(base_dir=BASE_DIR, mode="cli")

"""
___________              __   
\__    ___/___   _______/  |_ 
  |    |_/ __ \ /  ___/\   __\
  |    |\  ___/ \___ \  |  |  
  |____| \___  >____  > |__|  
             \/     \/        
"""

# print(App.admin.keys)
# print(App.admin.modules["types.app_two.mytype"])
# print(Project().admin.plugins)
# print(Project().admin.schema)
# print(Project().admin.schema.types["app_two.mytype"])
# print(Project().admin.schema)
# print(App.admin.keys)

#print(App.core.modules)
print(App.core.keys)
# print(App.admin.plugins.modules)
"""
print(App.core.schema.types)
print(App.core.schema.graphql)
print(App.core.schema.router)
print(App.core.schema.commands)
"""
