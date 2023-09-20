from google.oauth2 import service_account
from googleapiclient.discovery import build
import yaml
from db_managements import Database
from typing import Any, Dict, Optional, Union, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='app.log')
CONFIG_PATH = 'source/config.yaml'

class GoogleDrive:
    def __init__(self) -> None:
        self.conf = self._load_config()
        self.secondary_mime_types = f"({self.conf['GDRIVE_MIME_TYPES']['docs']} or {self.conf['GDRIVE_MIME_TYPES']['sheet']} or {self.conf['GDRIVE_MIME_TYPES']['image']} or {self.conf['GDRIVE_MIME_TYPES']['other']} or {self.conf['GDRIVE_MIME_TYPES']['unknown']})"
        self.drive_service = self._init_drive_service()
        self.new_users = self._get_users(status='New')
        self.fired_users = self._get_users(status='Fired')
        self.courses = self._get_courses()
        logging.info('All internal vars was setted')

    def _load_config(self) -> Optional[Dict[str, Union[str, List[str], int]]]:
        try:
            with open(CONFIG_PATH, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return None

    def _init_drive_service(self) -> Any:
        try:
            creds = service_account.Credentials.from_service_account_file(self.conf['GDRIVE_API_KEYS'], scopes=self.conf['SCOPES'])
            return build(self.conf['GDRIVE_SERVICE_NAME'], self.conf['GDRIVE_VERSION'], credentials=creds)
        except Exception as e:
            logging.error(f'Error on loading drive service: {e}')
    
    def _get_users(self, user_id=None, email=None, name=None, status=None, role=None, is_deleted=None) -> list:
        with Database() as db:
            return db.get_users(user_id, email, name, status, role, is_deleted)

    def _get_courses(self, course_id=None, category=None, sub_category=None, course=None) -> dict:
        with Database() as db:
            db_courses = db.get_courses(course_id, category, sub_category, course)
        
        courses = dict()

        for db_course in db_courses:
            courses[db_course['id']] = self._get_gdrive_course_files(db_course)

        return courses

    def _get_gdrive_course_files(self, course) -> dict:
        """
        Функция возвращает словарь с 2-мя ключами: 
            - presentation_files: список файлов с типом "Презентация"
            - secondary_files: список файлов со всеми иными типами

        Args:
            List[dict]: course

        Returns:
            Dict
        """
        path_parts = self._get_path_parts(course)

        # Начнем с поиска папки "Courses"
        response = self.drive_service.files().list(
            q=f"name='Courses' and {self.conf['GDRIVE_MIME_TYPES']['folder']}",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        if not response.get('files'):
            raise Exception(f"Directory 'Courses' not found!")
        
        current_folder_id = response.get('files')[0]['id']

        for part in path_parts:
            response = self.drive_service.files().list(
                q=f"'{current_folder_id}' in parents and name='{part}' and {self.conf['GDRIVE_MIME_TYPES']['folder']}",
                spaces='drive',
                fields='files(id, name, description)'
            ).execute()
            
            if not response.get('files'):
                raise Exception(f"Directory {part} not found!")
            
            # Если в описании папки указано Empty, то пропускаем данный курс
            if response.get('files')[0].get('description') == 'Empty':
                return

            current_folder_id = response.get('files')[0]['id']

        response_main = self.drive_service.files().list(
            q=f"'{current_folder_id}' in parents and {self.conf['GDRIVE_MIME_TYPES']['presentation']}",
            spaces='drive',
            fields='files(id, name, mimeType)'
        ).execute()

        response_secondary = self.drive_service.files().list(
            q=f"'{current_folder_id}' in parents and {self.secondary_mime_types}",
            spaces='drive',
            fields='files(id, name, mimeType)'
        ).execute()

        return {
            'presentation_files': response_main.get('files', []),
            'secondary_files': response_secondary.get('files', [])
        }
    
    def _provide_access(self, user, files, role):
        try:
            for file in files:
                permissions = {
                    'type': 'user',
                    'role': role,
                    'emailAddress': user['Email']
                }
                self.drive_service.permissions().create(fileId=file['id'], body=permissions, fields='id', sendNotificationEmail=False).execute()
        except Exception as e:
            logging.error(f'Error providing access: {e}')

    def _revoke_access(self, user, files):
        try:
            for file in files:
                permissions_list = self.drive_service.permissions().list(fileId=file['id'], fields="permissions(id,type,kind,role,emailAddress)").execute().get('permissions', [])
                for permission in permissions_list:
                    if permission.get('emailAddress').lower() == user['Email']:
                        self.drive_service.permissions().delete(fileId=file['id'], permissionId=permission['id']).execute()
                        print(f"Access revoked for {user['Email']} on file {file['name']}")
        except Exception as e:
            logging.error(f'Error revoking access: {e}')

    def _set_gdrive_course_files_permissions(self, user, files, role=None, action='provide'):
        if action == 'provide':
            self._provide_access(user, files, role)
        elif action == 'revoke':
            self._revoke_access(user, files)
        else:
            logging.error(f'Current action "{action}" not determined')
    
    def _revoke_gdrive_course_files_permissions(self, user, files) -> Optional[bool]:
        try:
            for file in files:
                permissions = self.drive_service.permissions().list(fileId=file['id']).execute()

                for permission in permissions:
                    if permission.get('permissions') == user['Email']:
                        self.drive_service.permissions().delete(fileId=file['id'], permissionId=permission['id']).execute()
                        print(f"Access revoked for {user['Email']} on file {file['name']}")
            
            return True

        except Exception as e:
            logging.error(f'Error revoking access: {e}')
            return None

    def set_file_copy_permissions(self) -> None:
        """
        Set copy permissions on all files in GDrive for read role users.
        That func work only with Owner permissions in service account

        Args:
            -

        Returns:
            None
        """
        try:
            for course in self.courses:
                files = self._get_gdrive_course_files(course)
                if not files:
                    logging.info(f'In {course} not found files')
                    continue
                if files:
                    for file in files:
                        self.drive_service.files().update(
                            fileId=file['id'],
                            body=self.conf['GDRIVE_COPY_PERMISSIONS'],
                            fields='id,copyRequiresWriterPermission'
                        ).execute()

            logging.info(f'For all files in gdrive setted copy permissions: {self.conf["GDRIVE_COPY_PERMISSIONS"]}')

        except Exception as e:
            logging.error(f'Error revoking copy permissions: {e}')
            return None

    def _get_path_parts(self, course) -> List[str]:
        path_parts = [course["category"]]
        if course["sub_category"]:
            path_parts.append(course["sub_category"])
        path_parts.append(course["course"])
        return path_parts

    def manage_accesses(self, users, action=None) -> None:
        if action not in ['provide', 'revoke']:
            logging.error(f'Invalid action "{action}" passed')
            return

        with Database() as db:
            for user in users:
                courses_id = db.get_access_by_user_id(user['ID']).get('courses', [])
                courses = [self.courses[course_id] for course_id in courses_id]

                for course in courses:
                    if course is None:
                        continue
                    
                    if course['presentation_files']:
                        self._set_gdrive_course_files_permissions(user, course['presentation_files'], action=action)
                    if course['secondary_files']:
                        self._set_gdrive_course_files_permissions(user, course['secondary_files'], role='writer', action=action)
                
                # Update user status
                if action == 'provide':
                    db.set_user_status(user['ID'], 'Active')
                    logging.debug(f'Changed status for user {user} to Active')
                elif action == 'revoke':
                    db.set_user_status(user['ID'], 'Deactivated')  # Corrected "Diactivated" to "Deactivated"
                    logging.debug(f'Changed status for user {user} to Deactivated')

if __name__ == "__main__":
    gd = GoogleDrive()
    gd.set_file_copy_permissions()

    # Handle new users
    if gd.new_users:
        logging.info("Providing access to new users...")
        gd.manage_accesses(gd.new_users, action='provide')

    # Handle fired users
    if gd.fired_users:
        logging.info("Revoking access from fired users...")
        gd.manage_accesses(gd.fired_users, action='revoke')


# TODO:
# Вытащить уроки из под папок. 