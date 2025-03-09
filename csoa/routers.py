# routers.py

class XYZRouter:
    """
    Routes all operations on XYZ app models to the 'xyz_db'.
    """
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'xyz':
            return 'xyz_db'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'xyz':
            return 'xyz_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Only allow relations if both models are in the same database
        if obj1._meta.app_label == 'xyz' and obj2._meta.app_label == 'xyz':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure the XYZ app only migrates to 'xyz_db'.
        """
        if app_label == 'xyz':
            return db == 'xyz_db'
        # Other apps don't migrate to xyz_db
        return db == 'default'