from sqlalchemy import select


async def get_or_create(
        session,
        model,
        **kwargs,
):
    """
    Searches the database for a model record by kwargs.
    If not found, creates a new one and returns it.
    """
    q = await session.execute(select(model).filter_by(**kwargs))
    inst = q.scalar_one_or_none()
    if inst:
        return inst
    inst = model(**kwargs)
    session.add(inst)
    await session.flush()
    return inst