from __future__ import annotations

from typing import TYPE_CHECKING

from angrmanagement.plugins import BasePlugin

from .swab_view import SWABView

if TYPE_CHECKING:
    from angrmanagement.ui.workspace import Workspace


class SWABPlugin(BasePlugin):
    """
    SWAB Plugin - provides a split-panel view with non-editable text and editable code.
    """

    DISPLAY_NAME = "SWAB"

    def __init__(self, workspace: Workspace) -> None:
        super().__init__(workspace)

        # Create and add the SWAB view to the workspace
        if workspace is not None:
            self._create_swab_view()

    def _create_swab_view(self) -> None:
        """Create and register the SWAB view."""
        swab_view = SWABView(
            self.workspace,
            "center",
            self.workspace.main_instance,
        )
        self.workspace.add_view(swab_view)
        self.workspace.raise_view(swab_view)

    def teardown(self) -> None:
        """Clean up the plugin."""
        super().teardown()
