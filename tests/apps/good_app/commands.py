import spoc


@spoc.plugin(config={"click": "command"})
class MyCommands:
    name: str
