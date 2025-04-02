import sqlite3

class DBManager:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()

    def create_table(self, table_name: str, columns: list):
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            print(f"Error creating table: {e}")

    def update_info(self, info: list, table: str, columns: list):
        if len(info) != len(columns):
            raise ValueError("Length of info must match the number of columns.")
    
        # Assuming first column is a unique identifier like ID
        query_check = f"SELECT COUNT(*) FROM {table} WHERE {columns[0]} = ?"
        self.cursor.execute(query_check, (info[0],))
        exists = self.cursor.fetchone()[0]

        if exists:
            placeholders = ', '.join([f"{column} = ?" for column in columns])
            query = f"UPDATE {table} SET {placeholders} WHERE {columns[0]} = ?"
            try:
                self.cursor.execute(query, (*info, info[0]))
                self.conn.commit()
            except Exception as e:
                print(f"Error updating info: {e}")
        else:
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in info)})"
            try:
                self.cursor.execute(query, info)
                self.conn.commit()
            except Exception as e:
                print(f"Error updating info: {e}")

    def get_info(self, table: str, columns: list) -> list:
        query = f"SELECT {', '.join(columns)} FROM {table}"
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error getting infor: {e}")
            return []
        
    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            print(f"Error closing the database: {e}")
            
def local_test():
    def setup_database(db, settings):
        # Define tables and their columns
        tables = {
            "settings": ["key TEXT", "value TEXT"]
        }
        # Code to set up the database, initialize password hashes, etc.
        for table_name, columns in tables.items():
            db.create_table(table_name, columns)
        for key, value in settings.items():
            db.update_info([key, value], "settings", ["key", "value"])
        
    def fetch_data(db):
        settings = {}
        fetched_data = db.get_info("settings", ["key", "value"])
        for item in fetched_data:
            key, value = item
            settings[key] = value
        return settings

    def update_data(db, new_settings):
        for key, value in new_settings.items():
            db.update_info((key, value), "settings", ["key", "value"])
    
    try:
        db = DBManager("./test_data/test.db")
        setup_database(db, {"test": "value"})
        settings = fetch_data(db)
        print(f"{settings == {'test': 'value'}}")
        update_data(db, {"test": "value2"})
        settings = fetch_data(db)
        print(f"{settings != {'test': 'value'}}")
    except Exception as e:
        print(f"Exception occurred {e}.")
        return False
    print("Test completed successfully.")
    return True
    
if __name__ == "__main__":
    local_test()
