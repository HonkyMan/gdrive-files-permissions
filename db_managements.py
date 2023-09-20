import yaml
import sqlite3
import json

CONFIG_PATH = 'source/config.yaml'

class Database:
    def __init__(self):
        self.conf = self._load_config()
        self.conn = self._connect_to_db(self.conf['DATABASE_NAME'])
        self.cursor = self.conn.cursor()
        self.tables = ['Users', 'Courses', 'Accesses']

    def _load_config(self):
        try:
            with open(CONFIG_PATH, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            print(f"Error loading config: {e}")
            raise

    def _connect_to_db(self, db_name):
        try:
            return sqlite3.connect(db_name)
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise

    def clear_db(self, tables = None):
        if tables is None:
            tables = self.tables

        for table in tables:
            try:
                self.cursor.execute(f"DELETE FROM {table}")
                self.conn.commit()
                print(f"Table {table} cleared sucessfully!")
            except sqlite3.Error as e:
                print(f"Error creating tables: {e}")
                raise

    def create_tables(self):
        try:
            # Создание таблицы Users
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                ID INTEGER PRIMARY KEY,
                Email TEXT,
                Name TEXT,
                Status TEXT,
                Role TEXT,
                IsDeleted INTEGER,  -- Using INTEGER for boolean
                Comment TEXT
            )
            """)

            # Создание таблицы Courses
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Courses (
                ID INTEGER PRIMARY KEY,
                Category TEXT,
                SubCategory TEXT,
                Course TEXT
            )
            """)

            # Создание таблицы Accesses
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS Accesses (
                AccessID INTEGER PRIMARY KEY,
                UserID INTEGER,
                CourseID INTEGER,
                FOREIGN KEY(UserID) REFERENCES Users(ID),
                FOREIGN KEY(CourseID) REFERENCES Courses(ID)
            )
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            raise

    def fill_tables(self, data_path=None):
        with open(data_path or self.conf['DATABASE_MOCK_DATA'], 'r') as file:
            data = json.load(file)
        
        for user in  data["users"]:
            self.add_user(email = user["email"], name = user["name"], status = user["status"], role = user["role"], is_deleted = user["is_deleted"], comment = user["comment"])
        
        for course in data["courses"]:
            self.add_course(course["category"], course["sub_category"],course["course_name"])

        for user in data["users"]:
            for course in data["courses"]:
                user_id = self.get_users(email=user['email'])[0]['ID']
                course_id = self.get_courses(category=course["category"], course=course["course_name"])[0]['id']
                self.add_access(user_id, course_id)

    def add_user(self, email=None, name=None, status=None, role=None, is_deleted=None, comment=None):
        if email is None or name is None or status is None or role is None or is_deleted is None:
            print("User have not neccessary fields")
            return
        
        try:
            if self.cursor.execute("""SELECT * From Users WHERE Email=?""", [email]).fetchone():
                print("User already added to db")
                return
            
            self.cursor.execute("""
                INSERT INTO Users (Email, Name, Status, Role, IsDeleted, Comment)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (email, name, status, role, is_deleted, comment))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding user: {e}")
            raise

    def add_course(self, category=None, sub_category=None, course_name=None):
        if category is None or sub_category is None or course_name is None:
            print("Course have not neccessary fields")
            return
        
        try:
            if self.cursor.execute("""SELECT * FROM Courses WHERE Category=? AND Course=?""", [category, course_name]).fetchone():
                print("Course already added to db")
                return
            
            self.cursor.execute("""
            INSERT INTO Courses (Category, SubCategory, Course)
            VALUES (?, ?, ?)
            """, (category, sub_category, course_name))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding course: {e}")
            raise

    def add_access(self, user_id, course_id):
        try:
            self.cursor.execute("""
                INSERT INTO Accesses (UserID, CourseID)
                VALUES (?, ?)
                """, (user_id, course_id))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding accesse: {e}")
            raise

    def set_user_status(self, user_id, status):
        try:
            self.cursor.execute("UPDATE Users SET Status = ? WHERE ID = ?", (status, user_id))
            self.conn.commit()

            # Check if any row was affected
            if self.cursor.rowcount == 0:
                print(f"No user found with ID {user_id}.")
                return
            
            return f"User with ID {user_id} status updated to Active."
        except sqlite3.Error as e:
            return f"An error occurred: {str(e)}."    

    def get_users(self, user_id=None, email=None, name=None, status=None, role=None, is_deleted=None):
        try:
            # Запрос по умолчанию
            query = "SELECT * FROM Users"
            parameters = []
            
            # Условия для запроса
            conditions = []
            
            if user_id is not None:
                conditions.append("ID=?")
                parameters.append(user_id)

            if email is not None:
                conditions.append("Email=?")
                parameters.append(email)
            
            if name is not None:
                conditions.append("Name=?")
                parameters.append(name)
                
            if status is not None:
                conditions.append("Status=?")
                parameters.append(status)
                
            if role is not None:
                conditions.append("Role=?")
                parameters.append(role)
                
            if is_deleted is not None:
                conditions.append("IsDeleted=?")
                parameters.append(is_deleted)
                
            # Добавляем условия в запрос
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            users = self.cursor.execute(query, parameters).fetchall()
            users = [
                {
                    "ID": user[0] or None,
                    "Email": user[1] or None,
                    "Name": user[2] or None,
                    "Status": user[3] or None,
                    "Role": user[4] or None,
                    "IsDeleted": user[5] or None,
                    "Comment": user[6] or None
                } for user in users
            ]
            return users

        except sqlite3.Error as e:
            print(f"Getting users raised error: {str(e)}")

    def get_courses(self, course_id=None, category=None, sub_category=None, course=None):
        try:
            # Запрос по умолчанию
            query = "SELECT * FROM Courses"
            parameters = []
            
            # Условия для запроса
            conditions = []
            
            if course_id is not None:
                conditions.append("ID=?")
                parameters.append(course_id)
            
            if category is not None:
                conditions.append("Category=?")
                parameters.append(category)
                
            if sub_category is not None:
                conditions.append("SubCategory=?")
                parameters.append(sub_category)
                
            if course is not None:
                conditions.append("Course=?")
                parameters.append(course)
                
            # Добавляем условия в запрос
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            courses = self.cursor.execute(query, parameters).fetchall()
            courses = [
                {
                    "id": course[0] or None,
                    "category": course[1] or None,
                    "sub_category": course[2] or None,
                    "course": course[3] or None
                } for course in courses
            ]

            return courses

        except sqlite3.Error as e:
            print(f"Getting courses raised an error: {str(e)}")

    def get_access_by_user_id(self, user_id):
        try:
            map = self.cursor.execute('select * from Accesses where UserID = ?', (user_id,)).fetchall()

            # Создаем словарь, используя генератор списков
            user_courses = {}
            [
                user_courses.setdefault(
                    user_id, 
                    {
                        "user_id": user_id, 
                        "courses": []
                    }
                )["courses"].append(course_id) for access_id, user_id, course_id in map
            ]

            return list(user_courses.values())[0]

        except sqlite3.Error as e:
            print(f"Getting course by id raised error: {str(e)}")

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == "__main__":
    with Database() as db:
        db.create_tables()
        db.fill_tables()
        #db.clear_db()
