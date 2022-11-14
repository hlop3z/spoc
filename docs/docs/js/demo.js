terminal("#terminal-0", [
  { type: "input", value: "mkdir myproject" },
  { type: "input", value: "cd myproject" },
  { type: "input", value: "mkdir config" },
  { type: "input", value: "mkdir framework" },
  { type: "input", value: "mkdir apps" },
  { type: "input", value: "mkdir apps/demo" },
]);

terminal("#terminal-1", [
  { type: "input", value: "touch config/spoc.toml" },
  { type: "input", value: "touch config/settings.py" },
]);

terminal("#terminal-2", [
  { type: "input", value: "touch framework/framework.py" },
  { type: "input", value: "touch framework/components.py" },
  { type: "input", value: "touch framework/__init__.py" },
]);

terminal("#terminal-3", [
  { type: "input", value: "touch apps/demo/commands.py" },
]);

terminal("#terminal-4", [{ type: "input", value: "touch main.py" }]);
