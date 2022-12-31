import nox

source_dirs = [
    "hll_server_status",
]


@nox.session(tags=["style", "black"])
def black(session):
    session.run("black", *source_dirs, external=True)


@nox.session(tags=["style", "isort"])
def isort(session):
    session.run("isort", *source_dirs, external=True)
