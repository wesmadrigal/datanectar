#!/usr/bin/env python
import boto
import os

def connect_s3():    
    return boto.connect_s3(
            os.environ['AWS_ACCESS_KEY_ID'],
            os.environ['AWS_SECRET_ACCESS_KEY']
            )
