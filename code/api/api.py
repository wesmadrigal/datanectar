#!/usr/bin/env python
import os
import sys
import luigi
import json
import logging
import requests
import subprocess
import tempfile
from flask.views import View, request
from flask import Response, jsonify
import importlib

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('datanectar_api.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

from pathutils import project_path
sys.path.append(os.path.join(project_path(), 'code'))

from api_chains import APIChainCollection
from util.luigi_helpers import traverse_task_requires
from util.aws_conns import connect_s3

VPC = os.getenv('VPC', 'localhost:5000')
LUIGI_URI = os.getenv('LUIGI_URI', 'http://localhost:8082')
LUIGI_STATUS_URI = '%s/api/task_list?data={"status":"%s","upstream_status":"","search":""}'
DATANECTAR_STATUS_URI = 'http://{0}/api/chainstatus?chain={1}'
PROJECT_BASE = project_path()

class Chains(View):
    def dispatch_request(self):
       coll = APIChainCollection()
       return jsonify(**coll.to_dict())

class ChainType(View):
    def dispatch_request(self, type=None):
        coll = APIChainCollection()
        if type is not None:
            try:
                this_chain_type = coll.chains[type]
                this_chain_type['chains'] = map(lambda x: x.to_dict(), this_chain_type['chains'])
                return jsonify(**this_chain_type)
            except Exception, e:
                response = {
                        "data" : {},
                        "status" : 400,
                        "message" : "No such chain type: %s" % type
                        }
                return jsonify(**response)
        else:
            return jsonify(**{
                "data" : {},
                "status" : 400,
                "message" : "Need a chain 'type' parameterized"
                })

class Chain(View):
    def dispatch_request(self, type=None, chain=None):
        coll = APIChainCollection() 
        if type is not None and chain is not None:
             try:
                 this_chain = filter(lambda x: x.get_module_name().strip('.py') == chain, coll.chains[type]['chains']) 
                 this_chain = this_chain[0]
                 if request.method == 'GET':
                     return jsonify(**this_chain.to_dict())
             except Exception, e:                
                 if locals().get('err', None):
                     resp = locals().get('err')
                 else:
                     resp = 'fail'
                 logger.error(resp)
                 response = {
                         "data" : {},
                         "status" : 400,
                         "message" : resp
                         }
                 return jsonify(**response)
        else:
             response = {
                     "data" : {},
                     "status" : 400,
                     "message" : "type and/or chain both need string values"
                     }
             return jsonify(**response)

class Task(View):
    methods = ['GET', 'POST']
    def dispatch_request(self, type=None, chain=None, task=None):
        coll = APIChainCollection()
        if type is not None and chain is not None and task is not None:
            try:
                this_chain = filter(lambda x: x.get_module_name().strip('.py') == chain, coll.chains[type]['chains']) 
                this_chain = this_chain[0]
                dict_version = this_chain.to_dict()
                # if it's just a GET request just return the resource
                if request.method == 'GET':
                    task = [ d for d in dict_version['tasks'] if d['task_name'] == task]
                    if len(task) > 0:
                        return jsonify(**{
                            "data" : task[0],
                            "status" : 200,
                            "message" : "success"
                        })
                    else:
                        return jsonify(**{
                            "data" : {},
                            "status" : 400,
                            "message" : "No tasks with name %s" % task
                            })
                elif request.method == 'POST':
                    tasks = filter(lambda x: x.__name__ == task, this_chain.load_tasks())
                    # let's try running this task with subprocess
                    if len(tasks) > 0:
                        local = True if os.getenv('ENV', 'local') == 'local' else False
                        this_task = tasks[0]
                        stdout_path = tempfile.mktemp()
                        stderr_path = tempfile.mktemp()
                        stdout = open(stdout_path, 'w')
                        stderr = open(stderr_path, 'w')
                        the_args = []
                        for k in request.args.keys():
                            the_args.append('--%s' % k)
                            the_args.append(request.args.get(k))
                        project_python_path = os.path.join(project_path(), 'venv/bin/python')
                        total_args = [project_python_path, this_chain.get_path(), task] + the_args
                        p = subprocess.Popen(
                                total_args,
                                stdout=stdout,
                                stderr=stderr
                                )                    
                        # let's fire up a task instance for the rest of what we need here
                        this_task_instance = this_task(**{k: request.args.get(k) for k in request.args.keys()})                       
                        if local:
                            resp = {
                                "data" : {
                                    "status_url" : DATANECTAR_STATUS_URI.format(VPC, this_task_instance.get_s3target_relative_path()),
                                    "expires_in" : 600
                                    },
                                "status" : 200,
                                "message" : "success"
                                }
                            return jsonify(resp)
                        out_s3path = this_task_instance.get_s3stdout_log_relative_path()
                        err_s3path = this_task_instance.get_s3stderr_log_relative_path()
                        out_s3_key = this_task_instance.bucket.new_key(out_s3path)
                        err_s3_key = this_task_instance.bucket.new_key(err_s3path)
                        out_s3_key.set_contents_from_filename(stdout_path)
                        err_s3_key.set_contents_from_filename(stderr_path)
# let's add the params
                        param_path = this_task_instance.get_s3params_relative_path()
                        param_key = this_task_instance.bucket.new_key(param_path)
                        param_key.set_contents_from_string(json.dumps(this_task_instance.param_kwargs))
                        # we'll return an endpoint for the status http location
                        resp = {
                                "data" : {
                                    "status_url" : DATANECTAR_STATUS_URI.format(VPC, this_task_instance.get_s3target_relative_path()),
                                    "expires_in" : 600
                                    },
                                "status" : 200,
                                "message" : "success"
                                }
                        logger.info("Executed task with name: %s" % task)
                        return jsonify(**resp)

                    else:
                        logger.info("Attempted to execute task with name %s but no such task exists" % task)
                        return
            except Exception, e:
                logger.error("Encountered an error executing task with name: %s" % task) 
                try:
                    status = 400
                    message = e.message
                except Exception, e:
                    status = 400
                    message = getattr(e, 'message', 'No error message')
                logger.error(message)
                resp = {
                        "data" : {},
                        "status" : status,
                        "message" : message
                        }
                return jsonify(**resp)


class ChainStatus(View):
    def dispatch_request(self):
        if request.args.has_key('chain'):
            local = True if os.getenv('ENV', 'local') == 'local' else False
            chain_key = request.args.get('chain')            
            task_name = chain_key.split('/')[-3]
            task_hashed_params = chain_key.split('/')[-2]
            luigi_statuses = ['PENDING', 'RUNNING', 'DONE', 'FAILED'] 
            task_status = None
            for status in luigi_statuses:
                status_endpoint = LUIGI_STATUS_URI % (LUIGI_URI, status)
                logger.debug("Checking %s" % status_endpoint)
                resp = requests.get(status_endpoint)
                data = json.loads(resp.text)
                for k in data['response'].keys():
                    if task_name in k:
                        task_status = status
                        break
            if local:
                return jsonify(**{
                    "status" : 200,
                    "data" : {
                        "job_status": task_status,
                        "resource_url": None,
                        "expires_in" : 1000000000000
                        }
                    })
            s3conn = connect_s3()
            bucket = s3conn.get_bucket('%s.%s' % (os.getenv('ENV', 'local'), os.getenv('PROJECT_BUCKET', 'datanectar')))
            if task_status == 'DONE' or task_status is None: 
                key = bucket.get_key(chain_key)
            else:
                key = None

            return jsonify(**{
               "status" : 200,
               "data" : {
                   "job_status" : task_status,
                   "resource_url" : key.generate_url(expires_in=600) if key is not None else None,
                   "expires_in" : 600 if key is not None else None
                   },
               "message" : "success"
               })
        else:
            return jsonify(**{
                "status" : 400,
                "data" : {},
                "message" : "Need chain parameter"
                })
