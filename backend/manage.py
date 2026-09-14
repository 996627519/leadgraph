"""数据库管理入口：python -m backend.manage init-db / create-user。"""
import argparse
from getpass import getpass
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from backend.persistend.database import Database
from backend.service.auth_service import AuthService


def main():
    parser = argparse.ArgumentParser(description='LeadGraph 账户数据库初始化')
    parser.add_argument('command', choices=['init-db', 'create-user', 'check-db'])
    parser.add_argument('--username', help='创建的用户名；密码在本机交互输入')
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parent / 'config/.env')
    database = None
    try:
        database = Database()
        if args.command == 'init-db':
            database.initialize()
            print('MySQL 业务表已就绪。不会删除现有数据。')
        elif args.command == 'check-db':
            database.check()
            print('MySQL 连接与用户表检查通过。')
        else:
            username = args.username or input('用户名：')
            password = getpass('密码（10–128 位，不回显）：')
            if password != getpass('再次输入密码：'):
                raise ValueError('两次输入的密码不一致。')
            AuthService(database).register(username, password)
            print('账户已创建，可以在页面登录。')
    except SQLAlchemyError:
        parser.exit(1, 'MySQL 操作失败。请检查实例、数据库、权限与本机 .env 配置；初始化步骤见 docs/ACCOUNT_SETUP.md。\n')
    except (ValueError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
    finally:
        if database is not None:
            database.close()


if __name__ == '__main__':
    main()
