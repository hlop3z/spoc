from framework import command


@command(group=True)
def cli():
    "Click Group"


@cli.command()
def other_cmd():
    print("Other (Command)")


@command
def hello_world():
    print("Hello World (Command)")
