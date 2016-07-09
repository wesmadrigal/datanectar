#!/usr/bin/env python
import os
import sys

# 3rd party
import luigi
from pathutils import project_path

# internal
from nectar_task import NectarTask

class NectarLocalTask(NectarTask):
    def __init__(self, *args, **kwargs):
        super(NectarLocalTask, self).__init__(*args, **kwargs)
        # all relevant directories
        self.PROJECT_DIR = project_path()
        self.CHAIN_DIR = os.path.join(self.PROJECT_DIR, 'local_targets/chains')
        self.TYPE_DIR = os.path.join(self.CHAIN_DIR, self.chain_type())
        # will possibly have to be modified on the individual task level
        self.SPECIFIC_CHAIN_DIR = os.path.join(self.TYPE_DIR, self.chain())
        self.TASK_DIR = os.path.join(self.SPECIFIC_CHAIN_DIR, self.__class__.__name__)
        self.INSTANCE_DIR = os.path.join(self.TASK_DIR, self.hash_params())
        self.LOG_DIR = os.path.join(self.INSTANCE_DIR, 'log')
        self.TARGET_PATH = os.path.join(self.INSTANCE_DIR, 'out.txt')
        self.STDOUT_PATH = os.path.join(self.LOG_DIR, 'stdout.log')
        self.STDERR_PATH = os.path.join(self.LOG_DIR, 'stderr.log')

    def setup_dirs(self):
        """
        Makes sure all relevant directories are instantiated
        """
        if not os.path.isdir(self.CHAIN_DIR):
            os.mkdir(self.CHAIN_DIR)
        if not os.path.isdir(self.TYPE_DIR):
            os.mkdir(self.TYPE_DIR)
        if not os.path.isdir(self.SPECIFIC_CHAIN_DIR):
            os.mkdir(self.SPECIFIC_CHAIN_DIR)
        if not os.path.isdir(self.TASK_DIR):           
            os.mkdir(self.TASK_DIR)
        if not os.path.isdir(self.INSTANCE_DIR):
            os.mkdir(self.INSTANCE_DIR)
        if not os.path.isdir(self.LOG_DIR):
            os.mkdir(self.LOG_DIR)

    def output(self):
        """
        Custom implementation of luigi.Task.output method        
        """
        return luigi.LocalTarget(self.TARGET_PATH)

    def run(self, *args, **kwargs):
        """
        Custom implementation of luigi.Task.run method

        Sets up local paths and/or makes sure they exist first
        """
        self.setup_dirs()
        super(NectarLocalTask, self).run(*args, **kwargs)
