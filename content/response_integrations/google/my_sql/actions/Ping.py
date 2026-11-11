from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from my_sql.core.MySQLManager import MySQLManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("MySQL")
    server_addr = conf["Server Address"]
    username = conf["Username"]
    password = conf["Password"]
    port = int(conf.get("Port"))
    database = conf.get("Database Name For Testing")

    mysql_manager = MySQLManager(
        username=username,
        password=password,
        server=server_addr,
        database=database,
        port=port,
    )

    mysql_manager.close()

    # If no exception occur - then connection is successful
    output_message = f"Successfully connected to {database} at {server_addr}:{port}."
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
