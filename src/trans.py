#!/usr/bin/python
#
# =============================================================================
#

from pyproj import Proj, transform
from urllib2 import urlopen, Request
import re as regex


def transform_lines(x_line, y_line, crs_to, crs_from):
	'''
	'''
	x_list = list()
	y_list = list()
	x_pts = x_line.split(',')
	y_pts = y_line.split(',')
	pto = Proj(init=crs_to)
	pfrom = Proj(init=crs_from)
	for i in range(0,len(x_pts)-1):
		x_pts[i] = float(x_pts[i].strip())
	for j in range(0,len(y_pts)-1):
		y_pts[j] = float(y_pts[j].strip())
	for d in range(0,len(x_pts)):
		x,y = transform(pfrom,pto,x_pts[d],y_pts[d])
		x_list.append(x)
		y_list.append(y)
	retval = dict()
	retval['x'] = x_list
	retval['y'] = y_list
	return retval

def read_config():
	prop_dict = dict()
	fileH = open('config.conf', 'r')
	conf_file = fileH.read()
	plines = conf_file.splitlines()

	for prop in plines:
		if prop.count('=') == 1 and not prop.startswith('#'):
			kv = prop.partition('=')
			prop_dict[kv[0]] = kv[2]

	if prop_dict.get('url') is None or prop_dict.get('x_var') is None or prop_dict.get('y_var') is None or prop_dict.get('source_crs') is None:
		print 'ERROR: missing required property value in config file'
		exit(1)

	if prop_dict.get('final_crs') is None:
		prop_dict['final_crs'] = 'epsg:4326'

	if prop_dict.get('chunk') is None:
		prop_dict['chunk'] = 1000

	return prop_dict

def get_variable_dimensions(x_name, y_name, url):
	retval = dict()
	request = Request(url)
	response = urlopen(request).read()
	dataset_ndx = response.find('Dataset {')
	# 'x' dimension
	xvar_ndx = response.find(x_name, dataset_ndx)
	nline_ndx = response.find('\n', xvar_ndx)
	xvar_line = response[xvar_ndx:nline_ndx]
	xvar_split = xvar_line.split('=')
	xmatch = regex.search('\d+', xvar_split[1])
	retval['x_dim'] = int(xmatch.string[xmatch.start():xmatch.end()])
	# 'y' dimension
	yvar_ndx = response.find(y_name, dataset_ndx)
	nline_ndx = response.find('\n', yvar_ndx)
	yvar_line = response[yvar_ndx:nline_ndx]
	yvar_split = yvar_line.split('=')
	ymatch = regex.search('\d+', yvar_split[1])
	retval['y_dim'] = int(ymatch.string[ymatch.start():ymatch.end()])

	if not retval['y_dim'] == retval['x_dim']:
		print 'ERROR: x and y have different dimensions!'
		exit(1)

	return retval

def read_dap_variable_data(url, var_name, start, chunk, stop):
	query = '?' + var_name + '[' + str(start) + ':' + str(chunk) + ':' + str(stop) + ']'
	rdvd_req = Request(url + query)
	rdvd_res = urlopen(rdvd_req).read()
	retval = ''
	for line in rdvd_res.split('\n'):
		if regex.match('\d+', line) is not None:
			retval = line
	return retval

def init_file():
	global file_name
	out = open(file_name, 'w')
	out.close()

def write_out_dict(final_dict, xvar, yvar):
	global file_name
	out = open(file_name, 'a')
	out.write(xvar + '[' + str(len(final_dict[xvar])) + ']: ')
	for x in final_dict[xvar]:
		out.write(str(x) + ', ')
	out.flush()
	out.write('\n')
	out.write(yvar + '[' + str(len(final_dict[yvar])) + ']: ')
	for y in final_dict[yvar]:
		out.write(str(y) + ', ')
	out.flush()
	out.close()

def __main__(*args, **xargs):
	global file_name
	properties = read_config()
	xname = properties.get('x_var')
	yname = properties.get('y_var')
	base_url = properties.get('url')

	file_name += xname + '-' + yname +'_transform.out'

	html_url = base_url
	if not base_url.endswith('.html'):
		html_url += '.html'
	print html_url

	dims = get_variable_dimensions(xname, yname, html_url)
	init_file()

	aurl = base_url
	if base_url.endswith('.html'):
		aurl = aurl.replace('.html', '.ascii')
	else:
		aurl += '.ascii'

	print aurl

	ndx_max = dims['x_dim']
	ndx_curr = 0
	chunk = int(properties.get('chunk'))
	out_dict = dict()
	out_dict[xname] = list()
	out_dict[yname] = list()
	while ndx_curr < ndx_max:
		ndx_stop = ndx_curr + chunk - 1
		if ndx_stop >= ndx_max:
			ndx_stop = ndx_max - 1

		xdata = read_dap_variable_data(aurl, xname, ndx_curr, 1, ndx_stop)
		ydata = read_dap_variable_data(aurl, yname, ndx_curr, 1, ndx_stop)

		tres = transform_lines(xdata, ydata, properties.get('final_crs'), properties.get('source_crs'))

		out_dict[xname] += tres['x']
		out_dict[yname] += tres['y']

		ndx_curr += chunk

	write_out_dict(out_dict, xname, yname)


file_name = "../"

if __name__ == "__main__":
	__main__()
