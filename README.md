# Datanectar is a base architecture for large-scale, production-ready, ETL and data science jobs.

## Goals
1. Dependency based task chain execution workflow (one task's completion is the requirement for the next downstream task, etc.)
2. Task idempotency
3. Task failover resolution
4. Task logging
5. Task visualization front-end
6. Dynamically built API
7. Bridgeing the gap between data science and software engineering (lets the data scientists worry about the data science and provides a software engineering backend for them to work with and go directly to production)

## Dependency based task chain execution workflow
Datanectar heavily leverages Spotify's [luigi](https://media.readthedocs.org/pdf/luigi/latest/luigi.pdf).  Luigi provides a very nice architecture for dependency based task chain workflows.  Since there is a plethora of documentation on the project, I'm going to defer going deeper to their docs.

## Task idempotency
Datanectar is currently tied to AWS in that outside of local development, the project has direct plugs into Amazon S3 for the Task Targets (more on this below).  This was chosen for two reasons.  One, S3 is in the cloud and atomic, two, the project aims to be horizontally scalable and we need a canonical location for those horizontal disparate nodes to look when deciding whether or not they need to execute a task.

## Task failover resolution
Due to the fact we have achieved idempotency in the project, if we have a 5 step task chain and step 3 fails, we can simply pick back up at step 3 after the bug is fixed.  Our step 1-3 targets (the output of our tasks) are already in S3 (or our local filesystem if we're doing local dev).

## Task logging
Datanectar creates tempfiles and pushes them to S3 out of the box for us.

## Task visualization front-end
Thanks to the authors of luigi, we get a d3 directed acrylic graph of tasks, their statuses, and stack traces for free.  Since datanectar uses luigi, this is available fo free

## Dynamically built API
Datanectar imposes certain taxonomy on the developer to make use of a dynamically available API for HTTP based task execution (if desired).  
* All task chains must live under some <b>chains/[somechaintype]</b> dir.  
* The actual chain definition in python code must be suffixed with <b>_chain.py</b>.  Ex. (<b>hello_luigiworld_chain.py</b>).  
* The <i>Task</i> classes within the chain.py file must be suffixed with <b>Task</b> Ex. (<b>TestS3Task, DownstreamTask, ETLTask</b>). 
If these schema and taxonomy are not followed, there will be no API availability at (http://localhost:5000/api/chains or your custom project URI in production).

## Bridging the gap between data science and software engineering
Likely the biggest issue I've had working with data scientists over the years is the transition from data science to production ready code.  In most places the data scientists explore the data and build their models, then hand the code off to software engineers to rewrite / wrap in something production ready.  This often proves to be nontrivial, error-prone, and quite frankly a horrible use of software engineering time.  The datanectar project aims to eliminate this friction and allow the data scientists to plug directly into the <b>NectarS3Task</b> (or your custom luigi.Task child) and get out of the box all of the above (logging, atomic availability of results with hashed tags, logs, api access, visualization, etc.).

# Local Setup
* checkout the project <i>git clone https://github.com/wesmadrigal/datanectar</i>
* <i>cd datanectar</i>
* build the virtual environment <i>virtualenv venv</i>
* install dependencies <i>venv/bin/pip install -r configuration/requirements.txt</i>
* startup the luigi server <i>source venv/bin/activate && luigid</i>
* startup the app server <i>cd ~/path/to/datanectar/code/ && ../venv/bin/python app.py</i>
* visit http://localhost:5000 (app front-end)
* visit http://localhost:8082 (luigi front-end)


# More on architecture

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
    "target_url": "https://qa.datanectar.s3.amazonaws.com/chains/test/hello_world_chain/TestS3Task/testdocker?Signature=3lFmgIabBQ9s51M1M2ajKiix4po%3D&Expires=1458956284&AWSAccessKeyId=AKIAI7ATDBGNCBNWZ7SQ"
  },
  "message": "success",
  "status": 200
}
```
