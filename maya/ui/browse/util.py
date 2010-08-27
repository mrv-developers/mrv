# -*- coding: utf-8 -*-
"""Contains misc utiltiies"""
__docformat__ = "restructuredtext"

def concat_url(root, path):
	if not root.endswith("/"):
		root += "/"
	return root + path

