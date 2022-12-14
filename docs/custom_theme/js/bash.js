terminal("#terminal-root", [
  { type: "input", value: "python -m pip install spoc" },
  { type: "progress", value: 100 },
  { value: "Successfully installed spoc", startDelay: 0 },
]);

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
  { type: "input", value: "touch config/__init__.py" },
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

terminal("#terminal-5", [
  { type: "input", value: "python main.py" },
  { value: "> Hello World (Commands)" },
]);

terminal("#terminal-overview", [
  { type: "input", value: "python -m pip install spoc Click" },
]);

terminal("#terminal-project", [
  { type: "input", value: "mkdir myproject" },
  { type: "input", value: "cd myproject" },
  { type: "input", value: "mkdir config" },
  { type: "input", value: "mkdir config/.env" },
  { type: "input", value: "mkdir framework" },
  { type: "input", value: "mkdir apps" },
  { type: "input", value: "mkdir apps/demo" },
]);

terminal("#terminal-framework", [
  { type: "input", value: "touch framework/framework.py" },
]);

terminal("#terminal-component", [
  { type: "input", value: "touch framework/components.py" },
]);

terminal("#terminal-component-commands", [
  { type: "input", value: "touch apps/demo/commands.py" },
]);

terminal("#terminal-config", [
  { type: "input", value: "touch config/settings.py" },
  { type: "input", value: "touch config/spoc.toml" },
  { type: "input", value: "touch config/.env/development.toml" },
]);

terminal("#terminal-extras", [
  { type: "input", value: "touch apps/demo/middleware.py" },
]);

terminal("#terminal-testing", [
  { type: "input", value: "python main.py hello-world" },
  { value: "> Hello World (Middleware)" },
  { value: "> Hello World (Commands)" },
]);
