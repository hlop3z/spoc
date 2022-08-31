import spoc


@spoc.component(config={"click": "command"})
class MyCommands:
    name: str
