
class SQLEngine:
    def __init__(self):
        ...

    def __repr__(self):
        return self.__class__.__name__


class MySQL(SQLEngine):

    def __init__(self):
        super(SQLEngine).__init__()

        self.base_from_clause = "FROM {table_name} {where} ORDER BY {order_by} limit 1 offset {row_num}"
        self.string_definition = "SELECT {}"
        self.string_len_definition = "SELECT length({})"
        self.string_char_definition = "SELECT ASCII(SUBSTRING({},{},1))"
        self.count_definition = "SELECT count(*) FROM (SELECT * FROM {} {})T"
        self.offset_shift = 0
        self.schemata_disclaimer = "In MySQL schema is synonym of database."
        self.schemata_query = ["schema_name",
                               "information_schema.schemata", None]
        self.tables_query = [
            "table_name", "information_schema.tables", "table_schema <> 'information_schema'"]
        self.tables_schema_query = [
            "table_name", "information_schema.tables", "table_schema='{schema_name}'"]
        self.columns_query = [
            "column_name", "information_schema.columns", "table_name = '{table_name}'"]


class MSSQL(SQLEngine):

    def __init__(self):
        super(SQLEngine).__init__()

        # Old version, could be very slow. Should be commented?
        self.base_from_clause = "FROM (SELECT *, ROW_NUMBER() OVER(ORDER by [{order_by}])n FROM {table_name} {where})T WHERE n={row_num}"
        self.offset_shift = 1
        # modern version FETCH - OFFSET
        self.base_from_clause = "FROM {table_name} {where} ORDER BY {order_by} OFFSET {row_num} ROWS FETCH NEXT 1 ROWS ONLY"
        self.offset_shift = 0
        self.string_def = "SELECT {}"
        self.string_len_def = "SELECT len({})"
        self.string_char_definition = "SELECT ASCII(SUBSTRING({},{},1))"
        self.count_definition = "SELECT count(*) FROM (SELECT * FROM {} {})T"
        self.schemata_query = ["schema_name",
                               "INFORMATION_SCHEMA.SCHEMATA", None]
        self.tables_query = ["name", "sysobjects", "xtype in ('V','U')"]
        self.tables_schema_query = [
            "table_name", "information_schema.tables", "table_schema='{schema_name}'"]
        self.columns_query = [
            "name", "syscolumns", "id=(select id from sysobjects where name='{table_name}')"]
        # tips:
        # cast to varchar(500), not to text.


class SQLite(SQLEngine):

    def __init__(self):
        super(SQLEngine).__init__()

        self.base_from_clause = "FROM {table_name} {where} ORDER BY {order_by} limit 1 offset {row_num}"
        self.string_definition = "SELECT {}"
        self.string_len_definition = "SELECT length({})"
        self.string_char_definition = "SELECT hex(SUBSTR({},{},1))"
        self.count_definition = "SELECT count(*) FROM (SELECT * FROM {} {})T"
        self.offset_shift = 0
        self.tables_query = ["sql", "sqlite_master", None]


class Oracle(SQLEngine):

    def __init__(self):
        super(SQLEngine).__init__()

        self.base_from_clause = "FROM (SELECT a.*, ROWNUM rn FROM {table_name} a {where} ORDER BY a.{order_by}) WHERE rn={row_num}"
        #self.base_from_clause = "FROM (SELECT *, ROWNUM rn FROM {table_name} {where} ORDER BY {order_by}) WHERE rn={row_num}"
        self.string_definition = "SELECT {}"
        self.string_len_definition = "SELECT LENGTH({})"
        self.string_char_definition = "SELECT ASCII(SUBSTR({},{},1))"
        self.count_definition = "SELECT count(*) FROM (SELECT * FROM {} {})T"
        self.offset_shift = 1
        self.schemata_query = [
            "owner", "(select distinct(owner) from all_tables)", None]
        self.schemata_disclaimer = "Schema in oracle is the same as an user. This query returns users."
        self.tables_query = ["TABLE_NAME", "USER_TABLES", None]
        self.tables_schema_query = [
            "TABLE_NAME", "ALL_TABLES", "owner=UPPER('{schema_name}')"]
        self.columns_query = [
            "column_name", "all_tab_columns", "table_name = UPPER('{table_name}')"]


class Postgre(SQLEngine):

    def __init__(self):
        super(SQLEngine).__init__()

        self.base_from_clause = "FROM {table_name} {where} ORDER BY {order_by} limit 1 offset {row_num}"
        self.string_definition = "SELECT {}"
        self.string_len_definition = "SELECT LENGTH({})"
        self.string_char_definition = "SELECT ASCII(SUBSTRING({},{},1))"
        self.count_definition = "SELECT count(*) FROM (SELECT * FROM {} {})T"
        self.offset_shift = 0
        self.schemata_disclaimer = "In PostgreSQL another databases exists but are not accessible. So only schemata here."
        self.schemata_query = ["nspname", "pg_catalog.pg_namespace", None]
        self.tables_query = ["c.relname", "pg_catalog.pg_class c LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace", "c.relkind IN ('r','') AND n.nspname NOT IN ('pg_catalog', 'pg_toast') AND pg_catalog.pg_table_is_visible(c.oid)"]
        # remove v and m if you don"t want see views
        self.tables_schema_query = ["c.relname", "pg_catalog.pg_class c LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace", "c.relkind IN ('r','m','v','') AND n.nspname='{schema_name}'"]
        self.columns_query = ["attname", "pg_attribute",
                              "attrelid=(SELECT oid FROM pg_class WHERE relname='{table_name}') AND attnum>0"]


engines = {v.__name__.lower(): v() for v in SQLEngine.__subclasses__()}
