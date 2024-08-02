# -*- coding: utf-8 -*-
# convert notes to html v3

import re
import cgi
import sys
import os
import argparse
from time import gmtime, strftime

import config

tabs = 0
lists = 0
tabs_string = ""
dont_process = 0
tags = []
br_control = 0

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
	line = re.sub(r'((https?://|www)[-\w./#?%=&]+)', r'<a href="\1">\1</a>', line)	# links - if there was a link on the line, not futher processing is performed
	if "<a href=" not in line:
		line = re.sub(r"\^_(.*?)[_|\n]", r"<i>\1</i>", line)	# inline tags end either with closing tag or the end of line
		line = re.sub(r"\^\*(.*?)[\*|\n]", r"<b>\1</b>", line)
		line = re.sub(r"\^,(.*?)[,|\n]", r"<sub>\1</sub>", line)
		line = re.sub(r"\^`(.*?)[`|\n]", r"<sup>\1</sup>", line)
		line = re.sub(r"\^/(.*?)[/|\n]", r"<u>\1</u>", line)
		line = re.sub(r"%(\w+)%(.*?)[%|\n]", r'<font color="\1">\2</font>', line)	# accepts only named colors
	return line

def images(line):
	line = re.sub(r'\$img (.*)\n', r'<a href="./.files/\1" target="_blank"><img src="./.files/\1"></a>', line)
	return line

def char_replace(line):
	line = line.replace("->", "→").replace("<-", "←").replace("...", "…")
	line = re.sub(r" (\w) ", r" \1 ", line)
	return line

def blok_tag(line):
	global dont_process, tags
	# code
	if re.match(r"^<\?c$", line):	# code. no regex needed here
		dont_process += 1
		tags.extend(["pre"])
		return re.sub("<\?c", "\n<pre>", line)
	# bold, just for testing
	if re.match(r"^<\?b$", line):	# bold. no regex needed here
		tags.extend(["b"])
		return re.sub("\n<\?b", "<b>", line)
	if re.match(r"^<\?t$", line):
		tags.extend(["table"])
		return re.sub("<\?t", "\n<table>", line)
	if re.match(r"^\?>$", line):	# closing tag. no regex needed here
		dont_process -= 1
		line = re.sub("\?>", "</" + tags[(len(tags)-1)] + ">\n", line)
		tags.remove(tags[(len(tags)-1)])	# delete the closed tag from list
		return line
	if "table" in tags:
		line = re.sub(r"^(.)", r"<tr><td>\1", line)
		line = line.replace("\t", "</td><td>")
		line = re.sub(r"$", r"</td></tr>", line)
		return line
	else:
		return cgi.escape(line)	# cgi.escape() escapes to html characters, so the code can contain stuff like <, >, etc.

def add_br(line):
	if line == "\n":
		return ""	# ignoring blank lines
	elif line == "|\n":
		return "<br>\n"
	else:
		return line.strip("\n") + "<br>\n"

def list_new(line):
	global tabs, lists, tabs_string
	line = "<ul>\n" + list_newline(line)
	lists += 1
	return line

def list_newline(line):
	global tabs, tabs_string
	tabs = line.count("\t")
	tabs_string = tabs * "\t"
	line = re.sub(tabs_string + r"- (.*)", "\t" + r"<li>\1</li>", line)
	return line

def list_close(line, all=0):
	global tabs, lists, tabs_string
	if all == 0:
		line = "</ul>\n" * ((lists-1)-tabs) + list_newline(line)
		lists = tabs+1
	elif all == 1:
		line = "</ul>\n" * lists + add_br(line)
		lists = 0
	return line

def bullets(line):
	global tabs
	if lists == 0:
		line = list_new(line)
	else:
		if (lists-1) < line.count("\t"):	# zvysil se pocet vnorenych listu
			line = list_new(line)
		elif (lists-1) == line.count("\t"):
			line = list_newline(line)
		else:
			tabs = line.count("\t")
			line = list_close(line)	# closing only 1 list
	return line

def convert(line):
	global rows
	if args.print_orig == True:
			print "\033[94m", line,
	# blok tags, opening, closing
	if re.match(r"^<\?[a-z]$", line) or re.match(r"^\?>$", line):
		line = blok_tag(line)
	# if blok tag is on no other function than following may be called
	elif dont_process > 0:
		line = blok_tag(line)
	else:
		# lists
		if re.match(r"^- ", line.strip("\t")):
			line = bullets(line)
		elif lists >= 1:
			line = list_close(line, all=1) # closing all lists at once
		# headings
		elif re.match(r"^\$\d (.*)", line):
			line = headings(line)
		# dividers (title, date)
		elif "$date" in line or "$title" in line:
			line = dividers(line)
		elif "$img" in line:
			line = images(line)
		elif "table" in tags:
			line = blok_tag(line)
		else:
			line = add_br(line)

		# inline code
		line = code(line)
		# formatting
		line = inline_format(line)
		# character replacing
		line = char_replace(line)
	if args.print_conv == True:
			print "\033[96m", line,
	return line


def copy_dirs(from_dir, to_dir, subdir):
	red = "\033[35m"
	reset = "\033[0m"
	if os.path.exists(from_dir):
		if os.name == "posix":
			os.system("cp -rf " + from_dir + "/" + subdir + " " + to_dir)
			print red + "\tFiles in '" + from_dir + "/" + subdir + "' copied." + reset
			return True
		elif os.name == "nt":
			os.system("xcopy " + from_dir.replace("/", "\\") + "\\" + subdir + " " + to_dir.replace("/", "\\") + "\\" + subdir + " /s /q /y")
			return True
		else:
			print "It seems I am unable to copy directories on this OS. I work with OS's identified as 'posix' and 'nt'."
			return False
	else:
		print "Not found"

def copy_files(path="", cp_styles=False):
	if cp_styles == True:
		print "Copying styles..."
		if copy_dirs(".", path, ".styles"):
			print "Done."
		else:
			print "Failed."
	else:
		if os.path.exists(path + "/.files/"):
			copy_dirs(path, config.out_path, ".files")

def rename_file(fname):
	return fname.replace(config.prefix, config.new_prefix).replace(config.sufix, "") +".html"

def write_file(path="", out_path="", single=False, cp_styles=False):
	# print cp_styles
	(path,fname) = os.path.split(path)
	if not os.path.exists(out_path):
		print "Output path does not exist, creating: ", out_path
		os.makedirs(out_path)
	if single:
		out_path = path
		copy_files(out_path, cp_styles)

	f_in = open(path + "/" + fname)
	new_name = rename_file(fname)
	# print out_path + "/" + new_name
	f_out = open(out_path + "/" + new_name, "w+")

	doc_title = config.doc_title + " :: " + new_name.replace(".html", "")
	f_out.write(open(config.header).read().replace("doc_title", doc_title.encode('utf-8')))

	for line in f_in:
		f_out.write(convert(line.rstrip()+"\n"))	# pridat konce radku

	print "\033[0m",	# reset the colors (which are in effect with parameters causing stdout print of files)
	
	last_update = '<div id="last_update">\n\tLast update: ' + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' UTC\n</div>'
	f_out.write(open(config.footer).read().replace("last_update", last_update))
	print "PROCESSED:", fname, "->", new_name

def file_ops(path):
	# if len(sys.argv) > 1:
	if "-s" in sys.argv:
		if not os.path.exists(args.filename):
			print "Path or file doesnt exist."
		else:
			if "-n" not in sys.argv:
				cp_styles = True
			else:
				cp_styles = False
			write_file(args.filename, args.filename, single=True, cp_styles=cp_styles)
	else:
		for fname in os.listdir(path):
			if os.path.isdir(path + "/" + fname):
				file_ops(path + "/" + fname)
			else:
				if re.match(r".*" + config.prefix + r".*" + config.sufix, fname):
					copy_files(path, cp_styles=False)
					write_file(path + "/" + fname, config.out_path)

parser=argparse.ArgumentParser(
    description="Script for parsing special markup designed for creating fast formatted notes.",
    epilog="For complete documentation see http://edison23.net/bleh/specification.html.")
parser.add_argument('-n', '--nostyle', action='store_true', help='disables copying of style.css and fonts; useful for updating existing document')
parser.add_argument('-s', '--single', action='store', dest="filename", help='process a single file')
parser.add_argument('-p', '--print_orig', action='store_true', help='print original lines of the processed file(s) to standard output - use with care when in batch mode!')
parser.add_argument('-q', '--print_conv', action='store_true', help='print converted lines of the processed file(s) to standard output - use with care when in batch mode!')
parser.add_argument('-v', '--version', action='version', version='%(prog)s 3.1')
args=parser.parse_args()

path = config.path
out_path = config.out_path

file_ops(path)

if args.nostyle == False and not args.filename:
	copy_files(out_path, cp_styles=True)
	print "\nInput directory: " + path + " | Output directory: " + out_path + "\n\033[92mAll files processed.\033[0m"


