from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from sircom2026._database_artifacts import ArtifactsRepository
from sircom2026._database_events import EventsRepository
from sircom2026._database_jobs import JobsRepository
from sircom2026._database_lots import LotsRepository
from sircom2026._database_problems import ProblemsRepository
from sircom2026._database_purge import PurgeTracesRepository
from sircom2026._database_steps import StepsRepository

__all__ = [
    "ArtifactsRepository",
    "EventsRepository",
    "JobsRepository",
    "LotsRepository",
    "ProblemsRepository",
    "PurgeTracesRepository",
    "Repositories",
    "StepsRepository",
]


@dataclass(frozen=True)
class Repositories:
    connection: sqlite3.Connection

    @property
    def lots(self) -> LotsRepository:
        return LotsRepository(self.connection)

    @property
    def steps(self) -> StepsRepository:
        return StepsRepository(self.connection)

    @property
    def jobs(self) -> JobsRepository:
        return JobsRepository(self.connection)

    @property
    def artifacts(self) -> ArtifactsRepository:
        return ArtifactsRepository(self.connection)

    @property
    def events(self) -> EventsRepository:
        return EventsRepository(self.connection)

    @property
    def problems(self) -> ProblemsRepository:
        return ProblemsRepository(self.connection)

    @property
    def purge_traces(self) -> PurgeTracesRepository:
        return PurgeTracesRepository(self.connection)
