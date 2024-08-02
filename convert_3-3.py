# -*- coding: utf-8 -*-
# Fast Markup Language (FML) interpreter
# edison23
# v3 - 2013

import re
import cgi
import sys
import os
import argparse
from time import gmtime, strftime

import config as cf

class ctrls:
	tabs = 0
	lists = []
	tabs_string = ""
	dont_process = 0
	tags = []
	br_control = 0

class colors:
    magenta = '\033[35m'
    blue = '\033[94m'
    green = '\033[32m'
    yellow = '\033[93m'
    red = '\033[91m'
    cyan = '\033[96m'
    reset = '\033[0m'

def headings(line):
	line = re.sub(r"^\$(\d) (.*)", r"<h\1>\2</h\1>", line.strip("\t"))
	return line

def dividers(line):
	line = re.sub(r"^\$([a-z]+) (.*)", r'<div class="\1">\2</div>', line.strip("\t"))	# using '' just bcs dunno how to escape quotes...
	return line	

def code(line):
	line = re.sub(r"(.*?)\<\?c(.*?)\?\>(.*?)", r"\1<code>\2</code>\3", line)
	return line

def inline_format(line):
	# links
	line = re.sub(r'((https?://|www)[-\w./#?%=&]+)', r'<a target="_blank" href="\1">\1</a>', line)
	
	# inline tags end either with closing tag or the end of line
	if "<a href=" not in line: # if there was a link in the line, not futher processing is performed
		# italics
		line = re.sub(r"%_(.*?)[_|\n]", r"<i>\1</i>", line)
		# bold
		line = re.sub(r"%\*(.*?)[\*|\n]", r"<b>\1</b>", line)
		# underline
		line = re.sub(r"%/(.*?)[/|\n]", r"<u>\1</u>", line)
		# subscript
		line = re.sub(r"%,(.*?)[,|\n]", r"<sub>\1</sub>", line)
		# superscript
		line = re.sub(r"%`(.*?)[`|\n]", r"<sup>\1</sup>", line)
		# font color 
		line = re.sub(r"%(\w+)%(.*?)[%|\n]", r'<font color="\1">\2</font>', line)	# accepts only named colors
		# notes
		line = re.sub(r"^\{(\d+)\} - (.*$)", r"<span class='note'>\1: \2</span>", line)
		line = re.sub(r"\{(\d+)\}", r"<sup><b>\1</b></sup>", line)
	return line

def images(line):
	line = re.sub(r'\$img (.*)\n', r'<a href="./.files/\1" target="_blank"><img src="./.files/\1"></a>', line)
	return line

def char_replace(line):
	for chars in range(len(cf.replacements)):
		line = line.replace(cf.replacements[chars][0], cf.replacements[chars][1])
	# non-breakable spaces after one-space words
	line = re.sub(r" (\w) ", r" \1 ", line)
	return line

def block_tag(line):
	# code
	if line == "<?c\n":
		ctrls.dont_process += 1
		ctrls.tags.extend(["pre"])
		return re.sub("<\?c", "\n<pre>", line)
	
	# bold, just for testing
	if line == "<?b\n":
		ctrls.tags.extend(["b"])
		return re.sub("\n<\?b", "<b>", line)
	
	# tables
	if line == "<?t\n":
		ctrls.tags.extend(["table"])
		return re.sub("<\?t", "\n<table>", line)
	
	#closing tag
	if line == "?>\n":
		ctrls.dont_process -= 1
		line = re.sub("\?>", "</" + ctrls.tags[(len(ctrls.tags)-1)] + ">\n", line)
		ctrls.tags.remove(ctrls.tags[(len(ctrls.tags)-1)])	# delete the closed tag from list
		return line
	if "table" in ctrls.tags:
		line = re.sub(r"^(.)", r"<tr><td>\1", line)
		line = line.replace("\t", "</td><td>")
		line = re.sub(r"$", r"</td></tr>", line)
		return line
	
	else:
		return cgi.escape(line)	# cgi.escape() escapes to html characters, so the code can contain stuff like <, >, etc.

def add_br(line):
	if line == "\n":
		return ""	# ignoring blank lines
	
	# special character for adding new line.
	elif line == "|\n":
		return "<br>\n"
	else:
		return line.strip("\n") + "<br>\n"

def list_new(line, uol):
	line = "<" + uol + ">\n" + list_newline(line, uol)
	ctrls.lists.append(uol)
	return line

def list_newline(line, uol):
	if uol == "ol":
		uol = "\+"
	else:
		uol = "-"
	ctrls.tabs = line.count("\t")
	ctrls.tabs_string = ctrls.tabs * "\t"
	line = re.sub(ctrls.tabs_string + uol + r" (.*)", "\t" + r"<li>\1</li>", line)
	return line

def list_tags(n, slash=""):
	tag_string = ""
	for i in range(n):
		tag_string += "<" + slash + ctrls.lists[-1] + ">\n"
		del ctrls.lists[-1]
	# print return_string
	return tag_string

def list_close(line, uol, all=0):
	if all == 0:
		line = list_tags((len(ctrls.lists)-1)-ctrls.tabs, "/") + list_newline(line, uol)
		# lists = tabs+1
	elif all == 1:
		line = list_tags(len(ctrls.lists), "/") + add_br(line)
		# lists = 0
	return line

def bullets(line, uol):
	# global tabs, lists
	if len(ctrls.lists) == 0:
		line = list_new(line, uol)
	else:
		if (len(ctrls.lists)-1) < line.count("\t"):	# zvysil se pocet vnorenych listu
			line = list_new(line, uol)
		elif (len(ctrls.lists)-1) == line.count("\t"):
			line = list_newline(line, uol)
		else:
			ctrls.tabs = line.count("\t")
			line = list_close(line, uol)	# closing only 1 list
	return line

def convert(line):
	# global rows
	if args.print_orig == True:
			print colors.blue, line,
	# blok tags, opening, closing
	if re.match(r"^<\?[a-z]$", line) or re.match(r"^\?>$", line):
		line = block_tag(line)
	# if blok tag is on no other function than following may be called
	elif ctrls.dont_process > 0:
		line = block_tag(line)
	else:
		# lists
		if re.match(r"^- ", line.strip("\t")):
			uol = "ul"
		elif re.match(r"^\+ ", line.strip("\t")):
			uol = "ol"
		else:
			uol = ""
		
		if uol == "ul" or uol == "ol":
			line = bullets(line, uol)
		elif len(ctrls.lists) >= 1:
			line = list_close(line, uol, all=1) # closing all lists at once
		# headings
		elif re.match(r"^\$\d (.*)", line):
			line = headings(line)
		# dividers (title, date)
		elif "$date" in line or "$title" in line:
			line = dividers(line)
		elif "$img" in line:
			line = images(line)
		elif "table" in ctrls.tags:
			line = block_tag(line)
		else:
			line = add_br(line)

		# inline code
		line = code(line)
		# formatting
		line = inline_format(line)
		# character replacing
		line = char_replace(line)
	if args.print_conv == True:
			print colors.cyan, line,
	return line


def copy_dirs(from_dir, to_dir, subdir):
	if os.path.exists(from_dir):
		if os.name == "posix":
			os.system("cp -rf " + from_dir + "/" + subdir + " " + to_dir)	# here should be some real control whether the copying finished successfully
			print colors.magenta + "\tFiles in '" + from_dir + "/" + subdir + "' copied." + colors.reset
			return True
		elif os.name == "nt":
			os.system("xcopy " + from_dir.replace("/", "\\") + "\\" + subdir + " " + to_dir.replace("/", "\\") + "\\" + subdir + " /s /q /y")
			return True
		else:
			print "It seems I am unable to copy directories on this OS. I work with OS's identified as 'posix' and 'nt'."
			return False
	else:
		print "Not found"

def copy_files(path="", cp_styles=False, cp_files=False):
	current_dir, _ = os.path.split(os.path.abspath(__file__))
	if cp_styles == True:
		print "Copying styles..."
		if copy_dirs(current_dir, path, ".styles"):
			print "Done."
		else:
			print "Failed."
	elif cp_files == True:
		if os.path.exists(path + "/.files/"):
			copy_dirs(path, cf.out_path, ".files")

def rename_file(fname):
	return fname.replace(cf.prefix, cf.new_prefix).replace(cf.sufix, "") +".html"

def write_file(path="", out_path="", single=False, cp_styles=False, cp_files=False):
	(path,fname) = os.path.split(path)
	current_dir, _ = os.path.split(os.path.abspath(__file__))	# _ --free variable
	if not os.path.exists(out_path):
		print "Output path does not exist, creating: ", out_path
		os.makedirs(out_path)
	if single:
		out_path = path
		copy_files(out_path, cp_styles, cp_files)

	f_in = open(path + "/" + fname)
	new_name = rename_file(fname)
	f_out = open(out_path + "/" + new_name, "w+")

	doc_title = cf.doc_title + " :: " + new_name.replace(".html", "")
	f_out.write(open(current_dir + cf.header).read().replace("doc_title", doc_title.encode('utf-8')))

	for line in f_in:
		f_out.write(convert(line.rstrip()+"\n"))	# pridat konce radku

	sys.stdout.write(colors.reset)	# reset the colors (which are in effect with parameters causing stdout print of files)
	
	last_update = '<div id="last_update">\n\tLast update: ' + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' UTC\n</div>'
	f_out.write(open(current_dir + cf.footer).read().replace("last_update", last_update))
	print "PROCESSED:", fname, "->", new_name

def file_ops(path):
	if "-s" in sys.argv:
		if not os.path.exists(args.filename):
			print "Path or file doesnt exist."
		else:
			if "-n" not in sys.argv:
				cp_styles = True
			else:
				cp_styles = False
				cp_files = False
			write_file(args.filename, args.filename, single=True, cp_styles=cp_styles)
	else:
		for fname in os.listdir(path):
			if os.path.isdir(path + "/" + fname):
				file_ops(path + "/" + fname)
			else:
				if re.match(r".*" + cf.prefix + r".*" + cf.sufix, fname):
					if "-n" not in sys.argv:
						cp_files = True
					else:
						cp_files = False
					copy_files(path, cp_styles=False, cp_files=cp_files)
					write_file(path + "/" + fname, cf.out_path)

parser=argparse.ArgumentParser(
    description="Script for parsing special markup designed for creating fast formatted notes.",
    epilog="For complete documentation see http://edison23.net/bleh/specification.html.")
parser.add_argument('-n', '--nostyle', action='store_true', help='disables copying of style.css and fonts; useful for updating existing document')
parser.add_argument('-s', '--single', action='store', dest="filename", help='process a single file')
parser.add_argument('-p', '--print_orig', action='store_true', help='print original lines of the processed file(s) to standard output - use with care when in batch mode!')
parser.add_argument('-q', '--print_conv', action='store_true', help='print converted lines of the processed file(s) to standard output - use with care when in batch mode!')
parser.add_argument('-v', '--version', action='version', version='%(prog)s 3.2')
args=parser.parse_args()

path = cf.path
out_path = cf.out_path

file_ops(path)

if args.nostyle == False and not args.filename:
	copy_files(out_path, cp_styles=True, cp_files=False)
	print "\nInput directory: " + path + " | Output directory: " + out_path + colors.green + "\nAll files processed." + colors.reset


