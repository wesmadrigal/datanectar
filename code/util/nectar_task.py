#!/usr/bin/env python
# internal
import os
import sys
import hashlib
from datetime import datetime

# 3rd party
import luigi

# internal
from pathutils import project_path


class NectarTask(luigi.Task):
    """
    Base for all child Task classes in
    the project.  Provides base methods
    for nectar tasks.
    """
    def __init__(self, *args, **kwargs):
        super(NectarTask, self).__init__(*args, **kwargs)

    def join_params(self, sep='_', frequency='day'):
        """
        Parameters
        ----------
        sep : str of params joined
        frequency : frequency of job so we can make sure this is unique per execution frequency
        
        Returns
        --------
        joined_params : str of the joined params
        """
        keys_sorted_by_letter = list(sorted([k for k in self.to_str_params().keys()], key=lambda x: sum(map(ord, [l for l in x]))))
        return datetime.strftime(datetime.now(), '%Y-%m-%d' if frequency == 'day' else '%Y-%m-%d %H') \
                if not len(keys_sorted_by_letter) \
                else  sep.join([self.to_str_params()[k] for k in keys_sorted_by_letter])

    def hash_params(self):
        """
        Returns
        -------
        hashed_params : returns hashed params        
        """
        return hashlib.md5(self.join_params()).hexdigest()

    def chain_type(self):
        """
        Returns
        -------
        type : str of the type of chain this task belongs to
        """
        module_path = os.path.join(
                project_path(),
                os.path.abspath(sys.modules[self.__module__].__file__)
                )
        dir_path = os.path.dirname(module_path)
        return dir_path.split(os.sep)[-1] 

    def get_relative_path_base(self):
        """
        Returns
        -------
        path : str '/' delimited relative path (either local or s3)        
        """
        module_name = sys.modules[self.__module__].__file__.split('/')[-1]
        module_name = module_name.strip('.py')
        module_name = module_name.strip('.pyc')
        return "chains/{0}/{1}/{2}/{3}/%s".format(
                self.chain_type(),
                module_name,
                self.__class__.__name__,
                self.hash_params()
                )

    def get_target_relative_path(self, name='out.txt'):
        """
        Params
        ------
        name : str of name of file

        Returns
        -------
        path : str '/' delimited relative path (either local or s3)
        """
        return self.get_relative_path_base() % name


    def get_log_relative_path(self):
        return self.get_relative_path_base() % 'log'

    def get_stdout_log_relative_path(self):
        return self.get_log_relative_path() + '/%' % 'stdout.log'

    def get_stderr_log_relative_path(self):
        return self.get_log_relative_path() + '/%' % 'stderr.log'
