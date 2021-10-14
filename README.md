# Datanectar is a base architecture for large-scale, production-ready, ETL and data science jobs.

## Goals
1. Dependency based task chain execution workflow (one task's completion is the requirement for the next downstream task, etc.)
2. Task idempotency
3. Task failover resolution
4. Task logging
5. Task visualization front-end
6. Dynamically built API
7. Bridgeing the gap between data science and software engineering (lets the data scientists worry about the data science and provides a software engineering backend for them to work with and go directly to production)

### Dependency based task chain execution workflow
Datanectar heavily leverages Spotify's [luigi](https://media.readthedocs.org/pdf/luigi/latest/luigi.pdf).  Luigi provides a very nice architecture for dependency based task chain workflows.  Since there is a plethora of documentation on the project, I'm going to defer going deeper to their docs.


### Dynamically built backend schema
Datanectar builds target locations based on project-level code locations by looking within the code directory.

### Task failover resolution
Due to the fact we have achieved idempotency in the project, if we have a 5 step task chain and step 3 fails, we can simply pick back up at step 3 after the bug is fixed.  Our step 1-3 targets (the output of our tasks) are already in S3 (or our local filesystem if we're doing local dev).

### Task logging
Datanectar creates tempfiles and pushes them to S3 out of the box for us.

### Task visualization front-end
Thanks to the authors of luigi, we get a d3 directed acyclic graph of tasks, their statuses, and stack traces for free.  Since datanectar uses luigi, this is available fo free

### Dynamically built API
Datanectar imposes certain taxonomy on the developer to make use of a dynamically available API for HTTP based task execution (if desired).  
* All task chains must live under some <b>chains/[somechaintype]</b> dir.  
* The actual chain definition in python code must be suffixed with <b>_chain.py</b>.  Ex. (<b>hello_luigiworld_chain.py</b>).  
* The <i>Task</i> classes within the chain.py file must be suffixed with <b>Task</b> Ex. (<b>TestS3Task, DownstreamTask, ETLTask</b>). 
If these schema and taxonomy are not followed, there will be no API availability at (http://localhost:5000/api/chains or your custom project URI in production).


## Local Setup
* checkout the project `git clone https://github.com/wesmadrigal/datanectar`
* `cd datanectar`
* build the virtual environment: `virtualenv venv`
* install dependencies: `venv/bin/pip install -r configuration/requirements.txt`
* startup the luigi server: `source venv/bin/activate && luigid`
* startup the app server: `cd ~/path/to/datanectar/code/ && ../venv/bin/python app.py`
* visit http://localhost:5000 (app front-end)
* visit http://localhost:8082 (luigi front-end)

## API and Hello World task (Local)
* make sure you've got the <b>app</b> and <b>luigi</b> running (final steps in local setup)
* visit <i>http://localhost:5000/api/chains</i> to explore the available task chains
* we'll be using the test chain at <i>http://localhost:5000/api/chains/testchains/hello_luigiworld_chain</i>
* fire up a python shell (you'll need the `requests` package)
* in the python shell execute the following:
* `import requests`
* `r = requests.post('http://localhost:5000/api/chains/testchains/hello_luigiworld_chain/TestS3Task')
* `print r.text`
```
{
  "data": {
    "expires_in": 600, 
    "status_url": "http://localhost:5000/api/chainstatus?chain=chains/testchains/hello_luigiworld_chain/TestS3Task/b226f1826734303ca9d39d79f960b367/out.txt"
  }, 
  "message": "success", 
  "status": 200
}
```
* `status = requests.get('http://localhost:5000/api/chainstatus?chain=chains/testchains/hello_luigiworld_chain/TestS3Task/b226f1826734303ca9d39d79f960b367/out.txt')`
* `print status.text`
```
{
data: {
expires_in: null,
job_status: "RUNNING",
resource_url: null
},
message: "success",
status: 200
}
```
* visit http://localhost:8082 and check the status on the luigi front-end (the API mirrors this status)
* when the task finally finishes (after about 2 minutes), you should see the target in <i>~/path/to/datanectar/local_targets</i>
* if you don't see it there, check the luigi front-end to see if a stack trace exists

## API and Hello World (production-ready REQUIRES AWS ACCESS)
* this is where our Environment variables come in
* in your ~/.bash_profile or ~/.profile dependening on your distribution, set the following
* `AWS_ACCESS_KEY_ID=YOURKEY`
* `AWS_SECRET_ACCESS_KEY=YOURSECRET`
* `ENV=(qa, prod, or your preference for env name but needs to be something other than local)`
* `PROJECT_BUCKET=yourcustomprojectname`
* Now that we have our environment variables set, make sure you've resourced the environment in all relevant terminals before continuing `source ~/.bash_profile` or `source ~/.profile`
* fire up the app server 
* `cd ~/path/to/datanectar/code && ../venv/bin/python app.py`
* fire up luigi 
* `cd ~/path/to/datanectar && venv/bin/python luigid`
* ok, given that your AWS credentials are correct we will now do the same as the local hello world but our output will go to s3 instead of our local machine
* fire up a python shell and execute the following commands
* `import requests, json`
* `r = requests.post('http://localhost:5000/api/chains/testchains/TestS3Task')
* `status_url = json.loads(r.text)['data']['status_url'])`
* <b>when the task finishes this time, our status URL will respond with the S3 resource</b>
* `status_resource = requests.get(status_url)`
* `print status_resource.text`
```
{
  "data": {
    "expires_in": 600, 
    "job_status": null, 
    "resource_url": "https://qa.datanectartest.s3.amazonaws.com/chains/testchains/hello_luigiworld_chain/TestS3Task/b226f1826734303ca9d39d79f960b367/out.txt?Signature=2DVZzbEJEFjcgNBELrJPe0S2wwc%3D&Expires=1464972637&AWSAccessKeyId=obfuscated"
  }, 
  "message": "success", 
  "status": 200
}
```
* that <b>resource_url</b> is the path to your <b>luigi.Target</b> which is defined in your task
* now, you can check the front-ends just like before, but now navigate to your [s3 console](https://console.aws.amazon.com/s3/home?region=us-west-2#)
* you should see an s3 bucket with your `ENV.PROJECT_BUCKET` environment variables
* The S3 bucket schema <b>mirrors our project structure</b>
* The S3 bucket path will be <b>chains/testchains/hello_luigiworld_chain/TestS3Task</b>
* inside `TestS3Task` key you should see an <b>MD5 hash</b>, which represents the task you just executed, click that
* inside that hash you should see <b>out.txt</b>, <b>log</b>, and <b>params.txt</b>
* <b>out.txt</b> is the Target output of your task
* <b>logs</b> contains the stdout and stderr of our task execution
* <b>params.txt</b> contains the parameters provided for this task


## More on architecture

Chains

   * all chains live under the code/chains/* directory
   * chain types
      * all chain types live under the code/chains/[TYPE] directory structure
      * example: code/chains/agg 
         * all chains under this directory will be of type agg
   * all chains should be suffixed with _chain.py (example: hello_world_chain.py)
      * this allows our code.api.api_chains.APIChainCollector to infer which modules under relevant directories are actually chains
      * this also allows for out-of-the-box exposure and access via the data nectar api: /api/chains/*



Tasks

   * all tasks should live within a _chain.py module
   * all tasks should be suffixed with Task (example: NectarS3Task)
   * all tasks desiring to target to S3 (this should be almost all of our tasks) should inherit from the NectarS3Task (code.util.s3task.NectarS3Task)


API

   * the datanectar API is a dynamically built and maintained API based on the above mentioned naming conventions
   * anything under chains/[TYPE]/some_chain.py will be dynamically exposed and accessible via the API
   * anything WITHOUT the proper naming conventions will not be exposed or accessible via the API, and that’s totally fine if we want to isolate some things
   * execution
      * all the API does is allow HTTP access to the luigi Tasks, so where a task might be normally invoked in python like: 
         * SomeLuigiTask(param1=hello, param2=world).run()
      * the api access is as follows:
         * POST /api/chains/[TYPE]/some_chain/SomeLuigiTask?param1=hello&param2=world
   * responses
      * the API will provide an HTTP response by default with an ephemeral s3 url for the target created by the task like: 

```
                    {
  "data": {
    "expires_in": 60,
    "target_url": "https://qa.datanectar.s3.amazonaws.com/chains/test/hello_world_chain/TestS3Task/testdocker?Signature=3lFmgIabBQ9s51M1M2ajKiix4po%3D&Expires=1458956284&AWSAccessKeyId=obfuscated"
  },
  "message": "success",
  "status": 200
}
```




Copyright 2021 Wes Madrigal

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
