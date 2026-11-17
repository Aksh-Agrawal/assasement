"""Compute a profile's progress screen away from the Qt event loop."""

import logging

from PySide6.QtCore import QObject, QRunnable, Signal

from app.data.intelligence import load_intelligence

LOGGER = logging.getLogger(__name__)


class AnalyticsSignals(QObject):
    finished = Signal(int, dict)


class AnalyticsJob(QRunnable):
    def __init__(self, generation, database, profile_id, window, marking=None, budget_ms=None):
        super().__init__()
        self.generation = generation
        self.arguments = (database, profile_id, window, marking, budget_ms)
        self.signals = AnalyticsSignals()

    def run(self):
        try:
            result = load_intelligence(*self.arguments)
        except Exception:
            LOGGER.exception("Could not load local intelligence")
            result = {"failed": True}
        self.signals.finished.emit(self.generation, result)
