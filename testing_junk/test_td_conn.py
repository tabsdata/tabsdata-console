from tabsdata.api.tabsdata_server import TabsdataServer

server = TabsdataServer("127.0.0.1:2457", "admin", "tabsdata", "sys_admin")
print(server.auth_info())
