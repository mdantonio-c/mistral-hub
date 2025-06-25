import logging
import sys
from datetime import datetime, timedelta

import dballe
from restapi.config import get_backend_url
from restapi.connectors import smtp, sqlalchemy
from restapi.env import Env


def setup_logging():
    logging.basicConfig(
        filename="/logs/dballe_aggr_cleanup.log",
        level=logging.INFO,
        format="%(asctime)s --- %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    setup_logging()

    aggregations_dsn = Env.get("AGGREGATIONS_DSN", "")
    aggregations_lastdays = Env.get_int("AGGREGATIONS_LASTDAYS", 3)

    db = sqlalchemy.get_instance()
    engine = db.variables.get("dbtype")
    user = db.variables.get("user")
    pw = db.variables.get("password")
    host = db.variables.get("host")
    port = db.variables.get("port")

    # Set time boundaries
    date = datetime.today() - timedelta(days=aggregations_lastdays)
    date_string = date.strftime("%Y-%m-%d")
    query = {"yearmax": date.year, "monthmax": date.month, "daymax": date.day}

    db = dballe.DB.connect(f"{engine}://{user}:{pw}@{host}:{port}/{aggregations_dsn}")

    logging.info("######################################################")
    logging.info(f"Starting dballe database '{aggregations_dsn}' cleanup.")
    logging.info(f"Removing data from {date_string} (and before)...")
    try:
        with db.transaction() as tr:
            tr.remove_data(query)
            tr.commit()
            logging.info(f"Data has been removed from database '{aggregations_dsn}'.")
    except Exception as exc:
        # sent alert by mail
        smtp_client = smtp.get_instance()
        host = get_backend_url()
        smtp_client.send(
            f"Dballe database '{aggregations_dsn}' cleanup. "
            f"Removing data from {date_string} (and before) raised the following exception: {exc}",
            f"Alert from {host} : removing data ended in an error",
            to_address="mistral-support@cineca.it",
        )
        logging.info(f"Error in dballe database '{aggregations_dsn}' cleanup.")
        logging.info("Data was not removed from the database.")

    logging.info("######################################################")


if __name__ == "__main__":
    # (this code was run as script)
    sys.exit(main())
