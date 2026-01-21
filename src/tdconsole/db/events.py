from sqlalchemy import event, inspect, update
from sqlalchemy.orm import object_session

from tdconsole.db.models import Instance


@event.listens_for(Instance, "after_update")
def manage_working_instance(mapper, connection, target):
    state = inspect(target)
    working_history = state.attrs.working.history
    print(working_history)

    if working_history.has_changes():
        print("new working changes")
        old = working_history.deleted[0] if working_history.deleted else None
        new = working_history.added[0] if working_history.added else None
        print("----")
        print(target)
        print(old)
        print(new)

        if old is False and new is True:
            session = object_session(target)
            app = session.info.get("app")
            stmt = (
                update(Instance)
                .where(Instance.name != target.name)
                .where(Instance.working.is_(True))
                .values(working=False)
            )
            connection.execute(stmt)
            if app:
                app.working_instance = target
            return

    if target.working is True:
        changed = [
            attr.key
            for attr in state.attrs
            if attr.key != "working" and attr.history.has_changes()
        ]
        if not changed:
            return
        session = object_session(target)
        app = session.info.get("app")
        if app:
            app.working_instance = target
            return
