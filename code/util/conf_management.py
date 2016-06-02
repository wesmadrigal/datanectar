#!/usr/bin/env python
import os

class cd:
    def __init__(self, path):
        self.original_path = os.getcwd()
        self.new_path = path

    def __enter__(self):
        os.chdir(self.new_path)

    def __exist__(self, etype, value, traceback):
        os.chdir(self.original_path)
