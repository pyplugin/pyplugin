import os

from hypothesis import settings
from hypothesis.database import (
    DirectoryBasedExampleDatabase,
    ReadOnlyDatabase,
    GitHubArtifactDatabase,
    MultiplexedDatabase,
)


local = DirectoryBasedExampleDatabase(".hypothesis/examples")
shared = ReadOnlyDatabase(GitHubArtifactDatabase("user", "repo"))

settings.register_profile("ci", database=local)
settings.register_profile("dev", database=MultiplexedDatabase(local, shared))
# We don't want to use the shared database in CI, only to populate its local one.
# which the workflow should then upload as an artifact.
settings.load_profile("ci" if os.environ.get("CI") else "dev")
