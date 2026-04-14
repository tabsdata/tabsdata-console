from contextlib import nullcontext
import json
import os
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from tabsdata.api.apiserver import APIServer
from tabsdata.api.tabsdata_server import TabsdataServer

from tdconsole.core.models import Collection, Function, Instance, Table
from tdconsole.core.subprocess_runner import run_bash


def _socket_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 2457
    if not host:
        return None
    return f"{host}:{port}"


def _load_connection_credentials() -> dict | None:
    path = os.path.expanduser("~/.tabsdata/connection.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as handle:
            payload = json.load(handle)
    except Exception:
        return None
    if not payload.get("url"):
        return None
    if not payload.get("bearer_token"):
        return None
    return payload


def _build_server_from_credentials(credentials: dict) -> TabsdataServer:
    connection = APIServer(credentials.get("url"))
    connection.refresh_token = credentials.get("refresh_token")
    connection.bearer_token = credentials.get("bearer_token")
    connection.token_type = credentials.get("token_type")
    connection.expires_in = credentials.get("expires_in")
    connection.expiration_time = credentials.get("expiration_time")
    server = TabsdataServer.__new__(TabsdataServer)
    server.connection = connection
    return server


def initialize_tabsdata_server_connection(app):
    """
    Build a TabsdataServer client and attempt login.

    Returns:
        dict with keys:
            - server: TabsdataServer | None
            - login_success: bool | None
              (None when no server/instance is available)
    """
    instance = app.working_instance
    login_success = None
    if instance is None:
        server = None
        return {"server": server, "login_success": login_success}

    socket = instance.ext_socket
    server = None

    # Prefer existing token-based session from ~/.tabsdata/connection.json.
    credentials = _load_connection_credentials()
    credentials_socket = _socket_from_url(credentials.get("url")) if credentials else None
    if credentials and credentials_socket == socket:
        try:
            server = _build_server_from_credentials(credentials)
            server.auth_info()
            login_success = True
            return {"server": server, "login_success": login_success}
        except Exception:
            server = None

    # Fallback for environments that still rely on username/password login.
    if server:
        return {"server": server, "login_success": login_success}

    username = "admin"
    password = "tabsdata"
    role = "sys_admin"
    try:
        server = TabsdataServer(socket, username, password, role)
        run_bash(
            f"td login --server {socket} --user {username} --role {role} --password {password}"
        )
        login_success = True
    except Exception:
        login_success = False
        if server is None:
            try:
                server = TabsdataServer(socket)
            except Exception:
                server = None

    return {"server": server, "login_success": login_success}


def pull_all_collections(app):
    try:
        server = app.tabsdata_server
        server: TabsdataServer
        collections = server.list_collections()
        return collections
    except:
        return []


def pull_functions_from_collection(app, collection):
    try:
        server = app.tabsdata_server
        server: TabsdataServer
        functions = server.list_functions(collection)
        return functions
    except:
        return []


def pull_tables_from_collection(app, collection):
    try:
        server = app.tabsdata_server
        server: TabsdataServer
        tables = server.list_tables(collection)
        return tables
    except:
        return []


def check_server_status(app, server: TabsdataServer = None):
    if not server:
        server = app.tabsdata_server

    if not server:
        return False

    try:
        auth_status = server.auth_info()
        return True
    except:
        return False


def sync_instance_to_db(app):
    session = app.session
    session: Session
    server = app.tabsdata_server
    instance = app.working_instance
    server: TabsdataServer
    server_status = check_server_status(app, server)

    if not server_status:
        return None

    collections = pull_all_collections(app)

    if len(collections) == 0:
        return None

    data = {
        i.name: {
            "tables": pull_tables_from_collection(app, i.name),
            "functions": pull_functions_from_collection(app, i.name),
        }
        for i in collections
    }

    instance = session.query(Instance).filter_by(name=instance.name).one()
    tx = nullcontext()
    if not session.in_transaction():
        tx = session.begin()
    with tx:
        instance.collections.clear()
        for name, v in data.items():
            c = Collection(name=name, instance=instance)
            c.tables = [
                Table(name=getattr(t, "name"), instance_name=instance.name)
                for t in v["tables"]
            ]
            c.functions = [
                Function(name=getattr(f, "name"), instance_name=instance.name)
                for f in v["functions"]
            ]
            session.add(c)
