#1/usr/bin/env python
import os
import sys
import time
import hashlib
from datetime import datetime
from boto import connect_s3
import luigi
from luigi.s3 import S3Client
from pathutils import project_path


class NectarS3Task(luigi.Task):
    def __init__(self, *args, **kwargs):
        super(NectarS3Task, self).__init__(*args, **kwargs)       
        self.KEY_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.000Z'
        self.s3client = S3Client(
                os.getenv('AWS_ACCESS_KEY_ID'),
                os.getenv('AWS_SECRET_ACCESS_KEY')
                )
        self.boto_s3_client = connect_s3(
                os.getenv('AWS_ACCESS_KEY_ID'),
                os.getenv('AWS_SECRET_ACCESS_KEY')
                )
        self.bucket = self.boto_s3_client.get_bucket('%s.%s' % (os.getenv('ENV', 'local'), os.getenv('PROJECT_BUCKET', 'datanectar')))

    def output(self):
        """
        Custom implementation for s3
        """
        return luigi.s3.S3Target(
                self.get_s3target_path(),
                client=self.s3client
                )

    def get_s3target_path_base(self):
        """
        Returns
        -------
        target_path : str of target path
        """
        module_name = sys.modules[self.__module__].__file__.split('/')[-1]
        module_name = module_name.strip('.py')
        module_name = module_name.strip('.pyc')
        # this could be an ENV variable that we first check
        # then default to datanectar
        return 's3://{0}.{1}/chains/{2}/{3}/{4}/{5}/%s'.format(
                os.getenv('ENV', 'local'),
                os.getenv('PROJECT_BUCKET', 'datanectar'),
                self.chain_type(),
                module_name,
                self.__class__.__name__,
                self.hash_params()
                )

    def get_s3target_path(self):
        """
        Returns
        -------
        target_path : str of target path
        """
        name = 'out.txt'
        self._target_path = self.get_s3target_path_base() % name
        return self._target_path

    def get_s3stdout_log_path(self):
        """
        Returns
        --------
        s3stdout_log_path : str of url to s3 stdout lot path for this task
        """
        return self.get_s3target_path_base() % 'log/%s' % 'stdout.log'

    def get_s3stderr_log_path(self):
        """
        Returns
        --------
        s3stderr_log_path : str of url to s3 stderr lot path for this task
        """
        return self.get_s3target_path_base() % 'log/%s' % 'stderr.log'

    def get_s3params_path(self):
        """
        Returns
        --------
        s3params_path : str of s3 url to params for this task
        """        
        return self.get_s3target_path_base() % 'params.txt'

    def get_s3target_relative_path_base(self):
        """
        Returns
        ------
        target_path : str of relative target path unformatted
        """     

        base = self.get_s3target_path_base()
        return '/'.join(base.split('/')[base.split('/').index('chains'):])

    def get_s3target_relative_path(self):
        """
        Returns
        -------
        relative_path : str like chains/test/TestS3Task/blah
        """
        name = 'out.txt'
        return self.get_s3target_relative_path_base() % name

    def get_s3stdout_log_relative_path(self):
        """
        Returns
        --------
        s3stdout_log_path : str of url to s3 stdout lot path for this task
        """
        return self.get_s3target_relative_path_base() % 'log/%s' % 'stdout.log'

    def get_s3stderr_log_relative_path(self):
        """
        Returns
        --------
        s3stderr_log_path : str of url to s3 stderr lot path for this task
        """
        return self.get_s3target_relative_path_base() % 'log/%s' % 'stderr.log'

    def get_s3params_relative_path(self):
        """
        Returns
        --------
        s3params_path : str of s3 url to params for this task
        """        
        return self.get_s3target_relative_path_base() % 'params.txt'

    def get_s3target_url(self, expires_in=600):
        """
        Parameters
        ---------
        expires_in : int expires_in how long url is good for (defaults to 600 [10 minutes])

        Returns
        ---------
        url : temporary url for target
        """
        if hasattr(self, '_target_path'):
            k = self.bucket.get_key(getattr(self, '_target_path'))
            if k:
                return k.generate_url(expires_in=expires_in)
        k = self.bucket.get_key(self.get_s3target_relative_path())
        if not k:
            raise type('TargetNotFoundException', (Exception,), {})("Couldn't find target with name: %s" % self.get_s3target_relative_path())
        return k.generate_url(expires_in=expires_in)

    def get_key_like(self, like=''):
        """
        Parameters
        ---------
        like : str of keys to get with this substr

        Returns
        --------
        keys : list of s3 keys with the like str inside
        """
        return filter(lambda x: like in x.name, self.bucket.get_all_keys())

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
