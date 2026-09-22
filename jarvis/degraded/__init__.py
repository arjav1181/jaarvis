"""W20 degraded mode — honest offline operation. Stdlib only.

When the model relay is unreachable this package is the whole Jarvis that
remains: fast relay-down detection, a banner that says so, a local-only
capability set, and a queue whose contents replay on recovery.

Never faked intelligence: anything needing a model while degraded is
refused with a reason, never hallucinated.
"""
