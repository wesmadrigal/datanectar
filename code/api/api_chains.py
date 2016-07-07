#!/usr/bin/env python
import os
import sys
import luigi
import importlib
from pathutils import project_path

TASK_BASE_DIR = os.path.join(project_path(), 'code')
TASK_CHAIN_BASE_DIR = os.path.join(TASK_BASE_DIR, 'chains')
sys.path.append(TASK_BASE_DIR)

VPC = os.getenv('VPC', 'http://localhost:5000')
API_BASE = VPC + '/api'

class APIChainNotFound(Exception): pass

class APIChainCollection:
    def __init__(self):        
        self.chains = {}
        for _d in filter(lambda x: '.py' not in x and '.pyc' not in x, os.listdir(TASK_CHAIN_BASE_DIR)):
            if not self.chains.get(_d):
                self.chains[_d] = []
            self.chains[_d] = {
                'chain_path' : os.path.join(TASK_CHAIN_BASE_DIR, _d),
                'api_href' : API_BASE + '/chains/%s' % _d,
                'chains' : []
                }
            for f in os.listdir(os.path.join(TASK_CHAIN_BASE_DIR, _d)):            
                if '_chain' in f and f.endswith('.py'):
                    self.chains[_d]['chains'].append( APIChain(os.path.join(self.chains[_d]['chain_path'], f)) )

    def to_dict(self):
        """
        Converts object to JSON / API friendly dict
        """
        import copy
        chain_copy = copy.copy(self.chains)
        for k in chain_copy.keys():
            chain_copy[k]['chains'] = map(lambda x: x.to_dict(), chain_copy[k]['chains'])
        return chain_copy

    def get_types(self):
        """
        Returns
        -------
        task chain types
        """        
        return self.chains.keys()

    def get_chains_by_type(self, type=''):
        """
        Parameters
        ----------
        type : str of type to get chains for
        
        Returns
        ------
        chains : list of APIChain instances
        """
        return self.chains.get(type, None)


class APIChain:
    def __init__(self, path):
        """
        Parameters
        ---------
        path : str of path to module        
        """
        if not os.path.exists(path):
            raise APIChainNotFound("chain module with path %s not found" % path)
        self._path = path
        tvar = self._path.strip('.py')
        self._api_path = API_BASE + '/%s' % '/'.join(tvar.split('/')[tvar.split('/').index('chains'):])
        self._type = os.path.dirname(path).split('/')[-1] # api chain type
        self._dir_path = os.sep.join(self._path.split('/')[0:-1])
        # TODO this is pretty ugly and should be refactored - needs to be more extensible
        module_dot_path = '.'.join(path.split('/')[path.split('/').index('chains') : -1] + [path.split('/')[-1].split('.')[0]])
        self._module = importlib.import_module(module_dot_path)

    def to_dict(self):
        """
        Returns a JSON version of this object
        """
        return {
                'path' : self._path,
                'api_href' : self._api_path,
                'tasks' : [
                    {
                    'task_name' : t.__name__,
                    'description' : t.__doc__,
                    'parameters' : [
                        p[0] for p in t.get_params()
                        ]
                    }
                    for t in self.load_tasks()
                    ]
                }

    def get_path(self):
        """
        Returns
        -------
        self._path : str of path to chain module
        """
        return self._path        

    def get_module(self):
        """
        Returns
        -------
        module : python module
        """
        return self._module

    def get_module_name(self):
        """
        Returns
        ------
        module_name : str
        """
        return self._path.split('/')[-1]

    def get_type(self):
        """
        Returns
        -------
        type : the type of chain this is
        """
        return self._type

    def get_purpose(self):
        """
        Returns
        -------
        purpose : the purpose of this chain
        """
        return self._module.__doc__ 

    def load_tasks(self):
        """
        Returns
        -------
        tasks : list of the tasks for this chain
        """
        return [
               getattr(self._module, t)
               for t in filter(lambda x: x.endswith('Task'), dir(self._module))
               if issubclass(getattr(self._module, t), luigi.Task)
             ] 

    def execute_task(self, task_name, **kwargs):
        """
        Parameters
        ----------
        task_name : str of task name
        kwargs : luigi.Task kwargs

        Returns
        ---------
        s3url : s3 url path to output
        """
        t = filter(lambda x: x.__name__ == task_name, self.load_tasks())
        if len(t) > 0:
            t = t[0]
            tinst = t(**kwargs)
            # let's make sure we're running our dependencies
            tinst.requires().run()
            tinst.run()
            return tinst.get_s3target_url() 
        return None
