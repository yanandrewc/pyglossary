# -*- coding: utf-8 -*-
# xdxf/__init__.py
"""xdxf file format reader and utils to convert xdxf to html."""
#
# Copyright © 2016 Ratijas <ratijas.t@me.com>
#
# some parts of this file include code from:
# Aard Dictionary Tools <http://aarddict.org>.
# Copyright © 2008-2009  Igor Tkach
#
# This program is a free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# You can get a copy of GNU General Public License along this program
# But you can always get it from http://www.gnu.org/licenses/gpl.txt
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

from os import path

from formats_common import *

enable = True
format = "Xdxf"
description = "XDXF"
extensions = [".xdxf", ".xml"]
singleFile = True
optionsProp = {}
depends = {
	"lxml": "lxml",
}

try:
	ModuleNotFoundError
except NameError:
	ModuleNotFoundError = ImportError


"""
new format
<xdxf ...>
	<meta_info>
		All meta information about the dictionary: its title, author etc.
	</meta_info>
	<lexicon>
		<ar>article 1</ar>
		<ar>article 2</ar>
		<ar>article 3</ar>
		<ar>article 4</ar>
		...
	</lexicon>
</xdxf>

old format
<xdxf ...>
	<full_name>...</full_name>
	<description>...</description>
	<ar>article 1</ar>
	<ar>article 2</ar>
	<ar>article 3</ar>
	<ar>article 4</ar>
	...
</xdxf>
"""

class Reader(object):
	def __init__(self, glos: GlossaryType):
		self._glos = glos
		self._xdxf = None
		self._old = False  # True if old format
		self.xdxf_init()

	def xdxf_init(self):
		"""
		call this only once, before `xdxf_to_html`.
		"""
		try:
			from lxml import etree as ET
		except ModuleNotFoundError as e:
			e.msg += ", run `sudo pip3 install lxml` to install"
			raise e

		xsl = path.join(path.dirname(__file__), "xdxf.xsl")
		with open(xsl, "r") as f:
			xslt_root_txt = f.read()

		xslt_root = ET.XML(xslt_root_txt)
		self._transform = ET.XSLT(xslt_root)

	def open(self, filename: str):
		from lxml import etree as ET
		# <!DOCTYPE xdxf SYSTEM "http://xdxf.sourceforge.net/xdxf_lousy.dtd">
		with open(filename, "rb") as f:
			self._xdxf = ET.XML(f.read())
		self._old = len(self._xdxf) > 2
		if self._old:
			self.read_metadata_old()
		else:
			self.read_metadata_new()

	def __len__(self):
		return 0  # FIXME

	def __iter__(self):
		from lxml.etree import tostring
		self._glos.setDefaultDefiFormat("x")
		rootElem = self._xdxf if self._old else self._xdxf.find("lexicon")
		for article in rootElem.iterfind("ar"):
			article.tail = None
			defi = tostring(article, encoding="utf-8")
			# <ar>...</ar>
			defi = defi[4:-5].strip()
			# FIXME: use self.xdxf_to_html(defi)
			yield self._glos.addEntry(
				[toStr(w) for w in self.titles(article)],
				toStr(defi),
			)

	def close(self) -> None:
		pass

	def read_metadata_old(self):
		full_name = self._xdxf.find("full_name").text
		desc = self._xdxf.find("description").text
		if full_name:
			self._glos.setInfo("name", full_name)
		if desc:
			self._glos.setInfo("description", desc)

	def read_metadata_new(self):
		meta_info = self._xdxf.find("meta_info")
		if meta_info is None:
			raise ValueError("meta_info not found")

		title = meta_info.find("full_title").text
		if not title:
			title = meta_info.find("title").text
		desc = meta_info.find("description").text

		if title:
			self._glos.setInfo("name", title)
		if desc:
			self._glos.setInfo("description", desc)

	def titles(self, article):
		"""

		:param article: <ar> tag
		:return: (title (str) | None, alternative titles (set))
		"""
		from itertools import combinations
		titles = []
		for title_element in article.findall("k"):
			n_opts = len([c for c in title_element if c.tag == "opt"])
			if n_opts:
				for j in range(n_opts + 1):
					for comb in combinations(list(range(n_opts)), j):
						titles.append(self._mktitle(title_element, comb))
			else:
				titles.append(self._mktitle(title_element))

		return titles


	def _mktitle(self, title_element, include_opts=None):
		if include_opts is None:
			include_opts = ()
		title = title_element.text
		opt_i = -1
		for c in title_element:
			if c.tag == "nu" and c.tail:
				if title:
					title += c.tail
				else:
					title = c.tail
			if c.tag == "opt":
				opt_i += 1
				if opt_i in include_opts:
					if title:
						title += c.text
					else:
						title = c.text
				if c.tail:
					if title:
						title += c.tail
					else:
						title = c.tail
		return title.strip()


	def xdxf_to_html(self, xdxf_text):
		"""
		make sure to call `xdxf_init()` first.

		:param xdxf_text: xdxf formatted string
		:return: html formatted string
		"""
		from lxml.etree import tostring
		from io import StringIO
		xdxf_txt = "<ar>" + xdxf_text + "</ar>"
		f = StringIO(xdxf_txt)
		doc = etree.parse(f)
		result_tree = self._transform(doc)
		return tostring(result_tree, encoding="utf-8")
