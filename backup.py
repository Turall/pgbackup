#!/usr/bin/python3

import os
import logging
import argparse
import datetime
import psycopg2
import subprocess
import configparser

BACKUP_PATH = "./"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

class PgBackup:
    
    def parse_config(self, config_path):
        config = configparser.ConfigParser()
        config.read(config_path)
        self.host = config.get("backup", "host")
        self.port = config.get("backup", "port")
        self.db = config.get("backup", "db")
        self.user = config.get("backup", "user")
        self.password = config.get("backup", "password")
        self.db_names = config.get("backup", "db").split(",")

    def generate_backup_name(self, db_name):
        timestr = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_filename = "backup-{}-{}.gz".format(timestr, db_name)
        local_file_path = "{}{}".format(BACKUP_PATH, backup_filename)
        return local_file_path

    def check_db_exist(self, db_name):
        return db_name in self.db_list

    def fetch_db_names(self, host, database_name, port, user, password):
        stmt = """SELECT datname FROM pg_database;"""

        connection = psycopg2.connect(
            database=database_name, user=user, password=password, host=host, port=port
        )
        try:
            cursor = connection.cursor()
            cursor.execute(stmt)
            db_names = cursor.fetchall()  # [tuple[str]]
            return [db[0] for db in db_names]
        except Exception as err:
            print(err)
        finally:
            cursor.close()
            connection.close()

    def backup_postgres_db(self, database_name, dest_file):
        """
        Backup postgres db to a file.
        pg_dump dbname | gzip > filename.gz
        """

        if not self.check_db_exist(database_name):
            logger.error(f"{database_name} is not exist")
            return False
        command = f'pg_dump --host={self.host} ' \
        f'--dbname={database_name} ' \
        f'--username={self.user} ' \
        f'--no-password ' \
        f'--format=c ' \
        f'| gzip > {dest_file} '
        envs = os.environ
        envs.update({'PGPASSWORD': self.password})
        proc = subprocess.Popen(command,shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE, env=envs)
        proc.wait()
        
        if int(proc.returncode) != 0:
            print("Command failed. Return code : {}".format(proc.returncode))
            return False
        return True
       

    def main(self):
        args_parser = argparse.ArgumentParser(
            description="Postgres database management"
        )
        args_parser.add_argument(
            "--action",
            metavar="action",
            choices=["backup"],
            required=True,
        )
        args_parser.add_argument(
            "--configfile", required=True, help="Database configuration file"
        )
        args = args_parser.parse_args()
        self.parse_config(args.configfile)
        self.db_list = self.fetch_db_names(
            self.host,
            self.db_names[0],
            self.port,
            self.user,
            self.password,
        )

        if args.action == "backup":
            for db_name in self.db_names:
                local_file_path  = self.generate_backup_name(db_name)
                logger.info(
                    "Backing up {} database to {}".format(db_name,local_file_path)
                )
                result = self.backup_postgres_db(
                    db_name,
                    local_file_path,
                )
                if result is not False:
                    logger.info("Backup complete")
                    logger.info("Compressing {}".format(local_file_path))


if __name__ == "__main__":
    backup = PgBackup()
    backup.main()
