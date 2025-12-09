from tdconsole.core.models import ApiResponse


def sync_api_rules(app) -> list[ApiResponse]:
    """
    Sync filesystem state into the DB using ORM models created by instance_name_to_instance.
    Returns the ORM models from the DB after upsert.
    """
    [{"label", "screen", "name", "priority"}]

    with app as session:
        for name in instance_names:
            # Instance from filesystem only
            fs_instance = instance_name_to_instance(name)

            # Try to find existing record in DB
            db_instance = session.query(Instance).filter_by(name=name).first()

            if db_instance is None:
                # Create if not found
                session.add(fs_instance)
            else:
                # Update existing with latest filesystem values
                db_instance.pid = fs_instance.pid
                db_instance.status = fs_instance.status
                db_instance.cfg_ext = fs_instance.cfg_ext
                db_instance.cfg_int = fs_instance.cfg_int
                db_instance.arg_ext = fs_instance.arg_ext
                db_instance.arg_int = fs_instance.arg_int

        session.query(Instance).filter(~Instance.name.in_(instance_names)).delete(
            synchronize_session=False
        )

        session.commit()

        # Return database versions of instances
        instances_in_db = session.query(Instance).order_by(Instance.name).all()

    return instances_in_db
