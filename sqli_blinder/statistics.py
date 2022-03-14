
class Statistics():
	def __init__(self):
		self._stats = {}

	def log(self,table_name,column_name,value):
		if table_name not in self._stats:
			self._stats[table_name]={}
		if column_name not in self._stats[table_name]:
			self._stats[table_name][column_name] = {"values":[],"chars":{}}
		self._stats[table_name][column_name]['values'].append(value)
		for c in value:
			if c in self._stats[table_name][column_name]['chars']:
				self._stats[table_name][column_name]['chars'][c] += 1
			else:
				self._stats[table_name][column_name]['chars'][c] = 1

	def get_all(self):
		return self._stats

	def get_values(self,table_name,column_name):
		if table_name not in self._stats:
			return None
		if column_name not in self._stats[table_name]:
			return None
		return self._stats[table_name][column_name]['values']

	def get_chars(self,table_name,column_name):
		return self._stats[table_name][column_name]['chars']

	def get_tables(self):
		return self._stats.keys()

	def get_char_in_position(self,table_name,column_name,position):
		result = []
		values = self.get_values(table_name,column_name)
		if values is None:
			return []
		for val in values:
			if len(val)>position:
				result.append(val[position])
			else:
				result.append(None)
		return result
