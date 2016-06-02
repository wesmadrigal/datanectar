#!/usr/bin/env python
import luigi

@luigi.Task.event_handler(luigi.Event.SUCCESS)
def success(*args, **kwargs):
    print "Success!"

@luigi.Task.event_handler(luigi.Event.FAILURE)
def failure(*args, **kwargs):
    print "You are a complete failure!  Jump off a bridge"
