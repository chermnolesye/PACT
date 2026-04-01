project_version = "german"
local_settings_loaded = False

try:
    from . import local
    local_settings_loaded = True

    if getattr(local, "PACT_PROJECT_VERSION", None) in ("german", "french"):
        project_version = local.PACT_PROJECT_VERSION
except ImportError:
    local = None

if project_version == "french":
    from .french import *
else:
    from .german import *

if local_settings_loaded:
    from .local import *
else:
    print("LOCAL SETTINGS NOT FOUND, USE DEFAULT SETTINGS!")