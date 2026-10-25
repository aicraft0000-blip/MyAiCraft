class CostWindowProcessDisabledError(Exception):
    """
    Raised when an ingest call returns status='blocked'.

    Kill-switch / budget blocks: catch this to skip further API calls.
    free_plan_limit: the free tier caps new processes at 2 — upgrade to continue.
    """
    def __init__(self, label: str, reason: str | None = None):
        self.label = label
        self.reason = reason
        if reason == "free_plan_limit":
            msg = (
                f"Cannot create process '{label}': free plan is limited to 2 processes. "
                "Upgrade at costwindow.com for unlimited processes."
            )
        else:
            msg = (
                f"Process '{label}' is disabled. "
                "Re-enable it in the CostWindow dashboard."
            )
        super().__init__(msg)
