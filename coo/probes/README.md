# coo/probes/ — re-runnable value probes

One file per completed tangent, emitted by the Validator. Each probe contains
cheap read-only checks that re-verify the tangent's value still holds.

Purpose: completed does not mean still-true. A weekly heartbeat can re-run recent
probes; a FAIL means something regressed and the tangent re-opens.

Format: markdown with a `checks:` list of (command, expect) pairs. A mechanical
runner can execute these later; today they are validator/operator-readable.
