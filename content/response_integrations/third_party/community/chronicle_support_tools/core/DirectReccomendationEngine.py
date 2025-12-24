from __future__ import annotations

# DREC

maxReccomendationsToGivePerSnippet = 2


# This is called in CSAL when reading through the detected errors in various logs in the agent machine.


class DirectReccomendationEngine:
    _integration_name = None
    _siemplify = None

    def __init__(self, integration_name, siemplify):
        self._integration_name = integration_name
        self._siemplify = siemplify

    def get_reccomendations(self, logSnippet):
        try:
            pass

        except Exception as e:
            self._siemplify.LOGGER.info(str(e))
            return "Unable to Fetch Reccomendations"

    def log_collected_info(self, logSnippet):
        self._siemplify.LOGGER.info(
            "============= Direct Reccomendations (DREC) =============",
        )

        self.get_reccomendations(logSnippet)

        self._siemplify.LOGGER.info(
            "============= Finished Direct Reccomendations (DREC) =============",
        )
