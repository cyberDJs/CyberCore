"""Reserved compatibility location for the CyberHIVE runtime bridge.

The active implementation lives at :mod:`cybercore.cyberhive_runtime`.

Do not move the bridge back under `cybercore.integrations` without first removing the
legacy eager imports in that package's `__init__.py`; importing this package currently
participates in the historical howedo/voice circular-import chain.
"""
