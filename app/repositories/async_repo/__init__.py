"""Async repository layer for use with FastAPI AsyncSession.

Routers should depend on this layer instead of CRUD classes. This keeps
access to the database uniform and easy to extend with cross-cutting
concerns (e.g., auditing, metrics, retries).
"""


